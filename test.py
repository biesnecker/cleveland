from cleveland.actor import BaseActor, ListeningActor
from cleveland.message import Message, QueryMessage, StopMessage
import asyncio

class StringMessage(Message): pass

class PrintActor(ListeningActor):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_message_handler(StringMessage,
                                      self._string_message_handler)


    @asyncio.coroutine
    def _string_message_handler(self, message):
        print(message.payload)


@asyncio.coroutine
def say_hello(a, b, n=10):
    for _ in range(n):
        message = StringMessage('Hello world!')
        #yield from asyncio.sleep(1)
        yield from a.tell(b, message)
    yield from a.stop()
    yield from b.stop()

loop = asyncio.get_event_loop()
a = BaseActor(loop=loop)
b = PrintActor(loop=loop)
a.start()
b.start()

loop.run_until_complete(say_hello(a, b, 1))
