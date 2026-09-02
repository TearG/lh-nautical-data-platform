# AI Project Spec - LH Nautical Data Pipeline
> **Contexto para Agentes AI (Brain Dump)**
> Quando retornar a este repositório, leia este documento para recuperar instantaneamente o contexto da arquitetura, decisões técnicas e problemas conhecidos.

## 1. O Projeto
O projeto **LH Nautical** é uma pipeline completa de Engenharia e Ciência de Dados (ETL -> Análise -> Previsão -> Dashboard) de um varejo náutico fictício com 6 anos de histórico.

O objetivo do código é ser **limpo, comentado, tipado** e resiliente, focando em responder problemas de negócios reais para 3 personas:
- **Gabriel Santos (Tech Lead):** Quer código limpo, fallback strategies, testes automatizados e arquitetura robusta.
- **Marina Costa (Negócios):** Quer analisar vendas, margem, CLV, recomendação de produtos e segmentação (RFM).
- **Sr. Almir (Fundador):** Quer reconciliação financeira perfeita (Pedido = Pagamento = NF-e) e mitigação de riscos de negócio.

## 2. A Arquitetura (Medallion)
- `1-lh_nautical_csv/` **(Bronze):** 24 CSVs brutos (ex: orders, order_items, fiscal_invoices, returns, variants).
- `processed/` **(Silver):** 16 tabelas limpas (4 dim core + 3 fato core + dim_employees, dim_suppliers, dim_addresses, dim_product_attributes, dim_product_suppliers, dim_stock_levels + fato_compras, fato_fiscal).
- `outputs/reports/` **(Gold):** CSVs finais agregados (KPIs).
- `outputs/dashboard_lh_nautical.html`: Dashboard Plotly exportado em standalone HTML.
- `tests/`: Suíte Pytest com **242 validações** estruturais, de negócio e de veracidade estatística (9 arquivos de teste, todos usando paths relativos portáveis).

## 3. Decisões Técnicas e "Pegadinhas"
1. **Modelagem SVD (Recomendação):** Utilizamos a biblioteca `surprise`. Cuidado ao mapear os IDs de usuário e itens, que são inteiros contínuos em vez de hashes, facilitando.
2. **Previsão de Demanda (Holt-Winters):** O projeto começou com um fallback de Média Móvel, pois o `prophet` é instável de instalar no Windows. Evoluímos o script para usar o **`statsmodels`** (`ExponentialSmoothing`) que reduziu o MAPE para ~13%. **Sempre use statsmodels** ao mexer nas previsões deste projeto.
3. **Encoding:** Os CSVs brutos têm caracteres latinos (`latin1` / `cp1252`). As funções de leitura no `01_eda.py` lidam com fallback de encoding para evitar crash.
4. **Devoluções:** Na Fato de Devoluções, o arquivo bruto (`returns.csv`) mapeia as datas usando a coluna `created_at` e não `returned_at`. 
5. **NF-e Faltando:** O Sr. Almir foi avisado que existem mais de 10.000 pedidos sem NF-e autorizada (Divergência caixa vs fiscal). Não corrija os dados brutos: isso é uma descoberta de auditoria.
6. **Integração Total (Fase 2):** O pipeline consome exatamente **100% dos 24 arquivos brutos**. Até tabelas auxiliares (`attributes`, `variant_attribute_values`, `product_suppliers` e `goods_receipt_items`) foram modeladas para não deixar nenhum gap analítico (RH, Logística e Fiscal).
7. **Exportação para Colab:** Há um script `convert_to_ipynb.py` que condensa os 6 scripts `.py` do pipeline (01 a 07) e o dashboard em um único arquivo `LH_Nautical_Colab.ipynb`, adaptando dinamicamente os caminhos (de Windows absoluto para Linux relativo) para rodar nativamente no Google Colab.
8. **Revisão de QA Final (Pré-Entrega):** Foram removidos caminhos absolutos hardcoded nos testes (`test_01`, `test_03`, `test_07`, `test_08`) para garantir portabilidade (`Path(__file__).parent.parent`). O pipeline foi expandido com o `test_09_fase2_outputs.py` para cobrir os relatórios da Fase 2, totalizando **242 testes**. A lógica de reconciliação de vendedores no script 07 considera receita bruta (todos os status), o que difere propositalmente do CLV (que usa apenas pagos).

## 4. Próximos Passos (Se o projeto for continuado)
- Integrar a pipeline com `DuckDB` ou `SQLite` em vez de gravar CSVs intermediários na pasta Silver.
- Criar DAGs (Airflow/Prefect) ou orquestrador local mais robusto que o atual `run_all.py`.
- Otimizar o script de join da Tabela Fato de Vendas, que pode consumir muita RAM caso os dados passem de 1 milhão de linhas.

*Fim do Brain Dump.*
