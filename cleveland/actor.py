from .message import Message, QueryMessage, StopMessage
import asyncio

class BaseActor(object):

    def __init__(self, **kwargs):
        self._loop = kwargs.get('loop', asyncio.get_event_loop())
        self._tasks = []
        self._task_shutdown_funcs = {}
        self._task_shutdown_handles = {}
        self._is_running = False
        self._run_complete = asyncio.Future()

    def register_task_handler(self, task_id, func, shutdown_func=None):
        self._tasks.append(func)
        self._task_shutdown_funcs[task_id] = shutdown_func
        self._task_shutdown_handles[task_id] = asyncio.Future()

    def start(self):
        self._is_running = True
        self._loop.create_task(self._run())

    @asyncio.coroutine
    def stop(self):
        self._is_running = False
        for task_id, func in self._task_shutdown_funcs.items():
            if func:
                x = yield from func()
                self._task_shutdown_handles[task_id].set_result(x)
            else:
                self._task_shutdown_handles[task_id].set_result(True)
        yield from self._run_complete

    @asyncio.coroutine
    def _run(self):
        while self._is_running:
            for fn in self._tasks:
                yield from fn()
            else:
                yield from asyncio.sleep(0.01)

        # Wait for all of the tasks' shutdown functions to return
        asyncio.wait(self._task_shutdown_handles.values())

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

class ListeningActor(BaseActor):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._max_inbox_size = kwargs.get('max_inbox_size', 0)

        self._message_handlers = {}
        self._inbox = asyncio.Queue(maxsize=self._max_inbox_size,
                                    loop=self._loop)

        self.register_message_handler(StopMessage, self._stop_message_handler)
        self.register_task_handler('__message_loop', self._process_inbox,
                                   self._shutdown_message_loop)


    def register_message_handler(self, message_cls, func):
        self._message_handlers[message_cls] = func

    @asyncio.coroutine
    def _receive(self, message):
        yield from self._inbox.put(message)

    @asyncio.coroutine
    def _process_inbox(self):
        message = yield from self._inbox.get()
        if type(message) in self._message_handlers:
            yield from self._message_handlers[type(message)](message)
        else:
            raise KeyError('No handler registered for messages of type '
                           '{0}'.format(type(message)))

    # The stop message is only to ensure that the queue has at least one item
    # in it so the call to _inbox.get() doesn't block. We don't actually have
    # to do anything with it.
    @asyncio.coroutine
    def _stop_message_handler(self, message):
        pass

    @asyncio.coroutine
    def _shutdown_message_loop(self):
        yield from self._receive(StopMessage())
        return True