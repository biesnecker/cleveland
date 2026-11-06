"""Type-checked by CI with `mypy --strict`, not run by pytest.

Exercises cleveland's public API the way a typed downstream project would, so
missing or wrong type hints fail CI.
"""

import asyncio

import cleveland
from cleveland import (
    AbstractActor,
    ActorStoppedError,
    BaseActor,
    BaseBroadcaster,
    HandlerNotFoundError,
    Message,
    QueryMessage,
    TimedBroadcaster,
)


class Greeting(Message):
    pass


class Add(QueryMessage):
    pass


class Greeter(BaseActor):
    def __init__(self) -> None:
        super().__init__(max_inbox_size=10)
        self.register_handler(Greeting, self.on_greeting)
        self.register_handler(Add, self.on_add)

    def _start(self) -> None:
        pass

    async def _stop(self) -> None:
        await super()._stop()

    async def on_greeting(self, message: Greeting) -> None:
        print(message.payload)

    async def on_add(self, message: Add) -> int:
        a, b = message.payload
        return int(a) + int(b)


class Clock(TimedBroadcaster):
    async def _message(self) -> Message:
        return Greeting("tick")


class Custom(AbstractActor):
    async def _task(self) -> None:
        await asyncio.sleep(1)


async def main() -> None:
    greeter = Greeter()
    greeter.start()
    clock = Clock(interval=0.5, targets=[greeter])
    clock.start()
    manual = BaseBroadcaster(targets=[greeter])
    manual.targets.append(greeter)
    await manual.broadcast(Greeting("hi"))

    await greeter.tell(greeter, Greeting("hello"))
    total = await greeter.ask(greeter, Add((1, 2)))
    print(total + 1)

    try:
        await greeter.ask(greeter, QueryMessage())
    except HandlerNotFoundError:
        pass
    except ActorStoppedError:
        pass

    stopped: bool = await clock.stop()
    print(stopped, cleveland.__version__, cleveland.__version_info__)
    await manual.stop()
    await greeter.stop()
    await Custom().stop()


asyncio.run(main())
