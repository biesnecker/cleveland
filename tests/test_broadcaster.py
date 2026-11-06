import asyncio
from typing import Any

import pytest

from cleveland import BaseActor, BaseBroadcaster, Message, TimedBroadcaster

from helpers import run, until_idle


class Tick(Message):
    pass


class Counter(BaseActor):
    def __init__(self) -> None:
        super().__init__()
        self.ticks: list[tuple[float, Any]] = []
        self.register_handler(Tick, self.on_tick)

    async def on_tick(self, message: Tick) -> None:
        self.ticks.append((asyncio.get_running_loop().time(), message.payload))


class Ticker(TimedBroadcaster):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.count = 0

    async def _message(self) -> Message:
        self.count += 1
        return Tick(self.count)


def test_timed_broadcaster_sends_to_every_target_each_interval() -> None:
    async def main() -> tuple[list[Any], list[Any]]:
        a, b = Counter(), Counter()
        a.start()
        b.start()
        ticker = Ticker(interval=10, targets=[a, b])
        ticker.start()
        await asyncio.sleep(35)
        await ticker.stop()
        await a.stop()
        await b.stop()
        return a.ticks, b.ticks

    a_ticks, b_ticks = run(main())
    assert a_ticks == [(10, 1), (20, 2), (30, 3)]
    assert b_ticks == a_ticks


def test_timed_broadcaster_waits_a_full_interval_before_first_message() -> None:
    async def main() -> list[int]:
        ticker = Ticker(interval=10)
        ticker.start()
        counts = []
        await asyncio.sleep(9.9)
        counts.append(ticker.count)
        await asyncio.sleep(0.2)
        counts.append(ticker.count)
        await ticker.stop()
        return counts

    assert run(main()) == [0, 1]


def test_timed_broadcaster_stops_without_waiting_for_interval() -> None:
    async def main() -> float:
        loop = asyncio.get_running_loop()
        ticker = Ticker(interval=60)
        ticker.start()
        await until_idle()
        started = loop.time()
        await ticker.stop()
        assert ticker.count == 0
        return loop.time() - started

    assert run(main()) == pytest.approx(0)


def test_timed_broadcaster_without_message_raises_from_stop() -> None:
    async def main() -> None:
        broadcaster = TimedBroadcaster(interval=1)
        broadcaster.start()
        await asyncio.sleep(1.5)
        with pytest.raises(NotImplementedError):
            await broadcaster.stop()

    run(main())


def test_base_broadcaster_broadcasts_on_demand_and_stops_immediately() -> None:
    async def main() -> tuple[list[Any], float]:
        loop = asyncio.get_running_loop()
        target = Counter()
        target.start()
        broadcaster = BaseBroadcaster(targets=[target])
        broadcaster.start()
        await broadcaster.broadcast(Tick("manual"))
        await until_idle()
        started = loop.time()
        await broadcaster.stop()
        elapsed = loop.time() - started
        await target.stop()
        return [payload for _, payload in target.ticks], elapsed

    ticks, elapsed = run(main())
    assert ticks == ["manual"]
    assert elapsed == pytest.approx(0)


def test_default_targets_are_not_shared() -> None:
    first, second = BaseBroadcaster(), BaseBroadcaster()
    first.targets.append(Counter())
    assert second.targets == []


def test_targets_list_is_used_as_given() -> None:
    targets: list[BaseActor] = []
    broadcaster = BaseBroadcaster(targets=targets)
    targets.append(Counter())
    assert broadcaster.targets is targets
