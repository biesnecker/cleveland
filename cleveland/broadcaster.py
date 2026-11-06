import asyncio
import contextlib

from .actor import AbstractActor
from .message import Message


class BaseBroadcaster(AbstractActor):
    """An actor that sends messages to a list of target actors."""

    def __init__(self, targets: list[AbstractActor] | None = None) -> None:
        super().__init__()
        self.targets: list[AbstractActor] = [] if targets is None else targets

    async def _task(self) -> None:
        await self._stopping.wait()

    async def broadcast(self, message: Message) -> None:
        """Tell every target the same message."""
        for target in self.targets:
            await self.tell(target, message)


class TimedBroadcaster(BaseBroadcaster):
    """Broadcasts the message returned by ``_message()`` every ``interval``
    seconds."""

    def __init__(
        self, interval: float = 1, targets: list[AbstractActor] | None = None
    ) -> None:
        super().__init__(targets)
        self._interval = interval

    async def _message(self) -> Message:
        raise NotImplementedError(
            "TimedBroadcaster subclasses must implement _message() and return "
            "a valid Message object."
        )

    async def _task(self) -> None:
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._stopping.wait(), self._interval)
        if self._is_running:
            await self.broadcast(await self._message())
