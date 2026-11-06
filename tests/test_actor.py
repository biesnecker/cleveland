import asyncio
import logging
from typing import Any

import pytest

import cleveland
from cleveland import (
    ActorStoppedError,
    BaseActor,
    HandlerNotFoundError,
    Message,
    QueryMessage,
    StopMessage,
)

from helpers import run, until_idle


class Text(Message):
    pass


class Double(QueryMessage):
    pass


class Unhandled(QueryMessage):
    pass


class Recorder(BaseActor):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.seen: list[Any] = []
        self.started = False
        self.release = asyncio.Event()
        self.release.set()
        self.register_handler(Text, self.on_text)
        self.register_handler(Double, self.on_double)

    def _start(self) -> None:
        self.started = True

    async def on_text(self, message: Text) -> None:
        await self.release.wait()
        if message.payload == "boom":
            raise ValueError("boom")
        self.seen.append(message.payload)

    async def on_double(self, message: Double) -> int:
        await self.release.wait()
        if message.payload is None:
            raise ValueError("no payload")
        return int(message.payload) * 2


def test_package_exports_public_api() -> None:
    from cleveland.actor import AbstractActor
    from cleveland.broadcaster import BaseBroadcaster, TimedBroadcaster
    from cleveland.message import StopMessage

    assert cleveland.AbstractActor is AbstractActor
    assert cleveland.BaseBroadcaster is BaseBroadcaster
    assert cleveland.TimedBroadcaster is TimedBroadcaster
    assert cleveland.StopMessage is StopMessage
    assert cleveland.__version__ == ".".join(map(str, cleveland.__version_info__))


def test_actor_can_be_created_outside_a_running_loop() -> None:
    actor = Recorder()

    async def main() -> None:
        actor.start()
        await actor.tell(actor, Text("hi"))
        await actor.stop()

    run(main())
    assert actor.seen == ["hi"]


def test_tell_delivers_messages_in_order() -> None:
    async def main() -> list[Any]:
        sender, receiver = BaseActor(), Recorder()
        receiver.start()
        for i in range(5):
            await sender.tell(receiver, Text(i))
        await receiver.stop()
        return receiver.seen

    assert run(main()) == [0, 1, 2, 3, 4]


def test_messages_told_before_start_are_handled_after_start() -> None:
    async def main() -> list[Any]:
        receiver = Recorder()
        await BaseActor().tell(receiver, Text("early"))
        receiver.start()
        await BaseActor().ask(receiver, Double(1))  # wait until it's processed
        await receiver.stop()
        return receiver.seen

    assert run(main()) == ["early"]


def test_start_calls_start_hook() -> None:
    async def main() -> bool:
        actor = Recorder()
        actor.start()
        await actor.stop()
        return actor.started

    assert run(main())


def test_start_twice_raises() -> None:
    async def main() -> None:
        actor = Recorder()
        actor.start()
        try:
            with pytest.raises(RuntimeError):
                actor.start()
        finally:
            await actor.stop()

    run(main())


def test_ask_returns_handler_result() -> None:
    async def main() -> int:
        receiver = Recorder()
        receiver.start()
        result = await BaseActor().ask(receiver, Double(21))
        await receiver.stop()
        return result

    assert run(main()) == 42


def test_ask_raises_handler_exception() -> None:
    async def main() -> None:
        receiver = Recorder()
        receiver.start()
        with pytest.raises(ValueError, match="no payload"):
            await BaseActor().ask(receiver, Double())
        await receiver.stop()

    run(main())


def test_ask_requires_query_message() -> None:
    async def main() -> None:
        receiver = Recorder()
        with pytest.raises(TypeError):
            await BaseActor().ask(receiver, Text("not a query"))  # type: ignore[arg-type]

    run(main())


def test_tell_to_non_actor_raises_type_error() -> None:
    async def main() -> None:
        with pytest.raises(TypeError, match="Is it an actor"):
            await BaseActor().tell(object(), Text("x"))  # type: ignore[arg-type]

    run(main())


