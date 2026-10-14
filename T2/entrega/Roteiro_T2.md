# Roteiro do vídeo – T2

Integrantes: Artur Lemos Pereira, Raul Neves Pedroso, Humberto Corrêa Gomes. Duração-alvo: 9 min 10 s.

## Slide 1 – Capa

**Artur Lemos Pereira** (~25 s)

Olá, somos Artur Lemos Pereira, Raul Neves Pedroso e Humberto Corrêa Gomes. Neste trabalho modelamos uma assistência técnica hipotética como uma rede de três filas, simulamos com o simulador da T1 e testamos uma melhoria no reparo. Eu começo pelo problema, o Raul apresenta a análise do cenário inicial e o Humberto mostra a melhoria e a conclusão.

## Slide 2 – A realidade modelada

**Artur Lemos Pereira** (~40 s)

A realidade escolhida é uma assistência técnica de equipamentos. Cada cliente da rede é uma ordem de serviço, ou seja, um equipamento. Ele passa pela triagem, segue para o reparo e depois para o teste; se o teste reprova, volta ao reparo. É um cenário hipotético: os tempos são premissas nossas, não dados de uma empresa real. A pergunta é onde a rede trava e qual mudança simples reduz espera e perdas. Vamos ao desenho da rede.

## Slide 3 – Rede inicial

**Artur Lemos Pereira** (~60 s)

A triagem, Q1, é G/G/1/5: um atendente, capacidade 5 contando quem está em atendimento, serviço uniforme entre 2 e 4 minutos. As chegadas externas ocorrem só na triagem, a cada 5 a 7 minutos, com a primeira em 6. Todo equipamento vai para o reparo, Q2, G/G/1/8, com serviço de 6 a 10 minutos, e todo reparado vai para o teste, Q3, G/G/1/5, de 2 a 4 minutos. Do teste, 20% retornam ao reparo, pela seta de retorno embaixo, e 80% saem da rede. Se a fila de destino está cheia, o equipamento é perdido, ou seja, encaminhado definitivamente para fora. A disciplina é FIFO.

## Slide 4 – Método de simulação

**Artur Lemos Pereira** (~50 s)

Usamos o simulador da T1 com 1.000.000 números aleatórios por replicação. Cada cenário teve 10 replicações, sementes 42 a 51, totalizando 20 execuções. A rede começa vazia e não descartamos aquecimento. Como cada execução termina num tempo diferente, 1.411.699,19 minutos no inicial e 1.043.673,87 no melhorado com a semente 42, comparamos taxas por hora, não contagens brutas. A semente 42 é o caso principal; o resumo das 10 sementes vem no fim. Agora o Raul explica os cálculos.

## Slide 5 – Fórmulas e unidades (M9)

**Raul Neves Pedroso** (~55 s)

Obrigado, Artur. Usamos as fórmulas do M9. Pi i é a fração do tempo no estado i: tempo acumulado dividido pelo tempo total. A população média N é a soma de pi i vezes i, incluindo quem está em atendimento. O serviço médio é a mais b sobre dois e mi é o inverso; no estado i, a taxa mi i é o mínimo entre i e c, vezes mi. A vazão D é a soma de pi i vezes mi i, o mesmo que mi vezes B, o número médio de servidores ocupados. A utilização U é B sobre c, por servidor, e o tempo de resposta W é N sobre D, em minutos por visita. Conferimos as fórmulas com as imagens do M9 fornecidas pelo grupo. No reparo, o serviço médio de 8 minutos dá 7,5 atendimentos por hora por técnico; com 2 técnicos, a capacidade sobe para 15,0 por hora.

## Slide 6 – Probabilidades – cenário inicial

**Raul Neves Pedroso** (~45 s)

Esta tabela traz a probabilidade de todos os estados das três filas no cenário inicial; o traço indica estado acima da capacidade. Na triagem e no teste o sistema fica entre zero e um equipamento. No reparo, a massa está no topo: 36,8127% do tempo com 7 e 63,1206% com 8, a capacidade máxima. Atenção: a fração de tempo com a fila cheia não é a probabilidade de perda, porque as chegadas não são Poisson.

## Slide 7 – Índices – cenário inicial

**Raul Neves Pedroso** (~45 s)

No reparo, a utilização é 100,00% e a população média N é 7,63. O tempo de resposta W é 61,04 minutos por visita, contra 3,00 na triagem e 3,00 no teste. Foram 94.045 perdas no reparo em 1.411.699,19 minutos, ou 3,9971 perdas por hora. Triagem e teste registraram 0 e 0 perdas.

