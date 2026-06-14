import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


class ServerStatus(Enum):
    UNKNOWN = auto()
    ONLINE = auto()
    OFFLINE = auto()


@dataclass
class ServerState:
    hostname: str
    status: ServerStatus = ServerStatus.UNKNOWN
    last_changed: float = field(default_factory=time.monotonic)
    last_notified: float = 0.0
    consecutive_failures: int = 0
    offline_since: Optional[float] = None


class StateManager:
    def __init__(self, hostnames: List[str]) -> None:
        self._states: Dict[str, ServerState] = {
            h: ServerState(hostname=h) for h in hostnames
        }

    def get(self, hostname: str) -> ServerState:
        return self._states[hostname]

    def all_offline(self) -> List[str]:
        return [
            h for h, s in self._states.items()
            if s.status == ServerStatus.OFFLINE
        ]
