# Simulador de redes de filas — T1

Simulador de eventos discretos para redes de filas com topologia arbitrária,
roteamento probabilístico, múltiplos servidores e capacidade finita **ou ilimitada**.
A entrada pode ser um arquivo `.yml`/`.yaml` ou `.json`.

Arquivos principais:

| Arquivo | Conteúdo |
| --- | --- |
| `simulador_fila.py` | Simulador e interface de linha de comando |
| `test_simulador_fila.py` | Suíte de testes (`unittest`, biblioteca padrão) |
| `rede_t1.yml` / `rede_t1.json` | Modelo da T1 (mesma rede nos dois formatos) |
| `resultado_t1.txt` / `resultado_t1.json` | Resultado da simulação exigida pelo enunciado |
| `requirements.txt` | Dependência externa (apenas PyYAML) |

## Requisitos e instalação

- Python 3.11 (testado em 3.11.9). Nenhuma outra dependência para entrada JSON.
- **PyYAML** é necessário apenas para ler arquivos `.yml`/`.yaml`.

Verifique se já está instalado:

```bash
python -c "import yaml; print(yaml.__version__)"
```

Se o comando falhar com `ModuleNotFoundError`, instale:

```bash
pip install -r requirements.txt
# ou, equivalentemente:
pip install pyyaml
```

Ao tentar ler um `.yml` sem PyYAML, o simulador encerra com a mensagem
`reading YAML requires PyYAML; install it with: pip install pyyaml`.

## Como executar

Na pasta `T1`:

```bash
# 1) simulação da T1, imprimindo o relatório na tela
python simulador_fila.py rede_t1.yml

# 2) gravando também o relatório em texto
python simulador_fila.py rede_t1.yml resultado_t1.txt

# 3) gravando o relatório em texto e o resultado completo em JSON
python simulador_fila.py rede_t1.yml resultado_t1.txt resultado_t1.json

# a mesma rede em JSON produz exatamente a mesma saída
python simulador_fila.py rede_t1.json
```

Argumentos posicionais: `<configuração> [saída .txt] [saída .json]`.
Os dois primeiros argumentos mantêm o comportamento anterior; o terceiro é opcional.
Sem argumentos, `python simulador_fila.py` executa os dois exemplos de fila única
(G/G/1/5 e G/G/2/5) usados nas entregas anteriores.

Para rodar os testes:

```bash
python -B -m unittest -v
```

## Esquema do arquivo de entrada

O mesmo esquema vale para YAML e JSON — `rede_t1.yml` e `rede_t1.json` são o mesmo
modelo escrito nos dois formatos e produzem saída idêntica.

```yaml
simulation:            # opcional
  randoms: 100000      # orçamento de números aleatórios (padrão 100000)
  seed: 42             # semente do gerador (padrão 42)

queues:                # obrigatório, ao menos uma fila
  Q1:
    servers: 1                   # obrigatório, inteiro >= 1
    capacity: null               # null ou ausente = ilimitada; senão inteiro >= servers
    service: [1.0, 2.0]          # obrigatório, intervalo uniforme [mín, máx], 0 < mín <= máx
    external_arrival: [2.0, 4.0] # opcional; sem ele a fila só recebe clientes por roteamento
    first_arrival: 2.0           # opcional (padrão 2.5), só vale com external_arrival
  Q2:
    servers: 2
    capacity: 5
    service: [4.0, 6.0]

routes:                # opcional; ausente = cliente sai da rede ao ser atendido
  Q1:
    - to: Q2
      probability: 0.2
    - to: Q3
      probability: 0.8
```

Regras de validação (erros levantam `ValueError`/`TypeError` com mensagem indicando o campo):

- `servers`: inteiro estritamente positivo (booleanos são rejeitados).
- `capacity`: `null`/ausente para fila ilimitada, ou inteiro `>= servers`.
  **A capacidade inclui os clientes em atendimento** (uma `G/G/2/5` comporta 2 em
  serviço e 3 esperando).
- `service` e `external_arrival`: pares `[mín, máx]` finitos, com `mín > 0` e `máx >= mín`.
  `NaN` e `Infinity` são rejeitados.
- `first_arrival`: número finito e positivo.
- Pelo menos uma fila precisa ter `external_arrival`.
- Cada rota aponta para uma fila existente e tem `probability` entre 0 e 1.
  A soma das probabilidades de uma origem não pode passar de 1; **a diferença para 1
  representa a saída da rede**. Exemplo: `Q3 → Q2` com 0,7 significa 0,3 de saída.

## Números aleatórios, semente e parada

