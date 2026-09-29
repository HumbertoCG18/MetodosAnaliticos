import heapq
import json
import math
import random
import sys
from pathlib import Path


def simulate(servers, capacity, arr_lo, arr_hi, svc_lo, svc_hi,
             total_randoms, seed):
    if type(total_randoms) is not int or total_randoms < 2:
        raise ValueError("total_randoms must be an integer of at least 2")

    rng = random.Random(seed)
    counter = [0]

    def draw(lo, hi):
        counter[0] += 1
        return rng.uniform(lo, hi)

    clock = 0.0
    last_event_time = 0.0
    state = 0                      # number of customers in system
    departures = []                # list of scheduled departure times (one per busy server)
    first_arrival = draw(arr_lo, arr_hi)
    next_arrival = first_arrival
    losses = 0
    accumulated = [0.0] * (capacity + 1)

    stop = False
    while counter[0] < total_randoms and not stop:
        # determine next event
        if departures:
            next_dep = min(departures)
        else:
            next_dep = None

        if next_dep is None or next_arrival <= next_dep:
            event_time = next_arrival
            event_type = 'arrival'
        else:
            event_time = next_dep
            event_type = 'departure'

        # accumulate time spent in current state up to this event
        accumulated[state] += (event_time - last_event_time)
        last_event_time = event_time
        clock = event_time

        if event_type == 'arrival':
            if state < capacity:
                state += 1
                if len(departures) < servers:
                    svc = draw(svc_lo, svc_hi)
                    departures.append(event_time + svc)
                    if counter[0] >= total_randoms:
                        stop = True
            else:
                losses += 1
            if not stop:
                interarr = draw(arr_lo, arr_hi)
                next_arrival = event_time + interarr
                if counter[0] >= total_randoms:
                    stop = True
        else:  # departure
            departures.remove(event_time)
            state -= 1
            if state > len(departures):
                svc = draw(svc_lo, svc_hi)
                departures.append(event_time + svc)
                if counter[0] >= total_randoms:
                    stop = True

    total_time = clock
    probs = [t / total_time for t in accumulated]
    return {
        'accumulated': accumulated,
        'probs': probs,
        'total_time': total_time,
        'losses': losses,
        'randoms_used': counter[0],
    }


