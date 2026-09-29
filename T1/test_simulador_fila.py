import io
import json
import runpy
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import simulador_fila
from simulador_fila import simulate

# Referências externas, apenas comparação manual; PRNG de origem não especificado:
# G/G/1/5: 211717.3019, 5865, 0.00%, 0.01%, 0.01%, 0.36%, 47.90%, 51.72%.
# G/G/2/5: 199847.9066, 0, 2.05%, 83.33%, 14.62%.


def network_config(q2_capacity=5):
    return {
        "queues": {
            "Q1": {
                "servers": 2,
                "capacity": 3,
                "service": (4.0, 5.0),
                "external_arrival": (1.0, 5.0),
            },
            "Q2": {
                "servers": 1,
                "capacity": q2_capacity,
                "service": (1.0, 3.0),
            },
        },
        "routes": {"Q1": [{"to": "Q2", "probability": 1.0}]},
    }


class SequenceRandom:
    def __init__(self, values):
        self.values = iter(values)

    def uniform(self, _lo, _hi):
        return next(self.values)

    def random(self):
        raise AssertionError("a route with probability 1.0 must not draw")


class ScriptedRandom:
    """uniform() returns the interval lower bound; route draws follow a script."""

    def __init__(self, route_samples=()):
        self.route_samples = iter(route_samples)
        self.route_draws = 0

    def uniform(self, lo, _hi):
        return lo

    def random(self):
        self.route_draws += 1
        return next(self.route_samples)


def growing_queue_config(capacity):
    """One slow server fed by faster arrivals, so the queue keeps growing."""
    return {
        "queues": {
            "Q1": {
                "servers": 1,
                "capacity": capacity,
                "service": (10.0, 10.0),
                "external_arrival": (1.0, 1.0),
                "first_arrival": 1.0,
            }
        }
    }


def cycle_config():
    """Q1 and Q2 hand customers back and forth, each hop costing one route draw."""
    return {
        "queues": {
            "Q1": {
                "servers": 1,
                "capacity": None,
                "service": (5.0, 5.0),
                "external_arrival": (1000.0, 1000.0),
                "first_arrival": 1.0,
            },
            "Q2": {
                "servers": 1,
                "capacity": None,
                "service": (3.0, 3.0),
            },
        },
        "routes": {
            "Q1": [{"to": "Q2", "probability": 0.5}],
            "Q2": [{"to": "Q1", "probability": 0.5}],
        },
    }


