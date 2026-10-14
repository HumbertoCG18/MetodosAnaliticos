"""T2 - análise dos cenários de assistência técnica sobre o simulador da T1.

Uso: python analise.py  (de qualquer diretório; grava em T2/resultados/).
"""

import csv
import importlib.util
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent
RESULTADOS = BASE / "resultados"
MODELOS = {
    "inicial": BASE / "modelo_inicial.yml",
    "melhorado": BASE / "modelo_melhorado.yml",
}
SEMENTES = tuple(range(42, 52))

# Reutiliza o motor da T1 sem copiá-lo.
_spec = importlib.util.spec_from_file_location(
    "simulador_fila", BASE.parent / "T1" / "simulador_fila.py"
)
simulador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simulador)


def calcular_indices(queue_result, service, global_time):
    """Índices de desempenho de uma fila a partir dos tempos acumulados por estado.

    queue_result: dicionário da T1 (servers, accumulated, losses).
    service: intervalo [a, b] do serviço uniforme, em minutos.
    global_time: tempo total simulado T, em minutos.

    p_n = tempo no estado n / T; L = sum(n p_n); B = sum(min(n, c) p_n) servidores
    ocupados em média; U = B / c (utilização média por servidor); prob_ocupado = 1 - p_0
    (há alguém no sistema), distinta de U quando c > 1. E[S] = (a + b) / 2,
    mu = 1 / E[S] atendimentos/min/servidor. X = mu B é ESTIMATIVA da vazão local
    (atendimentos/min, inclui revisitas; não é contagem de conclusões nem saída
    definitiva da rede); X_h = 60 X. R = L / X (Little) é estimativa de longo prazo
    do tempo por visita, em minutos; None se X = 0. perdas_h = 60 perdas / T é taxa
    observada de perdas por hora (contagem/tempo, não probabilidade de perda).
    """
    if (
        isinstance(global_time, bool)
        or not isinstance(global_time, (int, float))
        or not math.isfinite(global_time)
        or global_time <= 0
    ):
        raise ValueError("global_time deve ser positivo e finito")
    c = queue_result["servers"]
    if type(c) is not int or c < 1:
        raise ValueError("servers deve ser inteiro positivo")
    a, b = service
    if not 0 < a <= b:
        raise ValueError("service deve ser intervalo positivo [a, b] com a <= b")
    tempos = queue_result["accumulated"]
    if any(t < 0 for t in tempos) or not math.isclose(sum(tempos), global_time, rel_tol=1e-6):
        raise ValueError("tempos acumulados devem ser >= 0 e somar global_time")

    p = [t / global_time for t in tempos]
    L = sum(n * pn for n, pn in enumerate(p))
    B = sum(min(n, c) * pn for n, pn in enumerate(p))
    E_S = (a + b) / 2
    mu = 1 / E_S
    X = mu * B
    losses = queue_result["losses"]
    return {
        "p": p,
        "L": L,
        "B": B,
        "U": B / c,
        "prob_ocupado": 1 - p[0],
        "E_S": E_S,
        "mu": mu,
        "X": X,
        "X_h": 60 * X,
        "R": L / X if X > 0 else None,
        "perdas": losses,
        "perdas_h": 60 * losses / global_time,
    }


def analisar(config, randoms, seed):
    """Uma replicação: resultado completo da T1 mais os índices de cada fila."""
    resultado = simulador.simulate_network(config, randoms, seed)
    T = resultado["global_time"]
    return {
        "randoms_used": resultado["randoms_used"],
        "global_time": T,
        "queues": resultado["queues"],
        "indices": {
            nome: calcular_indices(fila, config["queues"][nome]["service"], T)
            for nome, fila in resultado["queues"].items()
        },
    }


def _resumir(replicacoes):
    """Média/mín/máx entre replicações (descritivo, não intervalo de confiança)."""
    series = {"rede": {"global_time": [r["global_time"] for r in replicacoes]}}
    for nome, indices in replicacoes[0]["indices"].items():
        series[nome] = {
            m: [r["indices"][nome][m] for r in replicacoes]
            for m, v in indices.items()
            if not isinstance(v, list)
        }
    resumo = {}
    for nome, metricas in series.items():
        resumo[nome] = {}
        for m, valores in metricas.items():
            validos = [v for v in valores if v is not None]
            resumo[nome][m] = {
                "media": sum(validos) / len(validos) if validos else None,
                "min": min(validos, default=None),
                "max": max(validos, default=None),
                "n": len(validos),
                "principal": valores[0],
            }
    return resumo


def executar(destino=RESULTADOS, sementes=SEMENTES, randoms=None):
    """Roda os dois cenários; grava <cenario>.json e resumo.csv em destino.

    randoms=None usa simulation.randoms do YAML. A primeira semente é o caso principal.
    """
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    linhas = []
    for cenario, caminho in MODELOS.items():
        config = simulador.load_config(caminho)
        total = randoms or config["simulation"]["randoms"]
        replicacoes = [{"seed": s, **analisar(config, total, s)} for s in sementes]
        resumo = _resumir(replicacoes)
        dados = {
            "cenario": cenario,
            "modelo": caminho.name,
            "config": config,
            "randoms": total,
            "sementes": list(sementes),
            "semente_principal": sementes[0],
            "replicacoes": replicacoes,
            "resumo": resumo,
        }
        (destino / f"{cenario}.json").write_text(
            json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        for fila, metricas in resumo.items():
            for m, est in metricas.items():
                linhas.append([cenario, fila, m, est["media"], est["min"], est["max"], est["principal"]])

    with open(destino / "resumo.csv", "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["cenario", "fila", "metrica", "media", "min", "max", f"semente_{sementes[0]}"])
        escritor.writerows(linhas)


if __name__ == "__main__":
    executar()
    print(f"Resultados gravados em {RESULTADOS}")
