# LH Nautical — Desafio de Dados

Projeto de pipeline de dados completo desenvolvido para o desafio da LH Nautical. Abrange desde a **ingestão e EDA** dos dados brutos até **modelos de IA** (previsão e recomendação) e um **dashboard HTML** interativo.

---

## Estrutura do Projeto

```
nautical/
├── 1-lh_nautical_csv/          # Dados brutos (24 CSVs)
│
├── 01_eda.py                   # EDA e qualidade dos dados
├── 02_tratamento_modelagem.py  # Limpeza e modelagem (Fato + Dim)
├── 03_analise_vendas_clientes.py # Analise de vendas e CLV
├── 04_previsao_recomendacao.py # Previsao (Holt-Winters/statsmodels) + Recomendacao (SVD) + RFM
├── 05_dashboard.py             # Dashboard HTML auto-contido
├── run_all.py                  # Executa o pipeline completo
│
├── processed/                  # Tabelas limpas (gerado automaticamente)
│   ├── dim_customers.csv
│   ├── dim_products.csv
│   ├── dim_locations.csv
│   ├── dim_calendar.csv
│   ├── fato_vendas.csv
│   ├── fato_payments.csv
│   ├── fato_returns.csv
│   └── fato_stock.csv
│
└── outputs/
    ├── figures/                # Graficos PNG gerados
    ├── reports/                # CSVs com resultados das analises
    └── dashboard_lh_nautical.html  # Dashboard final
```

---

## Como Executar

### Opção 1 — Pipeline Completo (recomendado)
```bash
python run_all.py
```

### Opção 2 — Etapas individualmente
```bash
python 01_eda.py                    # EDA e qualidade
python 02_tratamento_modelagem.py   # Limpeza e modelagem
python 03_analise_vendas_clientes.py# Analise de vendas
python 04_previsao_recomendacao.py  # Previsao e recomendacao
python 05_dashboard.py              # Gera o dashboard
```

---

## Dependências

```bash
pip install pandas matplotlib scikit-learn numpy statsmodels scikit-surprise
# Opcional (camada Silver em banco relacional — consultas analíticas rápidas):
pip install duckdb
```

---

## Modelo de Dados (Star Schema)

```
         dim_customers
              |
dim_calendar--+--fato_vendas--dim_products
              |
         dim_locations
```

A tabela **fato_vendas** é o centro do modelo, integrando:
- `orders.csv` + `order_items.csv` = cada linha é um item de um pedido
- Custo do produto (de `product_variants.csv`)
- Cálculo de `gross_profit` e `margin_pct` para cada linha

---

## O que cada script entrega

| Script | Stakeholder | Entregável |
|--------|-------------|-----------|
| `01_eda.py` | Gabriel Santos | Mapeamento de schema, % nulos, volume de dados |
| `02_tratamento_modelagem.py` | Gabriel Santos | 4 dimensões + 4 fatos limpos |
| `03_analise_vendas_clientes.py` | Marina Costa + Sr. Almir | 7 análises + 8 gráficos + 6 CSVs |
| `04_previsao_recomendacao.py` | Gabriel + Marina | Previsão 90 dias (Holt-Winters), RFM, Recomendações SVD |
| `05_dashboard.py` | Todos | Dashboard HTML com KPIs e todos os gráficos |

---

## Decisões de Tratamento de Dados

| Campo | Decisão | Justificativa |
|-------|---------|---------------|
| `customers.trade_name` nulo | Preenchido com `legal_name` | PF não tem nome fantasia |
| `addresses.complement` nulo | String vazia `""` | Campo opcional por natureza |
| `orders.salesperson_id` nulo | Mantido nulo | Pedidos ecommerce sem vendedor |
| `payments.paid_at` nulo | Mantido nulo | Pagamento pendente (análise de inadimplência) |
| `employees.termination_date` nulo | Mantido nulo | Colaborador ativo não tem data de demissão |

---

## Analises Geradas

### Vendas
- Receita, lucro e margem por ano (2020–2026)
- Distribuição por canal (ecommerce, POS, loja física)
- **Vendas médias por dia da semana** (com zeros para dias sem venda)
- **Ranking de produtos com prejuízo** (margem bruta negativa)

### Clientes
- **Top 20 clientes por lucro acumulado** (Customer Lifetime Value)
- **Segmentação RFM**: Champions, Loyal, Potential, At Risk, Lost

### Previsão
- Projeção de receita diária para os próximos 90 dias
- Usa **Holt-Winters (Exponential Smoothing)** via `statsmodels` — MAPE ~13%
- Captura tendência de crescimento e sazonalidade automaticamente

### Recomendação
- Sistema de filtragem colaborativa via SVD (`scikit-surprise`)
- Top 5 recomendações por cliente, excluindo produtos já comprados
