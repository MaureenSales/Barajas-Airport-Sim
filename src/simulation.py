"""
Discrete-event simulation of Barajas Airport.

A plane occupies a runway from the moment it lands until it finishes takeoff.
While on the runway the following happen (some in parallel):
  - Landing phase          : Normal(10, 5) min
  - Refueling              : Exp(lambda=1/30) min, starts at landing
  - Cargo load/unload      : Exp(lambda=1/30) min, with Uniform probability
  - Breakdown check        : prob 0.1, repair Exp(lambda=1/15), detected before takeoff
  - Takeoff phase          : Normal(10, 5) min

The runway is freed only after takeoff completes.
Simulation horizon: 1 week = 7 * 24 * 60 minutes.
"""

import heapq
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List

from events import Event, EventType
from random_vars import exponential, normal, bernoulli, uniform

NUM_RUNWAYS = 5
ARRIVAL_RATE = 1.0 / 20.0          # lambda for inter-arrival (planes/min)
LANDING_MU = 10.0                  # mean landing time (min)
LANDING_SIGMA2 = 5.0               # variance landing time
TAKEOFF_MU = 10.0
TAKEOFF_SIGMA2 = 5.0
REFUEL_RATE = 1.0 / 30.0
UNLOAD_RATE = 1.0 / 30.0
REPAIR_RATE = 1.0 / 15.0
BREAKDOWN_PROB = 0.1
SIMULATION_TIME = 7 * 24 * 60.0   # one week in minutes


@dataclass
class PlaneState:
    plane_id: int
    runway_id: int
    landing_done: bool = False
    refuel_done: bool = False
    unload_done: bool = False        # True also if no unload needed
    needs_repair: bool = False
    repair_done: bool = False


