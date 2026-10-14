import copy
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analise  # noqa: E402

MODELO_INICIAL_ESPERADO = {
    "simulation": {"randoms": 1000000, "seed": 42},
    "queues": {
        "Q1": {
            "servers": 1,
            "capacity": 5,
            "service": [2.0, 4.0],
            "external_arrival": [5.0, 7.0],
            "first_arrival": 6.0,
        },
        "Q2": {"servers": 1, "capacity": 8, "service": [6.0, 10.0]},
        "Q3": {"servers": 1, "capacity": 5, "service": [2.0, 4.0]},
    },
    "routes": {
        "Q1": [{"to": "Q2", "probability": 1.0}],
        "Q2": [{"to": "Q3", "probability": 1.0}],
        "Q3": [{"to": "Q2", "probability": 0.2}],
    },
}


def carregar(cenario):
    return analise.simulador.load_config(analise.MODELOS[cenario])


class CalcularIndicesTest(unittest.TestCase):
    def test_multiservidor_distingue_utilizacao_de_ocupacao(self):
        fila = {"servers": 2, "capacity": 3, "accumulated": [1.0, 2.0, 3.0, 4.0], "losses": 5}
        indices = analise.calcular_indices(fila, [6.0, 10.0], 10.0)

        for obtido, esperado in zip(indices["p"], [0.1, 0.2, 0.3, 0.4]):
            self.assertAlmostEqual(obtido, esperado)
        self.assertAlmostEqual(indices["L"], 2.0)
        self.assertAlmostEqual(indices["B"], 1.6)
        self.assertAlmostEqual(indices["U"], 0.8)
        self.assertAlmostEqual(indices["prob_ocupado"], 0.9)
        self.assertAlmostEqual(indices["E_S"], 8.0)
        self.assertAlmostEqual(indices["mu"], 0.125)
        self.assertAlmostEqual(indices["X"], 0.2)
        self.assertAlmostEqual(indices["X_h"], 12.0)
        self.assertAlmostEqual(indices["R"], 10.0)
        self.assertAlmostEqual(indices["perdas_h"], 30.0)

    def test_fila_ociosa_tem_tempo_de_resposta_indefinido(self):
        fila = {"servers": 1, "capacity": 5, "accumulated": [7.0, 0, 0, 0, 0, 0], "losses": 0}
        indices = analise.calcular_indices(fila, [2.0, 4.0], 7.0)

        self.assertEqual(indices["L"], 0)
        self.assertEqual(indices["U"], 0)
        self.assertEqual(indices["X"], 0)
        self.assertIsNone(indices["R"])
        self.assertEqual(indices["perdas_h"], 0)

    def test_rejeita_entradas_invalidas(self):
        fila = {"servers": 1, "capacity": 1, "accumulated": [1.0, 1.0], "losses": 0}
        for servico, tempo in (([2.0, 4.0], 0.0), ([4.0, 2.0], 2.0), ([2.0, 4.0], 5.0)):
            with self.subTest(servico=servico, tempo=tempo):
                with self.assertRaises(ValueError):
                    analise.calcular_indices(fila, servico, tempo)


class ModelosTest(unittest.TestCase):
    def test_modelo_inicial_segue_enunciado(self):
        self.assertEqual(carregar("inicial"), MODELO_INICIAL_ESPERADO)

    def test_melhoria_altera_somente_servidores_de_q2(self):
        esperado = copy.deepcopy(carregar("inicial"))
        esperado["queues"]["Q2"]["servers"] = 2
        self.assertEqual(carregar("melhorado"), esperado)

    def test_probabilidades_e_tempos_se_conservam(self):
        for cenario in analise.MODELOS:
            resultado = analise.analisar(carregar(cenario), 5000, 42)
            for nome, fila in resultado["queues"].items():
                with self.subTest(cenario=cenario, fila=nome):
                    self.assertAlmostEqual(sum(fila["probs"]), 1.0)
                    self.assertAlmostEqual(sum(fila["accumulated"]), resultado["global_time"], places=6)
                    self.assertAlmostEqual(sum(resultado["indices"][nome]["p"]), 1.0)


class ReprodutibilidadeTest(unittest.TestCase):
    def test_mesma_semente_reproduz_e_perdas_sao_por_hora(self):
        config = carregar("inicial")
        primeiro = analise.analisar(config, 20000, 7)
        self.assertEqual(primeiro, analise.analisar(config, 20000, 7))
        self.assertLessEqual(primeiro["randoms_used"], 20000)
        for nome, fila in primeiro["queues"].items():
            self.assertAlmostEqual(
                primeiro["indices"][nome]["perdas_h"],
                60 * fila["losses"] / primeiro["global_time"],
            )

    def test_executar_grava_replicacoes_e_resumo(self):
        with tempfile.TemporaryDirectory() as pasta:
            analise.executar(pasta, sementes=(42, 43), randoms=3000)
            for cenario in analise.MODELOS:
                dados = json.loads((Path(pasta) / f"{cenario}.json").read_text(encoding="utf-8"))
                self.assertEqual([r["seed"] for r in dados["replicacoes"]], [42, 43])
                u = dados["resumo"]["Q2"]["U"]
                self.assertLessEqual(u["min"], u["media"])
                self.assertLessEqual(u["media"], u["max"])
            with open(Path(pasta) / "resumo.csv", encoding="utf-8", newline="") as arquivo:
                linhas = list(csv.DictReader(arquivo))
            self.assertEqual({linha["cenario"] for linha in linhas}, set(analise.MODELOS))


if __name__ == "__main__":
    unittest.main()
