"""
Entry point for Barajas Airport simulation.
Runs multiple replications and reports per-runway idle time statistics.
"""

import random_vars as rv
from simulation import AirportSimulation, NUM_RUNWAYS, SIMULATION_TIME

REPLICATIONS = 30


def run_replications(n: int) -> None:
    totals = [0.0] * NUM_RUNWAYS
    planes_served_total = 0

    print(f"Running {n} replications (T = {SIMULATION_TIME:.0f} min = 1 week)\n")

    for rep in range(n):
        rv.seed(rep * 31337 + 1)
        sim = AirportSimulation()
        results = sim.run()

        idle = results["runway_idle_minutes"]
        for i in range(NUM_RUNWAYS):
            totals[i] += idle[i]
        planes_served_total += results["total_planes_served"]

        if rep == 0:
            # print detail for first replication
            print("=== Replication 1 detail ===")
            for i in range(NUM_RUNWAYS):
                pct = idle[i] / results["simulation_end_time"] * 100
                print(f"  Runway {i+1}: idle {idle[i]:8.1f} min  ({pct:.1f}%)")
            print(f"  Planes served : {results['total_planes_served']}")
            print(f"  Still in queue: {results['planes_still_in_queue']}")
            print(f"  Sim end time  : {results['simulation_end_time']:.1f} min\n")

    print("=== Averages over all replications ===")
    for i in range(NUM_RUNWAYS):
        avg = totals[i] / n
        pct = avg / SIMULATION_TIME * 100
        print(f"  Runway {i+1}: avg idle {avg:8.1f} min  ({pct:.1f}% of simulation time)")

    print(f"\n  Avg planes served per replication: {planes_served_total / n:.1f}")


if __name__ == "__main__":
    run_replications(REPLICATIONS)
