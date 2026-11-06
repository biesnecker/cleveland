"""Run tests on an event loop with a virtual clock, so no test depends on
real timing.

When nothing is ready to run, the loop jumps its clock straight to the next
scheduled timer instead of sleeping. ``asyncio.sleep(60)``, ``wait_for``
timeouts and ``TimedBroadcaster`` intervals all complete instantly, in a
deterministic order. If nothing is ready and no timer is pending, every task
is blocked forever, so the loop raises ``Deadlock`` rather than hanging.
"""

import asyncio
import selectors
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


class Deadlock(Exception):
    """Every task is waiting and no timer is scheduled to wake any of them."""


class _VirtualClockSelector(selectors.DefaultSelector):  # type: ignore[valid-type,misc]
    def __init__(self) -> None:
        super().__init__()
        self.now = 0.0

    def select(self, timeout: float | None = None) -> list[tuple[Any, int]]:
        # Never block on real I/O; the event loop's own wakeup socket is the
        # only thing registered, and tests don't do real I/O.
        events: list[tuple[Any, int]] = super().select(0)
        if not events:
            if timeout is None:
                raise Deadlock("all tasks are blocked and no timer is pending")
            self.now += timeout
        return events


class _VirtualClockLoop(asyncio.SelectorEventLoop):
    def __init__(self) -> None:
        self._clock = _VirtualClockSelector()
        super().__init__(self._clock)
        # asyncio runs timers due within the real clock's resolution early
        # (about 15ms on Windows), which would make until_idle() a plain
        # yield there. The virtual clock is exact.
        self._clock_resolution = 1e-9

    def time(self) -> float:
        return self._clock.now


def run(coro: Coroutine[Any, Any, T]) -> T:
    """Like ``asyncio.run``, but on the virtual clock."""
    with asyncio.Runner(loop_factory=_VirtualClockLoop) as runner:
        return runner.run(coro)


async def until_idle() -> None:
    """Let every other task run until it blocks.

    Uses the virtual clock, so this doesn't actually wait. Nothing the tests
    schedule fires sooner than this, so all other ready work runs first.
    """
    await asyncio.sleep(1e-6)