def test_handler_exception_from_tell_is_logged_and_actor_continues(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def main() -> list[Any]:
        receiver = Recorder()
        receiver.start()
        sender = BaseActor()
        await sender.tell(receiver, Text("boom"))
        await sender.tell(receiver, Text("after"))
        await receiver.stop()
        return receiver.seen

    with caplog.at_level(logging.ERROR, logger="cleveland"):
        assert run(main()) == ["after"]

    [record] = caplog.records
    assert "Text" in record.getMessage()
    assert record.exc_info is not None
    assert isinstance(record.exc_info[1], ValueError)


def test_ask_for_unhandled_message_raises_and_actor_continues() -> None:
    async def main() -> int:
        receiver = Recorder()
        receiver.start()
        sender = BaseActor()
        with pytest.raises(HandlerNotFoundError):
            await sender.ask(receiver, Unhandled())
        result = await sender.ask(receiver, Double(2))
        await receiver.stop()
        return result

    assert run(main()) == 4


def test_tell_unhandled_message_is_logged_and_actor_continues(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def main() -> int:
        receiver = Recorder()
        receiver.start()
        sender = BaseActor()
        await sender.tell(receiver, Message("nobody handles me"))
        result = await sender.ask(receiver, Double(3))
        await receiver.stop()
        return result

    with caplog.at_level(logging.ERROR, logger="cleveland"):
        assert run(main()) == 6

    [record] = caplog.records
    assert "No handler" in record.getMessage()


def test_abandoned_ask_does_not_crash_actor() -> None:
    async def main() -> int:
        receiver = Recorder()
        receiver.release.clear()
        receiver.start()
        sender = BaseActor()
        asking = asyncio.create_task(sender.ask(receiver, Double(1)))
        await until_idle()  # the actor is now blocked handling the query
        asking.cancel()  # the asker gives up, e.g. it timed out
        with pytest.raises(asyncio.CancelledError):
            await asking
        receiver.release.set()
        result = await sender.ask(receiver, Double(5))
        await receiver.stop()
        return result

    assert run(main()) == 10


def test_stop_without_start_returns() -> None:
    async def main() -> bool:
        return await Recorder().stop()

    assert run(main()) is True


def test_stop_twice_returns() -> None:
    async def main() -> None:
        actor = Recorder()
        actor.start()
        assert await actor.stop() is True
        assert await actor.stop() is True

    run(main())


def test_stop_waits_for_message_in_progress() -> None:
    async def main() -> list[Any]:
        receiver = Recorder()
        receiver.release.clear()
        receiver.start()
        await BaseActor().tell(receiver, Text("slow"))
        await until_idle()  # the actor is now blocked in the handler
        stopping = asyncio.create_task(receiver.stop())
        await until_idle()
        assert not stopping.done()
        receiver.release.set()
        await stopping
        return receiver.seen

    assert run(main()) == ["slow"]


def test_stop_handles_messages_sent_before_it() -> None:
    async def main() -> tuple[list[Any], int]:
        receiver = Recorder()
        receiver.release.clear()
        receiver.start()
        sender = BaseActor()
        await sender.tell(receiver, Text("in progress"))
        await sender.tell(receiver, Text("queued"))
        pending = asyncio.create_task(sender.ask(receiver, Double(4)))
        await until_idle()
        stopping = asyncio.create_task(receiver.stop())
        await until_idle()
        assert not stopping.done()
        receiver.release.set()
        await stopping
        return receiver.seen, await pending

    assert run(main()) == (["in progress", "queued"], 8)


def test_telling_stop_message_stops_actor() -> None:
    async def main() -> None:
        receiver = Recorder()
        receiver.start()
        await BaseActor().tell(receiver, StopMessage())
        assert receiver._run_task is not None
        await receiver._run_task  # ends by itself, without stop()
        assert await receiver.stop() is True

    run(main())


def test_pending_queries_fail_if_actor_dies() -> None:
    async def main() -> None:
        receiver = Recorder()
        receiver.release.clear()
        receiver.start()
        sender = BaseActor()
        await sender.tell(receiver, Text("in progress"))
        pending = asyncio.create_task(sender.ask(receiver, Double(1)))
        await until_idle()
        assert receiver._run_task is not None
        receiver._run_task.cancel()
        with pytest.raises(ActorStoppedError):
            await pending
        with pytest.raises(asyncio.CancelledError):
            await receiver.stop()

    run(main())


def test_tell_after_stop_raises() -> None:
    async def main() -> None:
        receiver = Recorder()
        receiver.start()
        await receiver.stop()
        with pytest.raises(ActorStoppedError):
            await BaseActor().tell(receiver, Text("too late"))

    run(main())


def test_max_inbox_size_bounds_inbox() -> None:
    async def main() -> list[Any]:
        receiver = Recorder(max_inbox_size=1)
        sender = BaseActor()
        await sender.tell(receiver, Text(1))
        second = asyncio.create_task(sender.tell(receiver, Text(2)))
        await until_idle()
        assert not second.done()  # inbox is full
        receiver.start()
        await second  # room once the actor takes the first message
        await receiver.stop()
        return receiver.seen

    assert run(main()) == [1, 2]


def test_message_repr_names_subclass() -> None:
    assert repr(Text("hi")) == "Text(payload='hi')"
    assert repr(Message()) == "Message(payload=None)"
