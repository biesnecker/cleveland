import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from .message import Message, QueryMessage, StopMessage

logger = logging.getLogger("cleveland")

M = TypeVar("M", bound=Message)


class HandlerNotFoundError(KeyError):
    """An actor received a message type it has no handler for."""


class ActorStoppedError(RuntimeError):
    """An actor stopped before it could handle a message."""


class AbstractActor:
    """An actor that repeatedly runs ``_task()`` between ``start()`` and
    ``stop()``.
    """

    def __init__(self) -> None:
        self._is_running = False
        self._stopping = asyncio.Event()
        self._run_task: "asyncio.Task[None] | None" = None

    def start(self) -> None:
        """Start the actor's work loop. Must be called with the event loop
        running, and only once per actor."""
        if self._run_task is not None:
            raise RuntimeError(f"{type(self).__name__} has already been started")
        self._is_running = True
        self._start()
        self._run_task = asyncio.create_task(self._run())

    async def stop(self) -> bool:
        """Stop the actor and wait for its work loop to finish.

        Raises any exception that ended the work loop early.
        """
        if self._run_task is None:
            return True
        if self._is_running:
            self._is_running = False
            self._stopping.set()
            await self._stop()
        await self._run_task
        return True

    def _start(self) -> None:
        """Custom startup logic, override in subclasses."""

    async def _stop(self) -> None:
        """Custom shutdown logic, override in subclasses."""

    async def _run(self) -> None:
        """The actor's main work loop."""
        while self._is_running:
            await self._task()

    async def _task(self) -> None:
        raise NotImplementedError("Subclasses of AbstractActor must implement _task()")

    async def tell(self, target: "AbstractActor", message: Message) -> None:
        """Put a message in the target actor's inbox."""
        receive = getattr(target, "_receive", None)
        if receive is None:
            raise TypeError("Target does not have a _receive method. Is it an actor?")
        await receive(message)

    async def ask(self, target: "AbstractActor", message: QueryMessage) -> Any:
        """Send a query to the target actor and wait for its handler's result."""
        if not isinstance(message, QueryMessage):
            raise TypeError(f"ask() needs a QueryMessage, not {type(message).__name__}")
        result = message.result
        if result is None:
            result = message.result = asyncio.get_running_loop().create_future()
        await self.tell(target, message)
        return await result


class BaseActor(AbstractActor):
    """An actor that handles messages from its inbox, one at a time, with the
    handler registered for each message type."""

    def __init__(self, *, max_inbox_size: int = 0) -> None:
        super().__init__()
        self._max_inbox_size = max_inbox_size
        self._inbox: asyncio.Queue[Message] = asyncio.Queue(maxsize=max_inbox_size)
        self._handlers: dict[type[Message], Callable[[Any], Awaitable[object]]] = {}
        # Set once stop() is called: no new messages are accepted.
        self._closed = False
        # Set once the StopMessage is handled: the work loop ends.
        self._done = False

        # Create handler for the 'poison pill' message
        self.register_handler(StopMessage, self._stop_message_handler)

    def register_handler(
        self, message_cls: type[M], func: Callable[[M], Awaitable[object]]
    ) -> None:
        """Handle messages of exactly ``message_cls`` with ``func``. For a
        ``QueryMessage``, its return value is the result of ``ask()``."""
        self._handlers[message_cls] = func

    async def _run(self) -> None:
        # Unlike AbstractActor, keep going until the StopMessage that stop()
        # queues is reached, so messages sent before stop() are all handled.
        try:
            while not self._done:
                await self._task()
        finally:
            self._closed = True
            self._fail_pending_queries()

    async def _task(self) -> None:
        message = await self._inbox.get()
        result = message.result if isinstance(message, QueryMessage) else None
        handler = self._handlers.get(type(message))

        if handler is None:
            if result is not None:
                _set_exception(result, HandlerNotFoundError(type(message)))
            else:
                logger.error("No handler for %r in %s", message, type(self).__name__)
            return

        try:
            response = await handler(message)
        except Exception as ex:
            if result is not None:
                _set_exception(result, ex)
            else:
                logger.exception(
                    "Unhandled exception from handler of %s in %s",
                    type(message).__name__,
                    type(self).__name__,
                )
        else:
            if result is not None and not result.done():
                result.set_result(response)

    async def _stop(self) -> None:
        self._closed = True
        if self._run_task is not None and not self._run_task.done():
            await self._inbox.put(StopMessage())

    async def _receive(self, message: Message) -> None:
        if self._closed:
            raise ActorStoppedError(f"{type(self).__name__} has stopped")
        await self._inbox.put(message)

    def _fail_pending_queries(self) -> None:
        while not self._inbox.empty():
            message = self._inbox.get_nowait()
            if isinstance(message, QueryMessage) and message.result is not None:
                _set_exception(
                    message.result,
                    ActorStoppedError(f"{type(self).__name__} stopped before handling {message!r}"),
                )

    async def _stop_message_handler(self, message: StopMessage) -> None:
        """The 'poison pill': everything queued before it has been handled,
        so end the work loop."""
        self._closed = True
        self._done = True


def _set_exception(future: "asyncio.Future[Any]", ex: BaseException) -> None:
    # The asker may have given up (been cancelled or timed out) already.
    if not future.done():
        future.set_exception(ex)
