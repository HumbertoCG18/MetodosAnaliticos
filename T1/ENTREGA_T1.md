# Entrega T1

Entrega local concluída em 29/09/2026 na branch `feature/t1-rede-filas`, HEAD de partida `54883099d66ec10474d01c9811b1dc5bc5653c8d`, issue https://github.com/HumbertoCG18/MetodosAnaliticos/issues/1.

## Arquivos

- `output/pdf/T1_Entrega_Rede_de_Filas.pdf`: documento final, duas páginas A4 conferidas visualmente.
- `output/T1_Entrega_Rede_de_Filas.docx`: modelo preenchido, com o original preservado.
- `output/T1_Entrega.zip`: 11 arquivos, contendo código, testes, configuração YAML/JSON, resultados, instruções, imagem da rede e DOCX/PDF.

## Resultado e validação

- 100.000 aleatórios, semente 42, primeira chegada em 2,0 minutos, filas inicialmente vazias.
- Tempo global: 50.819,91524012156 minutos; perdas: Q1=0, Q2=6, Q3=11.725.
- 30/30 testes passaram; Ruff sem erros. YAML e JSON produziram resultados idênticos. Maior desvio entre soma dos tempos de uma fila e tempo global: 7,276e-12.
- Única revisão Astra concluída: APROVADO; orçamento instrumentado de 1 a 1.000 consumido exatamente, sem ultrapassagem.
- Todas as 22 linhas de estados do PDF conferem com os resultados JSON. Apenas os nomes e os cinco slots de resposta foram alterados no modelo Word; estilos, imagens, relações e seção foram preservados.

## Pendências

O simulador do módulo 3 não foi fornecido; nenhuma comparação externa ou equivalência com esse simulador foi afirmada. Código e documentos ficam em https://github.com/HumbertoCG18/MetodosAnaliticos/tree/main/T1. O PDF está pronto para o usuário enviar no CARD T1 da disciplina.

Commit, push, PR e merge foram autorizados pelo usuário em 29/09/2026. Mensagem de commit: `feat(t1): entregar simulador de redes de filas e validação`.
