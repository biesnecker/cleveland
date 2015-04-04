from .actor import AbstractActor
from .message import Message
import asyncio

class BaseBroadcaster(AbstractActor):

    def __init__(self, targets=list(), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._targets = targets

    @asyncio.coroutine
    def _task(self):
        yield from asyncio.sleep(1)


    @asyncio.coroutine
    def broadcast(self, message):
        for target in self._targets:
            yield from self.tell(target, message)



class TimedBroadcaster(BaseBroadcaster):

    def __init__(self, interval=1, targets=list(), *args, **kwargs):
        super().__init__(targets, *args, **kwargs)
        self._interval = interval

    @asyncio.coroutine
    def _message(self):
        raise NotImplementedError('TimedBroadcast subclasses must implement '
                                  '_message() and return a valid Message '
                                  'object.')

    @asyncio.coroutine
    def _task(self):
        i = self._interval
        while i > 0.01:
            wait = min(i, 1)
            if not self._is_running:
                break
            yield from asyncio.sleep(wait)
            i -= wait
        if self._is_running:
            message = yield from self._message()
            yield from self.broadcast(message)




