# Changelog

## 0.3.0 (2026-11-05)

Cleveland 0.2 can't be imported on Python 3.11 and newer, because it used
`@asyncio.coroutine`. 0.3 rewrites it with `async def`/`await`. It's a
breaking release; see "Upgrading from 0.2" in the README.

### Changed

- Requires Python 3.11 or newer. Handlers, `tell()`, `ask()`, `stop()` and the
  `_stop()`, `_task()` and `_message()` hooks are `async def` coroutines.
- The `loop=` argument is gone; actors use the running event loop. Actors can
  be created outside a running loop, but `start()` must be called inside one.
- `stop()` now handles every message sent before it, then stops. Previously
  it stopped after the current message, and messages still in the inbox were
  never handled.
- Exceptions from handlers of told messages, and told messages with no
  handler, are logged to the `cleveland` logger with tracebacks instead of
  raising a warning without the exception.
- `BaseActor` and the broadcasters take keyword arguments
  (`max_inbox_size=`, `interval=`, `targets=`) instead of `*args, **kwargs`.
- A broadcaster's targets are the public `targets` list.
- `Message` reprs name the message class, e.g. `Text(payload='hi')`.
- Packaging moved from `setup.py`/distutils (removed in Python 3.12) to
  `pyproject.toml`. Wheels are now published alongside the sdist.

### Fixed

- `stop()` waited forever on an actor that was never started.
- A message with no handler crashed the actor, after which `stop()` waited
  forever. `ask()` now raises `HandlerNotFoundError` and the actor carries on.
- If an `ask()` was cancelled or timed out, the actor crashed when the
  handler finished.
- `ask()` waited forever if the actor was stopped, or stopped or died with the
  query still in its inbox. Queries sent before `stop()` are now answered.
  Later ones, and any left behind when an actor dies, raise
  `ActorStoppedError`, as does telling a stopped actor.
- Exceptions from a query's handler are raised from `ask()` (#3). The fix
  was merged in 2015 (#5, thanks @saaj) but never released.
- The `_start()` hook was never called.
- `stop()` on a broadcaster could take up to a second; it now returns
  immediately.
- Broadcasters created without `targets` shared one default list.
- `ask()` checked for a `QueryMessage` with `assert`, which `python -O` skips.
  It now raises `TypeError`.
- `tell()` turned any `AttributeError` raised while delivering a message into
  a misleading "Is it an actor?" `TypeError`.

### Added

- Type hints and a `py.typed` marker. `register_handler()` checks that the
  handler accepts the message class it's registered for.
- `ActorStoppedError`, and the public classes can be imported directly from
  `cleveland`.

## 0.2.1 (2015-04-04)

- Added `BaseBroadcaster` and `TimedBroadcaster`.

## 0.2 (2015-04-03)

- Simplified model, removed ListeningActor and the concept of tasks. Actors
  should only respond to messages.

## 0.1 (2015-04-02)

- Initial release.
