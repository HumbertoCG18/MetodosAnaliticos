import io
import runpy
import unittest
from contextlib import redirect_stdout
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


if __name__ == "__main__":
    unittest.main()
