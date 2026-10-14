# T2 — Rede de filas de uma assistência técnica

Integrantes: Artur Lemos Pereira, Raul Neves Pedroso e Humberto Corrêa Gomes.

Issue: [#3](https://github.com/HumbertoCG18/MetodosAnaliticos/issues/3).

## Enunciado aceito

Modelar uma rede de filas hipotética, simulá-la com o simulador da T1, calcular índices
de desempenho, propor uma melhoria e comparar os dois cenários.

Clientes = ordens de serviço/equipamentos. Tempos em minutos.

| Fila | Papel | Modelo | Serviço | Chegada externa |
|---|---|---|---|---|
| Q1 | triagem | G/G/1/5 | U(2, 4) | U(5, 7), primeira em 6 |
| Q2 | reparo | G/G/1/8 | U(6, 10) | — |
| Q3 | teste | G/G/1/5 | U(2, 4) | — |

Roteamento: Q1→Q2 100%; Q2→Q3 100%; Q3→Q2 20% (retrabalho), 80% sai da rede.

Melhoria (única mudança): Q2 passa de 1 para 2 servidores; capacidade de Q2 continua 8.

Arquivos: `modelo_inicial.yml`, `modelo_melhorado.yml` (esquema YAML da T1,
`simulation.randoms = 1000000`, `simulation.seed = 42`).

## Premissas

- Capacidade inclui quem está em atendimento; disciplina FIFO.
- Cliente que chega a uma fila cheia é perdido definitivamente (não retorna).
- Rede começa vazia; sem período de aquecimento (warmup) descartado.
- Parada: orçamento de 1.000.000 aleatórios por replicação (critério da T1).
- 10 replicações por cenário, sementes 42..51; semente 42 é o caso principal (slides).

## Como reproduzir

Requer Python 3 e `pip install -r T2/requirements.txt` (PyYAML para a análise;
python-pptx, openpyxl e reportlab para os artefatos; PyMuPDF só nos testes).

```
python T2/analise.py                                   # gera T2/resultados/
python T2/gerar_entrega.py                             # gera T2/entrega/ a partir dos JSON
python T2/gerar_entrega.py zip                         # T2/Entrega_T2.zip (exige o PDF da apresentação)
python -m unittest discover -s T2 -p "test_*.py" -v    # testes
```

`gerar_entrega.py` não roda simulação: lê `resultados/*.json`. Saídas em `T2/entrega/`:

- `Apresentacao_T2.pptx`: 15 slides editáveis (formas, tabelas e gráficos nativos), com
  as falas do roteiro nas notas do apresentador.
- `Indices_T2.xlsx`: dados brutos da semente 42 e fórmulas (π_i, N, B, U, D, W,
  perdas_h), comparação e replicações (valores exportados; média/mín/máx por fórmula).
- `Roteiro_T2.md` e `Roteiro_T2.pdf`: fala por slide, orador, tempo-alvo e checklist de
  gravação.
- `VIDEO_PENDENTE.txt`: substituir por `VIDEO.txt` com o link real após gravar.
- `Apresentacao_T2.pdf`: exportado do PPTX pelo PowerPoint (fora do script).

O ZIP contém `T2/` (fontes, testes, YAML, requirements, README, resultados, entrega) e
`T1/simulador_fila.py`, sem `__pycache__`, `.workflow`, logs, temporários e o próprio ZIP.

Os caminhos são relativos ao script; funciona a partir de qualquer diretório.
Importar `analise` não executa simulação.

Saídas em `T2/resultados/`:

- `inicial.json`, `melhorado.json`: configuração, resultado completo de cada replicação
  (tempos acumulados por estado, probabilidades, perdas, tempo global, aleatórios usados),
  índices por fila e resumo.
- `resumo.csv`: média, mínimo e máximo de cada métrica entre as replicações e o valor da
  semente 42, para conferência.

## Índices e unidades

Para cada fila com `c` servidores, capacidade `K`, tempo total simulado `T` (min) e
serviço U(a, b). Os artefatos usam a notação do M9 (N, D, U, W); o código, o JSON e o CSV
mantêm as chaves originais.

| M9 | Chave no código/JSON | Fórmula por estado (i = 1..K) | Unidade |
|---|---|---|---|
| π_i | `p[i]` | tempo no estado i / T | fração do tempo |
| N | `L` | Σ π_i·i | clientes |
| μ | `mu` | 1 / E[S], E[S] = (a + b)/2 (`E_S`) | atendimentos/min/servidor |
| μ_i | — | min(i, c)·μ | atendimentos/min |
| D | `X` | Σ π_i·μ_i = μ·B | atendimentos/min (estimativa) |
| D_h | `X_h` | 60·D | atendimentos/h (estimativa) |
| U | `U` | Σ π_i·min(i, c)/c = B/c | utilização média por servidor |
| W | `R` | N / D (D por minuto) | min por visita (estimativa); indefinido se D = 0 |
| B (auxiliar) | `B` | Σ π_i·min(i, c) | servidores ocupados (média) |
| — | `prob_ocupado` | 1 − π_0 | fração do tempo com alguém na fila |
| — | `perdas_h` | 60·perdas / T | perdas/h observadas |

O estado 0 contribui 0 nas somas, então somar de 0 ou de 1 dá o mesmo resultado. Logo
`analise.py` coincide com o M9: N = L, D = X = μ·B, U = B/c, W = R = N/D. A planilha usa
as mesmas fórmulas; só os cabeçalhos mudaram (aba Replicacoes: N, B, U, D_h, W, perdas,
perdas_h correspondem a `L`, `B`, `U`, `X_h`, `R`, `perdas`, `perdas_h`).

Conferência: as fórmulas foram conferidas com as imagens do M9 fornecidas pelo grupo (Prof.
Afonso Sales, M9 – Avaliação de um Modelo Simulado, PUCRS 2026/2,
https://moodle.pucrs.br/course/view.php?id=94492). É uma conferência de fórmulas, não uma
validação numérica do motor de simulação.

Cuidados de interpretação:

- U ≠ 1 − π_0 quando c > 1.
- D é estimativa da vazão local via ocupação e serviço médio, não contagem medida de
  conclusões; inclui revisitas (Q3→Q2), portanto não é a saída definitiva da rede.
- W = N/D (Little) é estimativa de longo prazo do tempo por visita, não por ordem.
- P(K) (fração do tempo com a fila cheia) não é a probabilidade de perda: as chegadas não
  são Poisson. A perda é informada como taxa observada (perdas_h) e contagem.
- O resumo entre replicações é descritivo (média/mín/máx), não intervalo de confiança.

## Limites

- Modelo hipotético; parâmetros não vêm de dados reais.
- Sem warmup: o transiente inicial (rede vazia) entra nas médias.
- Resumo entre sementes descritivo, sem intervalo de confiança; custo do técnico adicional
  não estimado.

## Referências locais

- `T1/simulador_fila.py`: motor reutilizado via `importlib` (`simulate_network`,
  `load_config`); não há cópia do simulador na T2.
- `T1/rede_t1.yml`: exemplo do esquema YAML.

## Pendências

- Exportar o PDF da apresentação, gravar e publicar o vídeo, criar `entrega/VIDEO.txt` e
  reconstruir o ZIP.
