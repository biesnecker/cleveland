from cleveland.actor import BaseActor
from cleveland.message import Message
import asyncio

class StringMessage(Message): pass

class PrintActor(BaseActor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_handler(StringMessage,
                              self._string_message_handler)


    @asyncio.coroutine
    def _string_message_handler(self, message):
        print(message.payload)


@asyncio.coroutine
def say_hello():
    a = BaseActor()
    b = PrintActor()
    a.start()
    b.start()
    for _ in range(10):
        message = StringMessage('Hello world!')
        yield from asyncio.sleep(0.25)
        yield from a.tell(b, message)
    yield from a.stop()
    yield from b.stop()

asyncio.get_event_loop().run_until_complete(say_hello())
