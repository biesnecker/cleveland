from .message import Message, QueryMessage, StopMessage
import asyncio

class HandlerNotFoundError(KeyError): pass

class BaseActor(object):

    def __init__(self, *args, **kwargs):
        self._loop = kwargs.get('loop', asyncio.get_event_loop())
        self._max_inbox_size = kwargs.get('max_inbox_size', 0)
        self._inbox = asyncio.Queue(maxsize=self._max_inbox_size,
                                    loop=self._loop)
        self._is_running = False
        self._run_complete = asyncio.Future()
        self._handlers = {}

        # Create handler for the 'poison pill' message
        self.register_handler(StopMessage, self._stop_message_handler)

    def register_handler(self, message_cls, func):
        self._handlers[message_cls] = func

    def start(self):
        self._is_running = True
        self._loop.create_task(self._run())

    @asyncio.coroutine
    def stop(self):
        self._is_running = False
        yield from self._receive(StopMessage())
        yield from self._run_complete
        return True

    @asyncio.coroutine
    def _run(self):
        while self._is_running:
            message = yield from self._inbox.get()
            try:
                response = yield from self._handlers[type(message)](message)

                # If the message is expecting a result, resolve it.
                try:
                    result.set_result(response)
                except AttributeError:
                    pass
            except KeyError as e:
                raise HandlerNotFoundError(type(message)) from e

        # Signal that the loop has finished.
        self._run_complete.set_result(True)

    def tell(self, target, message):
        yield from target._receive(message)

    def ask(self, target, message):
        result_future = message.result
        if not result_future:
            raise TypeError('Messages sent as asks must have a Future as its '
                            'results attribute.')
        yield from self.tell(target, message)
        return (yield from result_future)

    @asyncio.coroutine
    def _receive(self, message):
        yield from self._inbox.put(message)

    # The stop message is only to ensure that the queue has at least one item
    # in it so the call to _inbox.get() doesn't block. We don't actually have
    # to do anything with it.
    @asyncio.coroutine
    def _stop_message_handler(self, message):
        pass
