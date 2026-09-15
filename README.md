# Simulador de redes de filas

Simulador de eventos discretos para filas G/G/c/K e redes com roteamento probabilístico. Usa apenas a biblioteca padrão do Python.

## Arquivos do repositório

- `simulador_fila.py`: simulador e interface de linha de comando.
- `rede_tandem.json`: configuração solicitada para as duas filas em tandem.
- `resultado_tandem.txt`: saída reproduzível da simulação solicitada.
- `test_simulador_fila.py`: testes da fila simples e da rede tandem.
- `.gitignore`: exclui modelos, entregas e arquivos temporários do repositório.

## Executar a entrega

Requer Python 3. Execute na pasta dos arquivos:

```text
python simulador_fila.py rede_tandem.json resultado_tandem.txt
```

O comando imprime o resultado e atualiza `resultado_tandem.txt`. Sem argumentos, o programa executa os dois cenários da primeira etapa.

Para executar os testes:

```text
python -m unittest -v
```

## Sintaxe da rede

O arquivo JSON possui três blocos:

- `simulation`: quantidade de números aleatórios e semente do gerador.
- `queues`: servidores, capacidade total, intervalo de serviço e, quando houver, chegadas externas.
- `routes`: destinos e probabilidades após a saída de cada fila.

Os intervalos usam distribuição uniforme contínua. A capacidade inclui clientes em atendimento. Uma fila sem `external_arrival` não recebe clientes do exterior. A soma das probabilidades de saída pode ser menor que 1; a diferença representa a saída da rede.

Nesta entrega, o primeiro cliente chega à Q1 no instante 2,5 sem consumir número aleatório. A rota Q1 para Q2 possui probabilidade 1 e também não consome número aleatório. Uma transferência para uma fila cheia conta como perda nessa fila. Em empates, as saídas são processadas antes das chegadas externas.

O evento que usa o 100.000º número aleatório é processado e encerra imediatamente a simulação. Por isso, todos os resultados devem informar exatamente 100.000 números utilizados.