- Gerador: `random.Random(seed)` da biblioteca padrão do Python (Mersenne Twister),
  com `rng.uniform(mín, máx)` para tempos e `rng.random()` para roteamento.
  **O enunciado não especifica gerador nem semente**; adotamos `seed = 42`,
  declarada no arquivo de entrada, para que o resultado seja reproduzível.
- Consomem **um** aleatório: cada início de atendimento, cada intervalo entre
  chegadas externas e cada decisão de roteamento probabilístico.
- **Não** consomem aleatório: a primeira chegada (`first_arrival`, valor fixo),
  as rotas determinísticas (destino único com probabilidade exatamente 1,0) e a
  saída da rede quando a origem não tem rotas configuradas.
- A contagem é **inclusiva**: ao utilizar o 100.000º aleatório a simulação para
  imediatamente, sem sortear mais nada. Isso vale inclusive quando o último
  aleatório é o do roteamento — o cliente é encaminhado ao destino (ou perdido,
  se o destino estiver lotado), mas nenhum atendimento novo é iniciado.

## Política de empates

Quando vários eventos ocorrem no mesmo instante, a ordem é:

1. **Todas** as saídas agendadas para aquele instante são liberadas primeiro,
   desocupando os servidores.
2. Só então os clientes liberados são roteados e novos atendimentos iniciam.
   Assim, uma transferência nunca é perdida por um lugar que acabou de vagar.
3. Por último são tratadas as chegadas externas daquele mesmo instante
   (saída tem prioridade sobre chegada).

Entre saídas simultâneas, a ordem é a de agendamento (heap `(tempo, sequência)`),
o que torna o desempate determinístico e reprodutível.

## Estatísticas reportadas

Para cada fila: tempo acumulado em cada estado, probabilidade do estado
(tempo acumulado / tempo global) e número de clientes perdidos. Ao final,
o tempo global da simulação e o total de aleatórios utilizados.

Em filas de capacidade finita, os estados vão de 0 até a capacidade.
Em filas **ilimitadas**, a lista cresce conforme os estados são visitados e
reporta todos os estados de 0 até o maior estado alcançado; estados superiores
nunca visitados simplesmente não existem no relatório, e um estado alcançado
no instante final aparece com tempo 0.

## Resultado da T1

Rede do `imagem_t1.png`: Q1 `G/G/1` ilimitada com chegadas externas U(2,4) e
primeira chegada em 2,0; Q2 `G/G/2/5`; Q3 `G/G/2/10`; filas inicialmente vazias;
100.000 aleatórios; `seed = 42`.

| Fila | Config. | Perdas | Estados reportados |
| --- | --- | --- | --- |
| Q1 | G/G/1 (ilimitada) | 0 | 0 a 4 |
| Q2 | G/G/2/5 | 6 | 0 a 5 |
| Q3 | G/G/2/10 | 11.725 | 0 a 10 |

Tempo global: **50.819,9152** — aleatórios utilizados: **100.000**.
Os tempos acumulados e as probabilidades por estado estão em `resultado_t1.txt`
(texto) e `resultado_t1.json` (completo, para reuso programático).
Em cada fila a soma dos tempos acumulados reproduz o tempo global
(desvio máximo observado: 7,3e-12) e as probabilidades somam 1.

## Arquivos para entrega

O documento preenchido está em `output/T1_Entrega_Rede_de_Filas.docx`; o PDF para
envio está em `output/pdf/T1_Entrega_Rede_de_Filas.pdf`. O pacote
`output/T1_Entrega.zip` reúne código, testes, entradas, resultados, instruções e
documentos. Extraia o ZIP e execute os comandos acima na pasta `T1`.

Código e documentos da T1 ficam na [pasta T1 do repositório do grupo](https://github.com/HumbertoCG18/MetodosAnaliticos/tree/main/T1).

## Limitações conhecidas

- **Não foi possível comparar com o simulador do módulo 3**: a referência não foi
  disponibilizada a este repositório. Portanto **não afirmamos equivalência
  numérica com nenhum simulador externo**. Resultados de outro simulador
  divergirão sempre que o gerador pseudoaleatório, a semente, a ordem de consumo
  dos aleatórios ou a política de empate forem diferentes — mesmo com o modelo idêntico.
- Os valores aqui são de **uma única replicação** com semente fixa; não há
  intervalos de confiança nem descarte de período transitório (warm-up).
- Os tempos seguem distribuição uniforme; outras distribuições não são suportadas.
- A disciplina de atendimento é FIFO por ordem de agendamento, com servidores
  idênticos dentro de cada fila.
