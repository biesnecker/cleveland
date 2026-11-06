# Cleveland

[![CI](https://github.com/biesnecker/cleveland/actions/workflows/ci.yml/badge.svg)](https://github.com/biesnecker/cleveland/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/cleveland)](https://pypi.org/project/cleveland/)

Simple asyncio-based actors.

Named after [Carol Cleveland](http://en.wikipedia.org/wiki/Carol_Cleveland), the only significant female performer on Monty
Python's Flying Circus.

```
pip install cleveland
```

Cleveland supports Python 3.11 and newer, has no dependencies, and includes
type hints, so type checkers such as mypy check your handlers against its API.

### Example usage

```python
import asyncio

from cleveland import BaseActor, Message, QueryMessage


# Define new message classes, and register handlers for them in your actors.
class StringMessage(Message):
    pass


class LengthQuery(QueryMessage):
    pass


# Define actors that respond to Message subclasses with custom behavior.
class PrintActor(BaseActor):
    def __init__(self) -> None:
        super().__init__()
        self.register_handler(StringMessage, self.on_string)
        self.register_handler(LengthQuery, self.on_length)

    async def on_string(self, message: StringMessage) -> None:
        print(message.payload)

    # A query handler's return value is the answer to ask().
    async def on_length(self, message: LengthQuery) -> int:
        return len(message.payload)


async def main() -> None:
    a = BaseActor()
    b = PrintActor()
    b.start()
    for _ in range(3):
        await a.tell(b, StringMessage("Hello world!"))
    print(await a.ask(b, LengthQuery("Hello world!")))  # 12
    await b.stop()


asyncio.run(main())
```

[`example.py`](example.py) also shows a `TimedBroadcaster`.

### How actors behave

- Each actor handles the messages in its inbox one at a time, in the order they
  arrived. A handler is chosen by the message's exact class.
- `start()` must be called while the event loop is running. Messages told
  before `start()` wait in the inbox. An actor can only be started once.
- `await actor.stop()` handles every message sent before it, then waits for
  the actor to finish. After `stop()`, telling the actor anything raises
  `ActorStoppedError`. Telling an actor a `StopMessage` stops it the same way.
- `BaseActor(max_inbox_size=n)` bounds the inbox, so `tell()` waits while it's
  full. The default, 0, is unbounded.

### Errors

- If a query's handler raises, `ask()` raises that exception. If a told
  message's handler raises, the exception is logged to the `cleveland` logger
  with its traceback. Either way, the actor carries on with the next message.
- A message with no registered handler makes `ask()` raise
  `HandlerNotFoundError`. For `tell()`, it's logged.
- If an actor dies before answering a query, for example because its task was
  cancelled, `ask()` raises `ActorStoppedError` instead of waiting forever.
- An `ask()` that's cancelled or times out doesn't affect the actor.

### Broadcasters

`BaseBroadcaster(targets=[...])` tells every target the same message with
`await broadcaster.broadcast(message)`. Subclass `TimedBroadcaster` and
implement `async def _message(self) -> Message` to broadcast a message every
`interval` seconds. Stopping a broadcaster doesn't wait for the current
interval to finish.

### Upgrading from 0.2

Cleveland 0.3 uses `async def` throughout. `@asyncio.coroutine` was removed in
Python 3.11, so 0.2 can't be imported on any supported Python. To upgrade,
write handlers and overrides as `async def` methods, replace `yield from` with
`await`, and remove any `loop=` arguments: actors use the running event loop.
See [CHANGELOG.md](CHANGELOG.md) for all changes.