class SimulatorQueueTests(unittest.TestCase):
    def run_scenario(self, servers):
        return simulate(servers, 5, 3, 5, 4, 5, 100000, seed=42)

    def assert_probabilities(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for observed, target in zip(actual, expected):
            self.assertAlmostEqual(observed, target, places=12)

    def test_first_arrival_is_seeded_uniform_draw(self):
        result = self.run_scenario(1)

        self.assertAlmostEqual(result["accumulated"][0], 4.278853596915767)

    def test_requires_at_least_two_integer_random_draws(self):
        for total_randoms in (0, 1, 2.1, float("inf")):
            with self.subTest(
                total_randoms=total_randoms
            ), self.assertRaisesRegex(
                ValueError, "total_randoms must be an integer of at least 2"
            ):
                simulate(1, 5, 3, 5, 4, 5, total_randoms, seed=42)

    def test_accepts_two_random_draws(self):
        result = simulate(1, 5, 3, 5, 4, 5, 2, seed=42)

        self.assertEqual(result["randoms_used"], 2)

    def test_network_first_customer_is_fixed_and_budget_is_inclusive(self):
        result = simulador_fila.simulate_network(network_config(), 2, seed=42)

        self.assertEqual(result["randoms_used"], 2)
        self.assertEqual(result["global_time"], 2.5)
        self.assertEqual(set(result["queues"]), {"Q1", "Q2"})
        self.assertEqual(len(result["queues"]["Q1"]["accumulated"]), 4)
        self.assertEqual(len(result["queues"]["Q2"]["accumulated"]), 6)

    def test_network_uses_all_100000_random_numbers(self):
        result = simulador_fila.simulate_network(network_config(), 100000, seed=42)

        self.assertEqual(result["randoms_used"], 100000)

    def test_network_requires_a_mapping_config(self):
        with self.assertRaises(TypeError):
            simulador_fila.simulate_network(None, 1, 42)

    def test_network_releases_all_departures_before_transfers_at_a_tie(self):
        config = {
            "queues": {
                "Q1": {
                    "servers": 1,
                    "capacity": 1,
                    "service": (5.0, 5.0),
                    "external_arrival": (10.0, 10.0),
                    "first_arrival": 2.5,
                },
                "Q2": {
                    "servers": 1,
                    "capacity": 1,
                    "service": (5.0, 5.0),
                    "external_arrival": (10.0, 10.0),
                    "first_arrival": 2.5,
                },
            },
            "routes": {"Q1": [{"to": "Q2", "probability": 1.0}]},
        }
        rng = SequenceRandom([5.0, 10.0, 5.0, 10.0, 5.0])
        with patch("simulador_fila.random.Random", return_value=rng):
            result = simulador_fila.simulate_network(config, 5, seed=42)

        self.assertEqual(result["queues"]["Q2"]["losses"], 0)

    def test_network_rejects_non_finite_intervals_and_first_arrival(self):
        for field, value in (
            ("service", float("nan")),
            ("service", float("inf")),
            ("external_arrival", float("nan")),
            ("external_arrival", float("inf")),
            ("first_arrival", float("nan")),
            ("first_arrival", float("inf")),
        ):
            config = network_config()
            config["queues"]["Q1"][field] = (
                value if field == "first_arrival" else (value, value)
            )
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                simulador_fila._validated_network(config)

    def test_network_requires_a_positive_first_arrival(self):
        config = network_config()
        config["queues"]["Q1"]["first_arrival"] = 0.0

        with self.assertRaises(ValueError):
            simulador_fila.simulate_network(config, 1, 42)

    def test_partial_route_draws_once_and_can_exit_the_network(self):
        class RouteRandom:
            def __init__(self):
                self.route_draws = 0
                self.uniform_values = iter([4.0, 10.0, 4.0])

            def uniform(self, _lo, _hi):
                return next(self.uniform_values)

            def random(self):
                self.route_draws += 1
                return 0.75

        config = network_config()
        config["routes"] = {"Q1": [{"to": "Q2", "probability": 0.5}]}
        rng = RouteRandom()
        with patch("simulador_fila.random.Random", return_value=rng):
            result = simulador_fila.simulate_network(config, 4, seed=42)

        self.assertEqual(rng.route_draws, 1)
        self.assertEqual(result["queues"]["Q2"]["accumulated"][1], 0.0)

    def test_self_route_never_starts_more_services_than_servers(self):
        class ServiceCountingRandom:
            def __init__(self):
                self.service_draws = 0
                self.values = iter([5.0, 1.0, 5.0, 5.0, 5.0])

            def uniform(self, lo, hi):
                if (lo, hi) == (5.0, 5.0):
                    self.service_draws += 1
                return next(self.values)

            def random(self):
                raise AssertionError("a route with probability 1.0 must not draw")

        config = {
            "queues": {
                "Q1": {
                    "servers": 1,
                    "capacity": 3,
                    "service": (5.0, 5.0),
                    "external_arrival": (1.0, 10.0),
                    "first_arrival": 2.5,
                }
            },
            "routes": {"Q1": [{"to": "Q1", "probability": 1.0}]},
        }
        rng = ServiceCountingRandom()
        with patch("simulador_fila.random.Random", return_value=rng):
            simulador_fila.simulate_network(config, 5, seed=42)

        self.assertEqual(rng.service_draws, 2)

    def test_network_counts_source_and_destination_losses_without_route_draws(self):
        rng = SequenceRandom([4.0, 1.0, 4.0, 1.0, 1.0, 5.0, 3.0, 4.0, 1.0])
        with patch("simulador_fila.random.Random", return_value=rng):
            result = simulador_fila.simulate_network(network_config(q2_capacity=1), 9, seed=42)

        self.assertEqual(result["randoms_used"], 9)
        self.assertEqual(result["queues"]["Q1"]["losses"], 1)
        self.assertEqual(result["queues"]["Q2"]["losses"], 1)
        self.assertEqual(result["queues"]["Q2"]["accumulated"][1], 3.0)

    def test_network_processes_departures_before_arrivals_at_a_tie(self):
        rng = SequenceRandom([4.0, 4.0, 3.0, 4.0, 5.0, 1.0])
        with patch("simulador_fila.random.Random", return_value=rng):
            result = simulador_fila.simulate_network(network_config(), 6, seed=42)

        self.assertEqual(result["queues"]["Q2"]["accumulated"][1], 3.0)

    def test_cli_uses_feedback_labels(self):
        output = io.StringIO()
        with redirect_stdout(output):
            runpy.run_path("simulador_fila.py", run_name="__main__")

        rendered = output.getvalue()
        for label in (
            "Queue:   Q1 (G/G/1/5)",
            "Queue:   Q1 (G/G/2/5)",
            "Arrival: 3.0 ... 5.0",
            "Service: 4.0 ... 5.0",
            "Number of losses:",
            "Simulation average time:",
        ):
            with self.subTest(label=label):
                self.assertIn(label, rendered)
        self.assertNotIn("Queue:   Q2", rendered)
        second_queue = rendered.split("Queue:   Q1 (G/G/2/5)", maxsplit=1)[1]
        for state in (3, 4, 5):
            with self.subTest(state=state):
                self.assertNotIn(f"  {state}    |", second_queue)

    def test_gg_1_5_matches_seeded_reference_statistics(self):
        result = self.run_scenario(1)

        self.assertEqual(result["randoms_used"], 100000)
        self.assertAlmostEqual(result["total_time"], 211827.48226167043, places=9)
        self.assertEqual(result["losses"], 5815)
        self.assert_probabilities(
            result["probs"],
            [
                2.019970945804898e-05,
                4.711390714056254e-05,
                7.902871600519334e-05,
                0.0034964761178986276,
                0.47993325306209017,
                0.5164239284874074,
            ],
        )

    def test_gg_2_5_matches_seeded_reference_statistics(self):
        result = self.run_scenario(2)

        self.assertEqual(result["randoms_used"], 100000)
        self.assertAlmostEqual(result["total_time"], 199920.7343204156, places=9)
        self.assertEqual(result["losses"], 0)
        self.assert_probabilities(
            result["probs"],
            [
                0.020762398112648052,
                0.8327874912736258,
                0.14645011061372606,
                0.0,
                0.0,
                0.0,
            ],
        )
        self.assertEqual(result["accumulated"][3:], [0.0, 0.0, 0.0])


class UnlimitedCapacityTests(unittest.TestCase):
    def test_unlimited_queue_grows_past_a_known_finite_capacity(self):
        unlimited = simulador_fila.simulate_network(growing_queue_config(None), 8, seed=42)
        limited = simulador_fila.simulate_network(growing_queue_config(3), 8, seed=42)

        queue = unlimited["queues"]["Q1"]
        self.assertIsNone(queue["capacity"])
        self.assertEqual(queue["losses"], 0)
        self.assertEqual(len(queue["accumulated"]), 8)
        self.assertEqual(queue["accumulated"], [1.0] * 7 + [0.0])
        self.assertEqual(len(limited["queues"]["Q1"]["accumulated"]), 4)
        self.assertEqual(limited["queues"]["Q1"]["losses"], 4)

    def test_unlimited_queue_conserves_time_across_visited_states(self):
        result = simulador_fila.simulate_network(growing_queue_config(None), 8, seed=42)

        queue = result["queues"]["Q1"]
        self.assertEqual(result["global_time"], 7.0)
        self.assertAlmostEqual(sum(queue["accumulated"]), result["global_time"])
        self.assertAlmostEqual(sum(queue["probs"]), 1.0)
        self.assertEqual(queue["probs"][-1], 0.0)

    def test_capacity_must_be_null_or_at_least_the_server_count(self):
        for capacity in (0, -1, 2.0, True, "10"):
            config = growing_queue_config(capacity)
            config["queues"]["Q1"]["servers"] = 3
            with self.subTest(capacity=capacity), self.assertRaisesRegex(
                ValueError, "Q1.capacity"
            ):
                simulador_fila._validated_network(config)

    def test_unlimited_queue_is_reported_without_a_capacity_limit(self):
        result = simulador_fila.simulate_network(growing_queue_config(None), 8, seed=42)
        config = growing_queue_config(None)

        rendered = simulador_fila.format_network_result(config, result)

        self.assertIn("Queue:   Q1 (G/G/1)", rendered)
        self.assertNotIn("None", rendered)


class CyclicRoutingTests(unittest.TestCase):
    def simulate_cycle(self, total_randoms):
        rng = ScriptedRandom([0.1] * 5)
        with patch("simulador_fila.random.Random", return_value=rng):
            return rng, simulador_fila.simulate_network(cycle_config(), total_randoms, seed=42)

    def test_customers_cycle_back_and_each_hop_costs_one_route_draw(self):
        rng, result = self.simulate_cycle(8)

        self.assertEqual(rng.route_draws, 3)
        self.assertEqual(result["randoms_used"], 8)
        self.assertEqual(result["global_time"], 14.0)
        self.assertEqual(result["queues"]["Q1"]["accumulated"], [4.0, 10.0])
        self.assertEqual(result["queues"]["Q2"]["accumulated"], [11.0, 3.0])

    def test_budget_stops_exactly_on_the_route_draw(self):
        rng, result = self.simulate_cycle(3)

        self.assertEqual(rng.route_draws, 1)
        self.assertEqual(result["randoms_used"], 3)
        self.assertEqual(result["global_time"], 6.0)
        self.assertEqual(result["queues"]["Q2"]["accumulated"], [6.0, 0.0])


class ConfigurationInputTests(unittest.TestCase):
    def test_yaml_and_json_configs_describe_the_same_network(self):
        from_yaml = simulador_fila.load_config("rede_t1.yml")
        from_json = simulador_fila.load_config("rede_t1.json")

        self.assertEqual(from_yaml, from_json)
        self.assertIsNone(from_yaml["queues"]["Q1"]["capacity"])
        self.assertEqual(
            simulador_fila.simulate_network(from_yaml, 500, seed=42),
            simulador_fila.simulate_network(from_json, 500, seed=42),
        )

    def test_yaml_is_parsed_safely_and_must_be_a_mapping(self):
        with tempfile.TemporaryDirectory() as folder:
            unsafe = Path(folder, "unsafe.yaml")
            unsafe.write_text("!!python/object/apply:os.system ['echo']\n", encoding="utf-8")
            with self.assertRaises(Exception) as unsafe_error:
                simulador_fila.load_config(unsafe)
            self.assertNotIsInstance(unsafe_error.exception, SystemExit)

            scalar = Path(folder, "scalar.yml")
            scalar.write_text("just-a-string\n", encoding="utf-8")
            with self.assertRaisesRegex(TypeError, "mapping"):
                simulador_fila.load_config(scalar)

    def test_cli_writes_the_text_report_and_a_complete_json_report(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder, "small.yml")
            config.write_text(
                "simulation:\n"
                "  randoms: 4\n"
                "  seed: 42\n"
                "queues:\n"
                "  Qa:\n"
                "    servers: 1\n"
                "    service: [2.0, 2.0]\n"
                "    external_arrival: [3.0, 3.0]\n"
                "    first_arrival: 1.0\n",
                encoding="utf-8",
            )
            text_out = Path(folder, "out.txt")
            json_out = Path(folder, "out.json")
            stdout = io.StringIO()
            argv = ["simulador_fila.py", str(config), str(text_out), str(json_out)]
            with patch.object(sys, "argv", argv), redirect_stdout(stdout):
                runpy.run_path("simulador_fila.py", run_name="__main__")
            printed = stdout.getvalue()
            written = text_out.read_text(encoding="utf-8")
            report = json.loads(json_out.read_text(encoding="utf-8"))

        self.assertIn("Queue:   Qa (G/G/1)", printed)
        self.assertEqual(written, printed)
        self.assertEqual(report["randoms_used"], 4)
        self.assertEqual(report["global_time"], 4.0)
        self.assertEqual(report["queues"]["Qa"]["accumulated"], [2.0, 2.0])
        self.assertEqual(report["queues"]["Qa"]["losses"], 0)
        self.assertIsNone(report["queues"]["Qa"]["capacity"])


class T1NetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = simulador_fila.load_config("rede_t1.yml")
        simulation = cls.config["simulation"]
        cls.result = simulador_fila.simulate_network(
            cls.config, simulation["randoms"], simulation["seed"]
        )

    def test_stops_on_the_hundred_thousandth_random(self):
        self.assertEqual(self.result["randoms_used"], 100000)

    def test_queue_shapes_follow_the_assignment(self):
        queues = self.result["queues"]

        self.assertEqual(
            [(queues[name]["servers"], queues[name]["capacity"]) for name in ("Q1", "Q2", "Q3")],
            [(1, None), (2, 5), (2, 10)],
        )
        self.assertEqual(len(queues["Q2"]["accumulated"]), 6)
        self.assertEqual(len(queues["Q3"]["accumulated"]), 11)
        # Q1 has no ceiling: it reports exactly the states it visited, all of them occupied
        self.assertGreater(len(queues["Q1"]["accumulated"]), queues["Q1"]["servers"] + 1)
        self.assertTrue(all(time > 0.0 for time in queues["Q1"]["accumulated"]))

    def test_unlimited_queue_never_loses_customers(self):
        self.assertEqual(self.result["queues"]["Q1"]["losses"], 0)

    def test_each_queue_conserves_the_global_time(self):
        self.assertGreater(self.result["global_time"], 0.0)
        for name, queue in self.result["queues"].items():
            with self.subTest(queue=name):
                self.assertAlmostEqual(
                    sum(queue["accumulated"]), self.result["global_time"], places=6
                )
                self.assertAlmostEqual(sum(queue["probs"]), 1.0, places=12)

    def test_system_starts_empty_until_the_first_arrival_at_two(self):
        self.assertGreaterEqual(self.result["queues"]["Q1"]["accumulated"][0], 2.0)


if __name__ == "__main__":
    unittest.main()
