from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List


@dataclass
class RuntimeEvent:
    event_type: str
    payload: Dict[str, Any]
    timestamp: str


class EventBus:
    """Lightweight in-process event bus for runtime orchestration."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[RuntimeEvent], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable[[RuntimeEvent], None]):
        self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, payload: Dict[str, Any]):
        event = RuntimeEvent(
            event_type=event_type,
            payload=dict(payload),
            timestamp=datetime.utcnow().isoformat(),
        )
        for callback in self._subscribers.get(event_type, []):
            callback(event)
        for callback in self._subscribers.get("*", []):
            callback(event)
