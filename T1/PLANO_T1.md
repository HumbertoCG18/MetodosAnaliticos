# Entrega T1 de redes de filas

Fonte: `T1_Enunciado.md`, `imagem_t1.png` e o modelo Word fornecido.

## Diagnóstico verificado

- O simulador existente em `../simulador_fila.py` já aceita redes e roteamento probabilístico, mas exige capacidade finita (linhas 117–118) e sua CLI carrega apenas JSON (linha 352).
- A T1 exige Q1 G/G/1 sem limite de capacidade, Q2 G/G/2/5 e Q3 G/G/2/10. Primeira chegada em 2,0 minutos, sistema vazio e encerramento ao consumir o 100.000º aleatório.
- Baseline: `python -B -m unittest -v`, na pasta pai, passou 16/16 testes em 29/09/2026.
- Git: branch `main`, HEAD `54883099d66ec10474d01c9811b1dc5bc5653c8d`; `T1/` já estava não rastreada. Nenhum código foi alterado.
- Consulta de issues abertas em `HumbertoCG18/MetodosAnaliticos` retornou lista vazia.

## Plano para aprovação no Gate 1

1. Reutilizar o simulador existente em uma cópia de entrega na T1; acrescentar capacidade ilimitada sem teto artificial e entrada YAML, preservando JSON. Antes de implementar, abrir issue e preparar branch do escopo.
2. Configurar chegadas externas U(2,4) em Q1; serviços U(1,2), U(4,6) e U(5,15); rotas Q1→Q2 0,2, Q1→Q3 0,8, Q2→Q1 0,3, Q2→Q3 0,5 e Q3→Q2 0,7. Probabilidades restantes representam saída da rede.
3. Validar capacidade ilimitada, ciclos, perdas, estados, conservação do tempo e parada exata em 100.000 aleatórios; usar semente 42, explicitamente documentada, pois o enunciado não define gerador/semente.
4. Executar a configuração T1 e salvar resultados completos e instruções reproduzíveis de uso; realizar uma revisão independente Astra do código.
5. Preencher cópia do modelo Word com estudantes, link do código, resultados das três filas e tempo total; gerar PDF e conferir visualmente todas as páginas.

## Aceite

- Código-fonte e configuração executáveis, instruções de uso e resultados da T1.
- Q1 realmente ilimitada; topologia da imagem preservada.
- Exatamente 100.000 aleatórios consumidos e primeira chegada em 2,0.
- Tempos acumulados, probabilidades por estado, perdas por fila e tempo global presentes.
- Soma dos tempos de cada fila igual ao tempo global, probabilidades somando 1 dentro de tolerância numérica.
- Modelo original preservado e DOCX/PDF preenchidos e renderizados.
- Compatibilidade com o módulo 3 só será afirmada após acesso à sua referência.

## Rota e pendências

- T2: integração de capacidade ilimitada, entrada, simulação e artefatos; risco moderado, confiança alta no diagnóstico local.
- Investigação/coordenação: agente ativo. Implementação concluída: Claude Opus 5/high solicitado e observado. Revisão Astra/medium concluída e aprovada, uma tentativa consumida.
- Gate 1 e Gate 2 aprovados pelo usuário em 29/09/2026. Commit, push, PR e merge expressamente autorizados na mesma sessão.
- Nomes reutilizados do modelo M6 anterior: Artur Lemos Pereira, Raul Neves Pedroso e Humberto Corrêa Gomes. Falta caminho/link do simulador/formato do módulo 3.
- Runtime empacotado localizado. Sem LibreOffice no bundle Windows, PDF exportado pelo Word e renderizado pelo Poppler; duas páginas finais conferidas visualmente.
- Escrita fora da pasta T1 e alterações no Git da pasta pai exigem permissão do sandbox.

## Rascunho de issue

Título: Entregar simulador de redes de filas e validação T1

O enunciado T1 exige uma rede com Q1 ilimitada, três filas e retornos probabilísticos. O simulador existente aceita apenas capacidades finitas e entrada JSON. Reutilizar o motor, acrescentar capacidade ilimitada e entrada YAML, fornecer configuração e resultados reproduzíveis com 100.000 aleatórios e primeira chegada em 2,0, instruções de uso e DOCX/PDF conforme o modelo fornecido. Validar invariantes e preservar os cenários já existentes. Compatibilidade com módulo 3 depende de acesso à referência.
