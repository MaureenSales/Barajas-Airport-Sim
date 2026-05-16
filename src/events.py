from enum import Enum, auto
from dataclasses import dataclass, field


class EventType(Enum):
    ARRIVAL = auto()        # plane arrives at airport
    LANDING_END = auto()    # landing phase complete
    REFUEL_END = auto()     # refueling complete
    UNLOAD_END = auto()     # cargo load/unload complete
    REPAIR_END = auto()     # repair complete (if breakdown)
    TAKEOFF_END = auto()    # takeoff complete — runway free


@dataclass(order=True)
class Event:
    time: float
    etype: EventType = field(compare=False)
    plane_id: int = field(compare=False)
    runway_id: int = field(compare=False, default=-1)