## Slide 8 – Diagnóstico: o reparo é o gargalo

**Raul Neves Pedroso** (~40 s)

O gargalo é o reparo. Ele recebe as ordens da triagem e ainda os retornos do teste, mas um técnico atende em média 7,5 por hora. Com utilização de 100,00%, a fila fica cheia e as perdas aparecem. Triagem e teste têm folga, com 50,04% e 37,49%. Por isso a melhoria deve atacar o reparo. Passo para o Humberto.

## Slide 9 – Rede melhorada

**Humberto Corrêa Gomes** (~30 s)

Obrigado, Raul. Na rede melhorada mudamos um único parâmetro: o reparo passa de 1 para 2 técnicos, virando G/G/2/8. A capacidade 8 continua igual, assim como chegadas, serviços e rotas, inclusive o retorno de 20%.

## Slide 10 – Probabilidades – cenário melhorado

**Humberto Corrêa Gomes** (~25 s)

Com 2 técnicos, a distribuição do reparo se desloca para baixo: o estado vazio tem 0,4374% e o estado cheio aparece em apenas 0,0193% do tempo. As regras da tabela são as mesmas do inicial.

## Slide 11 – Índices – cenário melhorado

**Humberto Corrêa Gomes** (~25 s)

No melhorado, a utilização média por técnico do reparo é 83,30%, a população média N cai para 2,04 e o tempo de resposta W para 9,78 minutos. Houve 12 perdas em 1.043.673,87 minutos, 0,000690 por hora: raras, mas não eliminadas.

## Slide 12 – Comparação: reparo e efeito no teste

**Humberto Corrêa Gomes** (~40 s)

No reparo, W varia -83,97%, de 61,04 para 9,78 minutos por visita, e as perdas por hora variam -99,98%. A utilização por técnico cai 16,7 pontos percentuais. O teste recebe mais fluxo: a vazão estimada D de Q3 vai de 7,50 para 12,50 por hora e seu W de 3,00 para 3,33 minutos. Não somamos os W das filas como tempo de rede, porque com retornos um equipamento pode visitar reparo e teste mais de uma vez; e o D do reparo inclui revisitas, não é o número de equipamentos únicos concluídos.

## Slide 13 – Robustez: 10 sementes

**Humberto Corrêa Gomes** (~25 s)

Nas 10 sementes, o W do reparo ficou entre 61,04 e 61,05 minutos no inicial, média 61,04, e entre 9,72 e 9,78 no melhorado, média 9,75. As perdas por hora seguem o mesmo sentido. É um resumo descritivo, sem intervalo de confiança.

## Slide 14 – Conclusão, custo e limites

**Humberto Corrêa Gomes** (~30 s)

Neste modelo hipotético, o segundo técnico no reparo reduz fortemente espera e perdas. O custo é um técnico adicional, que não estimamos em dinheiro. A simulação não prova rentabilidade nem que uma empresa real se comportaria assim. Limites: modelo hipotético, tempos uniformes supostos, sem aquecimento, e a vazão D é estimada pela ocupação, não contada.

## Slide 15 – Referências e próximos passos

**Humberto Corrêa Gomes** (~15 s)

As referências são o M9 do professor Afonso Sales, o simulador da T1, a análise da T2 e o texto do MIT sobre a lei de Little. Obrigado pela atenção.

## Checklist de gravação

- [ ] Ensaiar a apresentação inteira com cronômetro (alvo de 8 a 10 minutos).
- [ ] Abrir Apresentacao_T2.pptx no PowerPoint e iniciar a apresentação de slides.
- [ ] No Zoom, iniciar a reunião com os três integrantes e compartilhar a janela da apresentação.
- [ ] Conferir o áudio de cada integrante antes de gravar.
- [ ] Gravar a reunião; cada integrante fala nos slides indicados neste roteiro.
- [ ] Revisar a gravação inteira (áudio, slides visíveis, duração).
- [ ] Publicar no YouTube como não listado e testar o link em uma janela anônima.
- [ ] Criar T2/entrega/VIDEO.txt com o link real e apagar VIDEO_PENDENTE.txt.
- [ ] Reconstruir o ZIP (python T2/gerar_entrega.py zip) antes de enviar no Moodle.

O vídeo ainda não foi gravado nem publicado; o link real entra em T2/entrega/VIDEO.txt.
