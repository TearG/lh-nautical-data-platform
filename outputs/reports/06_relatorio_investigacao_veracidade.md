# Relatório de Investigação de Veracidade dos Dados - LH Nautical

> *Documento gerado automaticamente após anomalias levantadas na camada de validação Gold.*

### 1. Investigação da Taxa de Devolução (0.48%)
- **Receita Total (Pedidos Pagos/Entregues):** R$ 1,225,732,784.05
- **Valor Total Devolvido:** R$ 5,881,260.49
- **Taxa Global:** 0.48%

**Análise por Ano:**

| Ano | Receita | Valor Devolvido | Taxa (%) |
|---|---|---|---|
| 2020 | R$ 111,320,746.30 | R$ 517,834.14 | 0.47% |
| 2021 | R$ 127,471,340.70 | R$ 620,670.78 | 0.49% |
| 2022 | R$ 147,383,725.45 | R$ 557,634.17 | 0.38% |
| 2023 | R$ 168,100,270.07 | R$ 701,106.10 | 0.42% |
| 2024 | R$ 192,103,996.95 | R$ 1,232,260.34 | 0.64% |
| 2025 | R$ 224,123,071.77 | R$ 1,039,926.41 | 0.46% |
| 2026 | R$ 255,229,632.81 | R$ 1,129,053.00 | 0.44% |

**Conclusão:** A taxa é uniformemente baixa em todos os anos. Em varejo náutico, 0.48% é extremamente baixo, indicando que ou o processo de logística reversa é falho (itens não são devolvidos no sistema) ou os dados são sintéticos e não modelaram o comportamento realista de defeitos/arrependimento (tipicamente 2% a 5%).

### 2. Investigação da Cobertura de NF-e (73%)
- **Receita Total (Pipeline):** R$ 1,225,732,784.05 (41700 pedidos)
- **Receita Total (NF-e Autorizadas):** R$ 905,770,161.72 (31583 pedidos)
- **Diferença de Receita:** R$ 319,962,622.33
- **Pedidos Pagos/Entregues SEM NF-e Autorizada:** 10117

**Status dos pedidos sem NF-e:**

| Status do Pedido | Qtd Pedidos SEM NF-e |
|---|---|
| confirmed | 7335 |
| paid | 2782 |

**Conclusão:** Há 10117 pedidos confirmados, pagos ou entregues que simplesmente não possuem uma NF-e com status 'authorized'. Isso explica a discrepância de 35% na receita (já que os testes comparavam valores diretamente). O pipeline financeiro (caixa) tem faturamento maior que o fiscal. **Isso é um risco gravíssimo de compliance.**

### 3. Investigação da Distribuição (Pareto)
- **Top 20% Clientes representam:** 27.7% da receita.
- **Para atingir 80% da receita precisa-se de:** 71.2% dos clientes.

- **Top 20% Produtos representam:** 37.4% da receita.
- **Para atingir 80% da receita precisa-se de:** 57.4% dos produtos.

**Conclusão:** Num varejo B2B normal, a proporção é 80/20 (20% dos clientes fazem 80% da receita). Aqui vemos que para atingir 80% da receita, precisamos de ~71% dos clientes. Isso é uma linha reta quase perfeita (distribuição uniforme). O Sr. Almir pode ficar tranquilo com o risco de concentração, mas tecnicamente isso comprova que **a massa de dados é sintética e gerada aleatoriamente sem pesos de Pareto**.

### 4. Melhoria no Modelo de Previsão de Demanda
Comparamos o modelo básico de Média Móvel com o **Holt-Winters (Suavização Exponencial com Tendência)** nos últimos 3 meses conhecidos da base.

| Modelo | MAPE (Erro Médio) | Mês 1 Prev | Mês 2 Prev | Mês 3 Prev |
|---|---|---|---|---|
| **Real** | - | R$ 22,142,017 | R$ 28,349,752 | R$ 33,840,861 |
| **Média Móvel** | 51.2% | R$ 13,315,844 | R$ 13,315,844 | R$ 13,315,844 |
| **Holt-Winters** | 13.1% | R$ 19,534,025 | R$ 24,402,728 | R$ 29,271,431 |

**Conclusão:** O modelo de Holt-Winters reconheceu a tendência de alta recente dos dados e reduziu substancialmente o erro de 51.2% para 13.1%. Recomenda-se substituir a Média Móvel por Holt-Winters (Statsmodels) ou Prophet no pipeline produtivo.

