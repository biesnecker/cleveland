from .message import StopMessage
import asyncio

class HandlerNotFoundError(KeyError): pass

class AbstractActor(object):

    def __init__(self, *args, **kwargs):
        self._loop = kwargs.get('loop', asyncio.get_event_loop())
        self._is_running = False
        self._run_complete = asyncio.Future()

    def start(self):
        self._is_running = True
        self._loop.create_task(self._run())

    @asyncio.coroutine
    def stop(self):
        self._is_running = False
        yield from self._stop()
        yield from self._run_complete
        return True

    # Custom startup logic, override in subclasses
    def _start(self): pass

    # Custom shutdown logic, override in subclasses
    @asyncio.coroutine
    def _stop(self): pass

    # The actor's main work loop
    @asyncio.coroutine
    def _run(self):
        while self._is_running:
            yield from self._task()

        # Signal that the loop has finished.
        self._run_complete.set_result(True)

    @asyncio.coroutine
    def _task(self):
        raise NotImplementedError('Subclasses of AbstractActor must implement '
                                  '_task()')

    @asyncio.coroutine
    def tell(self, target, message):
        try:
            yield from target._receive(message)
        except AttributeError as e:
            print('Target does not have a _receive method. Is it an actor?')
            raise

    @asyncio.coroutine
    def ask(self, target, message):
        result_future = message.result
        if not result_future:
            raise TypeError('Messages sent as asks must have a Future as its '
                            'results attribute.')
        yield from self.tell(target, message)
        return (yield from result_future)


class BaseActor(AbstractActor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_inbox_size = kwargs.get('max_inbox_size', 0)
        self._inbox = asyncio.Queue(maxsize=self._max_inbox_size,
                                    loop=self._loop)
        self._handlers = {}

        # Create handler for the 'poison pill' message
        self.register_handler(StopMessage, self._stop_message_handler)

    def register_handler(self, message_cls, func):
        self._handlers[message_cls] = func

    @asyncio.coroutine
    def _task(self):
        message = yield from self._inbox.get()
        try:

            response = yield from self._handlers[type(message)](message)

            # If the message is expecting a result, resolve it.
            try:
                message.result.set_result(response)
            except AttributeError:
                pass

        except KeyError as e:
            raise HandlerNotFoundError(type(message)) from e


    @asyncio.coroutine
    def _stop(self):
        yield from self._receive(StopMessage())

    @asyncio.coroutine
    def _receive(self, message):
        yield from self._inbox.put(message)

    # The stop message is only to ensure that the queue has at least one item
    # in it so the call to _inbox.get() doesn't block. We don't actually have
    # to do anything with it.
    @asyncio.coroutine
    def _stop_message_handler(self, message): pass
