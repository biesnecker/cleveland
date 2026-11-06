import asyncio
from typing import Any


class Message:
    """Base class for messages sent between actors."""

    def __init__(self, payload: Any = None) -> None:
        self.payload = payload

    def __repr__(self) -> str:
        return f"{type(self).__name__}(payload={self.payload!r})"


class QueryMessage(Message):
    """Special type of message that expects a response."""

    def __init__(self, payload: Any = None) -> None:
        super().__init__(payload)
        self.result: "asyncio.Future[Any] | None" = None
        """Future for the response, set in ``AbstractActor.ask`` if not set by
        the caller."""


class StopMessage(Message):
    """Special type of message that tells actors to quit processing their
    inbox.
    """
