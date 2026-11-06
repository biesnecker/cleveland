import asyncio

from cleveland import BaseActor, Message, QueryMessage, TimedBroadcaster


class StringMessage(Message):
    pass


class LengthQuery(QueryMessage):
    pass


class PrintActor(BaseActor):
    def __init__(self) -> None:
        super().__init__()
        self.register_handler(StringMessage, self.on_string)
        self.register_handler(LengthQuery, self.on_length)

    async def on_string(self, message: StringMessage) -> None:
        print(message.payload)

    async def on_length(self, message: LengthQuery) -> int:
        return len(message.payload)


class GreetingBroadcaster(TimedBroadcaster):
    async def _message(self) -> Message:
        return StringMessage("Hello dolly!")


async def say_hello() -> None:
    a = BaseActor()
    b = PrintActor()
    b.start()
    for _ in range(3):
        await a.tell(b, StringMessage("Hello world!"))
        await asyncio.sleep(0.25)
    print("Length:", await a.ask(b, LengthQuery("Hello world!")))
    await b.stop()


async def broadcast_hello() -> None:
    b = PrintActor()
    b.start()
    a = GreetingBroadcaster(interval=0.75, targets=[b])
    a.start()
    await asyncio.sleep(3)
    await a.stop()
    await b.stop()


if __name__ == "__main__":
    asyncio.run(say_hello())
    asyncio.run(broadcast_hello())
