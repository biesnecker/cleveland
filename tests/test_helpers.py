"""Tests for the virtual-clock test helpers themselves."""

import asyncio

import pytest

from helpers import Deadlock, run, until_idle


def test_sleep_advances_virtual_clock_without_waiting() -> None:
    async def main() -> float:
        loop = asyncio.get_running_loop()
        start = loop.time()
        await asyncio.sleep(3600)
        return loop.time() - start

    assert run(main()) == 3600


def test_timers_fire_in_order() -> None:
    async def main() -> list[int]:
        fired: list[int] = []

        async def after(delay: float, tag: int) -> None:
            await asyncio.sleep(delay)
            fired.append(tag)

        await asyncio.gather(after(3, 3), after(1, 1), after(2, 2))
        return fired

    assert run(main()) == [1, 2, 3]


def test_deadlock_raises_instead_of_hanging() -> None:
    with pytest.raises(Deadlock):
        run(asyncio.Event().wait())


def test_until_idle_lets_other_tasks_run_until_they_block() -> None:
    async def main() -> list[str]:
        steps: list[str] = []
        gate = asyncio.Event()

        async def worker() -> None:
            steps.append("started")
            await asyncio.sleep(0)
            steps.append("blocking")
            await gate.wait()
            steps.append("released")

        task = asyncio.create_task(worker())
        await until_idle()
        assert steps == ["started", "blocking"]
        gate.set()
        await task
        return steps

    assert run(main()) == ["started", "blocking", "released"]
