from typing import Any, Callable, Self, cast


class SubscriptableEvent:
    """An event other components can send and subscribe to."""

    _subscribers: list[Callable[[Self], Any]] = []

    def __init_subclass__(cls) -> None:
        cast(list[Callable[[Self], Any]], cls._subscribers)

    @classmethod
    def subscribe(cls, callback: Callable[[Self], Any]) -> None:
        # mypy doesn't understand the Self type here
        cls._subscribers.append(callback)

    @classmethod
    def unsubscribe(cls, callback: Callable[[Self], Any]) -> None:
        cls._subscribers.remove(callback)

    def process(self: Self) -> None:
        for func in self._subscribers:
            func(self)