class AirportSimulation:
    def __init__(self):
        self.clock: float = 0.0
        self.event_queue: List[Event] = []
        self.arrival_queue: deque = deque()    # planes waiting for a runway
        self.runways: List[bool] = [False] * NUM_RUNWAYS  # True = occupied

        # time each runway has been free
        self.runway_free_time: List[float] = [0.0] * NUM_RUNWAYS
        # last time runway became free (to accumulate idle time)
        self.runway_last_freed: List[float] = [0.0] * NUM_RUNWAYS

        self.planes: Dict[int, PlaneState] = {}
        self.next_plane_id: int = 1

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _push(self, event: Event) -> None:
        heapq.heappush(self.event_queue, event)

    def _pop(self) -> Event:
        return heapq.heappop(self.event_queue)

    def _free_runway(self) -> int:
        """Return index of a free runway, or -1 if all occupied."""
        for i, occupied in enumerate(self.runways):
            if not occupied:
                return i
        return -1

    def _assign_runway(self, plane_id: int, runway_id: int) -> None:
        """Mark runway as occupied and start landing sequence for plane."""
        self.runways[runway_id] = True
        # accumulate idle time for this runway up to now
        self.runway_free_time[runway_id] += self.clock - self.runway_last_freed[runway_id]

        state = PlaneState(plane_id=plane_id, runway_id=runway_id)
        # cargo/unload probability is itself Uniform(0,1): draw p ~ U(0,1),
        # then the plane loads/unloads with that probability p.
        # Equivalent to: does a U(0,1) drawn against p succeed?
        # Since p ~ U(0,1) and the check is U2 < p with U2 ~ U(0,1),
        # P(load) = E[p] = 0.5, but correctly models the uniform-probability statement.
        p_unload = uniform()
        state.unload_done = not bernoulli(p_unload)
        self.planes[plane_id] = state

        # landing and refueling start simultaneously at arrival on runway
        landing_duration = max(0.0, normal(LANDING_MU, LANDING_SIGMA2))
        refuel_duration = exponential(REFUEL_RATE)

        self._push(Event(self.clock + landing_duration, EventType.LANDING_END, plane_id, runway_id))
        self._push(Event(self.clock + refuel_duration, EventType.REFUEL_END, plane_id, runway_id))

        if not state.unload_done:
            unload_duration = exponential(UNLOAD_RATE)
            self._push(Event(self.clock + unload_duration, EventType.UNLOAD_END, plane_id, runway_id))

    def _try_takeoff(self, plane_id: int) -> None:
        """Schedule takeoff if all pre-takeoff conditions are met."""
        state = self.planes[plane_id]
        if not (state.landing_done and state.refuel_done and state.unload_done):
            return
        # breakdown check happens right before takeoff
        state.needs_repair = bernoulli(BREAKDOWN_PROB)
        if state.needs_repair and not state.repair_done:
            repair_duration = exponential(REPAIR_RATE)
            self._push(Event(self.clock + repair_duration, EventType.REPAIR_END,
                             plane_id, state.runway_id))
        else:
            takeoff_duration = max(0.0, normal(TAKEOFF_MU, TAKEOFF_SIGMA2))
            self._push(Event(self.clock + takeoff_duration, EventType.TAKEOFF_END,
                             plane_id, state.runway_id))

    # ------------------------------------------------------------------
    # event handlers
    # ------------------------------------------------------------------

    def _handle_arrival(self) -> None:
        """A new plane arrives. Assign runway if available, else queue."""
        plane_id = self.next_plane_id
        self.next_plane_id += 1

        # schedule next arrival (only if within simulation time)
        next_arrival = self.clock + exponential(ARRIVAL_RATE)
        if next_arrival <= SIMULATION_TIME:
            self._push(Event(next_arrival, EventType.ARRIVAL, -1))

        runway = self._free_runway()
        if runway != -1:
            self._assign_runway(plane_id, runway)
        else:
            self.arrival_queue.append(plane_id)

    def _handle_landing_end(self, plane_id: int) -> None:
        state = self.planes[plane_id]
        state.landing_done = True
        self._try_takeoff(plane_id)

    def _handle_refuel_end(self, plane_id: int) -> None:
        state = self.planes[plane_id]
        state.refuel_done = True
        self._try_takeoff(plane_id)

    def _handle_unload_end(self, plane_id: int) -> None:
        state = self.planes[plane_id]
        state.unload_done = True
        self._try_takeoff(plane_id)

    def _handle_repair_end(self, plane_id: int) -> None:
        state = self.planes[plane_id]
        state.repair_done = True
        # now proceed to takeoff
        takeoff_duration = max(0.0, normal(TAKEOFF_MU, TAKEOFF_SIGMA2))
        self._push(Event(self.clock + takeoff_duration, EventType.TAKEOFF_END,
                         plane_id, state.runway_id))

    def _handle_takeoff_end(self, plane_id: int, runway_id: int) -> None:
        """Plane leaves. Free runway and assign to next waiting plane if any."""
        del self.planes[plane_id]
        self.runways[runway_id] = False
        self.runway_last_freed[runway_id] = self.clock

        if self.arrival_queue:
            next_plane = self.arrival_queue.popleft()
            self._assign_runway(next_plane, runway_id)

    # ------------------------------------------------------------------
    # main loop
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, object]:
        # schedule first arrival
        first_arrival = exponential(ARRIVAL_RATE)
        if first_arrival <= SIMULATION_TIME:
            self._push(Event(first_arrival, EventType.ARRIVAL, -1))

        while self.event_queue:
            event = self._pop()

            # stop processing arrivals past simulation horizon;
            # continue processing departures until runways empty
            if event.etype == EventType.ARRIVAL and event.time > SIMULATION_TIME:
                continue
            if event.etype != EventType.ARRIVAL and not self.planes and not self.arrival_queue:
                break

            self.clock = event.time

            if event.etype == EventType.ARRIVAL:
                self._handle_arrival()
            elif event.etype == EventType.LANDING_END:
                self._handle_landing_end(event.plane_id)
            elif event.etype == EventType.REFUEL_END:
                self._handle_refuel_end(event.plane_id)
            elif event.etype == EventType.UNLOAD_END:
                self._handle_unload_end(event.plane_id)
            elif event.etype == EventType.REPAIR_END:
                self._handle_repair_end(event.plane_id)
            elif event.etype == EventType.TAKEOFF_END:
                self._handle_takeoff_end(event.plane_id, event.runway_id)

        # accumulate idle time for runways still free at end
        for i in range(NUM_RUNWAYS):
            if not self.runways[i]:
                self.runway_free_time[i] += self.clock - self.runway_last_freed[i]

        return {
            "runway_idle_minutes": self.runway_free_time,
            "total_planes_served": self.next_plane_id - 1 - len(self.arrival_queue),
            "planes_still_in_queue": len(self.arrival_queue),
            "simulation_end_time": self.clock,
        }