def _interval(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{label} must contain two numbers")
    lo, hi = value
    if (
        isinstance(lo, bool)
        or isinstance(hi, bool)
        or not isinstance(lo, (int, float))
        or not isinstance(hi, (int, float))
        or not math.isfinite(lo)
        or not math.isfinite(hi)
        or lo <= 0
        or hi < lo
    ):
        raise ValueError(f"{label} must be a positive interval")
    return float(lo), float(hi)


def _validated_network(config):
    if not isinstance(config, dict) or not isinstance(config.get("queues"), dict):
        raise TypeError("config must contain a queues mapping")
    if not config["queues"]:
        raise ValueError("config must contain at least one queue")

    queues = {}
    for name, spec in config["queues"].items():
        if not isinstance(name, str) or not name or not isinstance(spec, dict):
            raise ValueError("each queue must have a name and settings")
        servers = spec.get("servers")
        capacity = spec.get("capacity")
        if type(servers) is not int or servers < 1:
            raise ValueError(f"{name}.servers must be a positive integer")
        if capacity is not None and (type(capacity) is not int or capacity < servers):
            raise ValueError(
                f"{name}.capacity must be null (unlimited) or an integer >= servers"
            )

        queue = {
            "servers": servers,
            "capacity": capacity,
            "service": _interval(spec.get("service"), f"{name}.service"),
        }
        if "external_arrival" in spec:
            queue["external_arrival"] = _interval(
                spec["external_arrival"], f"{name}.external_arrival"
            )
            first_arrival = spec.get("first_arrival", 2.5)
            if (
                isinstance(first_arrival, bool)
                or not isinstance(first_arrival, (int, float))
                or not math.isfinite(first_arrival)
                or first_arrival <= 0
            ):
                raise ValueError(f"{name}.first_arrival must be positive")
            queue["first_arrival"] = float(first_arrival)
        queues[name] = queue

    if not any("external_arrival" in queue for queue in queues.values()):
        raise ValueError("at least one queue must receive external arrivals")

    routes = {}
    for source, choices in config.get("routes", {}).items():
        if source not in queues or not isinstance(choices, list):
            raise ValueError("routes must start at configured queues")
        total_probability = 0.0
        routes[source] = []
        for choice in choices:
            if not isinstance(choice, dict) or choice.get("to") not in queues:
                raise ValueError("each route must target a configured queue")
            probability = choice.get("probability")
            if (
                isinstance(probability, bool)
                or not isinstance(probability, (int, float))
                or not 0 <= probability <= 1
            ):
                raise ValueError("route probability must be between 0 and 1")
            total_probability += probability
            routes[source].append((choice["to"], float(probability)))
        if total_probability > 1.0 + 1e-12:
            raise ValueError("route probabilities cannot sum to more than 1")
    return queues, routes


def simulate_network(config, total_randoms, seed):
    """Simulate a configured queue network until the random-number budget ends."""
    if type(total_randoms) is not int or total_randoms < 1:
        raise ValueError("total_randoms must be a positive integer")

    queue_specs, routes = _validated_network(config)
    rng = random.Random(seed)
    randoms_used = 0
    serial = 0
    clock = 0.0
    states = {name: 0 for name in queue_specs}
    busy = {name: 0 for name in queue_specs}
    losses = {name: 0 for name in queue_specs}
    accumulated = {
        # unlimited queues start with the empty state and grow as states are visited
        name: [0.0] * (1 if spec["capacity"] is None else spec["capacity"] + 1)
        for name, spec in queue_specs.items()
    }
    departures = []
    external_arrivals = []

    def push(heap, event_time, queue_name):
        nonlocal serial
        serial += 1
        heapq.heappush(heap, (event_time, serial, queue_name))

    def draw_uniform(interval):
        nonlocal randoms_used
        randoms_used += 1
        return rng.uniform(*interval)

    def choose_destination(source):
        nonlocal randoms_used
        choices = routes.get(source, [])
        if not choices:
            return None
        if len(choices) == 1 and choices[0][1] == 1.0:
            return choices[0][0]

        randoms_used += 1
        sample = rng.random()
        cumulative = 0.0
        for target, probability in choices:
            cumulative += probability
            if sample < cumulative:
                return target
        return None

    def start_service(queue_name, event_time):
        if (
            randoms_used >= total_randoms
            or busy[queue_name] >= queue_specs[queue_name]["servers"]
        ):
            return
        duration = draw_uniform(queue_specs[queue_name]["service"])
        busy[queue_name] += 1
        push(departures, event_time + duration, queue_name)

    def accept_customer(queue_name, event_time):
        capacity = queue_specs[queue_name]["capacity"]
        if capacity is not None and states[queue_name] >= capacity:
            losses[queue_name] += 1
            return
        states[queue_name] += 1
        times = accumulated[queue_name]
        if states[queue_name] >= len(times):
            times.append(0.0)
        if busy[queue_name] < queue_specs[queue_name]["servers"]:
            start_service(queue_name, event_time)

    for name, spec in queue_specs.items():
        if "external_arrival" in spec:
            push(external_arrivals, spec["first_arrival"], name)

    while randoms_used < total_randoms and (departures or external_arrivals):
        next_departure = departures[0][0] if departures else float("inf")
        next_arrival = external_arrivals[0][0] if external_arrivals else float("inf")
        event_time = min(next_departure, next_arrival)
        elapsed = event_time - clock
        for name in queue_specs:
            accumulated[name][states[name]] += elapsed
        clock = event_time

        completed_sources = []
        while departures and departures[0][0] == event_time:
            _, _, source = heapq.heappop(departures)
            busy[source] -= 1
            states[source] -= 1
            completed_sources.append(source)

        for source in completed_sources:
            destination = choose_destination(source)
            if destination is not None:
                accept_customer(destination, event_time)
            if randoms_used >= total_randoms:
                break
            if states[source] > busy[source]:
                start_service(source, event_time)
            if randoms_used >= total_randoms:
                break

        if randoms_used >= total_randoms:
            break

        while external_arrivals and external_arrivals[0][0] == event_time:
            _, _, queue_name = heapq.heappop(external_arrivals)
            accept_customer(queue_name, event_time)
            if randoms_used >= total_randoms:
                break
            interval = queue_specs[queue_name]["external_arrival"]
            push(external_arrivals, event_time + draw_uniform(interval), queue_name)
            if randoms_used >= total_randoms:
                break

    queue_results = {}
    for name, spec in queue_specs.items():
        times = accumulated[name]
        queue_results[name] = {
            "servers": spec["servers"],
            "capacity": spec["capacity"],
            "accumulated": times,
            "probs": [time / clock for time in times],
            "losses": losses[name],
        }
    return {
        "queues": queue_results,
        "global_time": clock,
        "randoms_used": randoms_used,
    }


def load_config(path):
    """Read a network configuration from a .yml/.yaml or .json file."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yml", ".yaml"):
        try:
            import yaml
        except ImportError as error:
            raise ImportError(
                "reading YAML requires PyYAML; install it with: pip install pyyaml"
            ) from error
        config = yaml.safe_load(text)
    else:
        config = json.loads(text)
    if not isinstance(config, dict):
        raise TypeError(f"{path} must contain a configuration mapping")
    return config


def format_network_result(config, result):
    lines = []
    for name, queue in result["queues"].items():
        spec = config["queues"][name]
        kendall = f"G/G/{queue['servers']}"
        if queue["capacity"] is not None:
            kendall += f"/{queue['capacity']}"
        lines.extend(["=" * 70, f"Queue:   {name} ({kendall})"])
        if "external_arrival" in spec:
            lo, hi = spec["external_arrival"]
            lines.append(f"Arrival: {lo:.1f} ... {hi:.1f}")
        else:
            lines.append("Arrival: no external arrivals")
        lo, hi = spec["service"]
        lines.extend(
            [
                f"Service: {lo:.1f} ... {hi:.1f}",
                "",
                "State               Time               Probability",
            ]
        )
        for state, (time, probability) in enumerate(
            zip(queue["accumulated"], queue["probs"])
        ):
            lines.append(f"{state:<8}{time:18.4f}{probability:22.2%}")
        lines.extend(["", f"Number of losses: {queue['losses']}", ""])
    lines.extend(
        [
            "=" * 70,
            f"Global simulation time: {result['global_time']:.4f}",
            f"Random numbers used: {result['randoms_used']}",
            "=" * 70,
        ]
    )
    return "\n".join(lines)


def _print_single_queue_examples():
    scenarios = [
        ("Q1", "G/G/1/5", 1, 5, 3, 5, 4, 5),
        ("Q1", "G/G/2/5", 2, 5, 3, 5, 4, 5),
    ]
    for queue, name, servers, cap, alo, ahi, slo, shi in scenarios:
        res = simulate(servers, cap, alo, ahi, slo, shi, 100000, seed=42)
        print("="*70)
        print(f"Queue:   {queue} ({name})")
        print(f"Arrival: {alo:.1f} ... {ahi:.1f}")
        print(f"Service: {slo:.1f} ... {shi:.1f}")
        print(f"Number of losses: {res['losses']}")
        print(f"Simulation average time: {res['total_time']:.4f}")
        print("State | Accumulated time | Probability")
        for i, (t, p) in enumerate(zip(res['accumulated'], res['probs'])):
            if t:
                print(f"  {i}    | {t:14.4f} | {p:.2%}")
        print(f"Probability sum: {sum(res['probs']):.6f}")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith((".json", ".yml", ".yaml")):
        network_config = load_config(sys.argv[1])
        simulation = network_config.get("simulation", {})
        network_result = simulate_network(
            network_config,
            simulation.get("randoms", 100000),
            simulation.get("seed", 42),
        )
        rendered = format_network_result(network_config, network_result)
        print(rendered)
        if len(sys.argv) > 2:
            Path(sys.argv[2]).write_text(rendered + "\n", encoding="utf-8")
        if len(sys.argv) > 3:
            Path(sys.argv[3]).write_text(
                json.dumps(network_result, indent=2) + "\n", encoding="utf-8"
            )
    else:
        _print_single_queue_examples()
