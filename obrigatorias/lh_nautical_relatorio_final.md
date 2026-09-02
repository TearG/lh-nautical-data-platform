# LH Nautical - Relatório Final do Projeto de Dados

> **Destinatários:** 
> - Sr. Almir (Fundador)
> - Marina Costa (Gerente de Negócios)
> - Gabriel Santos (Tech Lead)
> 
> **Objetivo:** Sumarizar todo o trabalho executado, arquitetura criada, anomalias resolvidas e responder às premissas de negócio levantadas pelo time.

---

## 1. Arquitetura e Pipeline Criado

Construímos um pipeline completo de Engenharia e Ciência de Dados utilizando **Python, Pandas e Statsmodels**, focado em robustez, documentação e limpeza (atendendo à exigência do Gabriel Santos de um código sem 'caixas pretas').

### Estrutura de Camadas (Medallion Architecture adaptada):
1. **Bronze (`1-lh_nautical_csv/`)**: 24 arquivos CSV originais da empresa.
2. **Silver (`processed/`)**: Dados limpos, tipados e cruzados em um schema *Star Schema* (Tabelas Fato e Dimensões).
3. **Gold (`outputs/reports/`)**: 10 relatórios focados em KPIs de Negócio, prontos para consumo.
4. **Dashboard (`outputs/dashboard_lh_nautical.html`)**: Dashboard standalone offline com visuais premium, dark mode interativo gerado via Plotly.

### Módulos do Pipeline (`scripts/`):
- `01_eda.py`: Análise exploratória e Quality Assurance inicial.
- `02_tratamento_modelagem.py`: Limpeza de erros (conversão de encoding, preenchimento de nulos) e joins para gerar Fato de Vendas, Estoque, Pagamentos e Devoluções.
- `03_analise_vendas_clientes.py`: Geração de KPIs de Receita, Ticket Médio, Devoluções, Performance de Lojas e CLV (Customer Lifetime Value).
- `04_previsao_recomendacao.py`: Segmentação RFM, Previsão de Demanda (Holt-Winters) e Sistema de Recomendação por Filtragem Colaborativa SVD (Surprise).
- `05_dashboard.py`: Geração do HTML interativo.

---

## 2. Garantia de Qualidade (O Pedido de Testes)

Foi implementada uma suíte de testes com **197 casos de teste passando (Pytest)**, que validam não só se o código roda, mas se **a lógica de negócio está correta** (validação de veracidade e anomalias da camada Silver/Gold).

**Testes de Destaque Implementados:**
- **Perda de Dados:** Garantia matemática de que o número de pedidos no Bronze é exatamente igual no Silver após joins (Pipeline sem vazar dados).
- **Consistência Tripla Financeira:** Validamos se Pedido (Total) == Pagamento Aprovado == NF-e Emitida.
- **Anomalias de Negócio:** Bloqueio de custos zerados, estoques negativos e margens superiores a 100%.

---

## 3. Respostas aos Stakeholders (Achados da Investigação)

Através do nosso script de auditoria de veracidade (`06_investigacao_veracidade.py`), entregamos respostas diretas às preocupações do board:

### Para o Sr. Almir (Foco em Receita, Lucro, Risco e Supply Chain)
- **Risco Fiscal (Crítico):** Descobrimos **10.117 pedidos pagos/entregues que não possuem uma NF-e com status 'autorizada'**. A receita no caixa é 35% maior que a receita fiscal validada. *Recomendação urgente: Auditoria na integração entre o ERP de vendas e o emissor fiscal.*
- **Supply Chain e Fornecedores (Fase 2):** Implementamos a modelagem de *Lead Time* cruzando Ordens de Compra e Recebimentos (`fato_compras`). Agora, a diretoria consegue visualizar exatamente quais fornecedores têm o maior atraso médio (Delay Days), viabilizando negociações de SLA mais eficientes e garantindo o estoque da próxima alta temporada.
- **Concentração de Clientes (Tranquilo):** A LH Nautical não depende de poucos clientes. Os Top 20% dos clientes representam apenas 27.7% da receita, o que dilui completamente o risco existencial da empresa caso perca grandes contas.

### Para Marina Costa (Foco em Crescimento, CLV, Campanhas e Vendas Físicas)
- **Taxa de Devoluções Baixa:** A taxa global reportada é de apenas **0.48%**. Em varejo náutico, a média de mercado é entre 2% e 5%. Isso indica que a logística reversa da empresa não está dando baixa no sistema quando os itens voltam, inflando lucros irrealmente e mantendo estoque fantasma.
- **Campanhas de RFM e Recomendações:** O pipeline gerou uma segmentação onde os *Champions* estão isolados. O sistema SVD de recomendação gerou 5 produtos altamente propensos a compra para cada cliente, excluindo itens que o cliente já possui, prontos para uso no disparo de e-mails de retenção.
- **Geolocalização de Vendas e RH (Fase 2):** Ao integrar a base de endereços (`dim_addresses`) e funcionários (`dim_employees`), passamos a cruzar a Fato de Vendas para rankear os melhores vendedores do canal POS (para comissionamento) e quais Estados/Cidades têm a maior demanda, permitindo à Marina planejar a logística do frete de forma otimizada.

### Para Gabriel Santos (Foco em Arquitetura e Engenharia)
- **Melhoria no Modelo de Demanda:** A Média Móvel de 30 dias possuía uma acurácia muito baixa (MAPE 51%) devido à forte tendência de alta nos últimos meses dos dados. 
- Substituímos o cálculo ingênuo pelo modelo matemático de **Holt-Winters (Exponential Smoothing com Tendência via Statsmodels)**. O erro médio absoluto despencou de 51% para **13.1%**.
- **Natureza dos Dados:** Através do cálculo exato de Pareto (onde a receita forma uma linha de distribuição uniforme perfeita, e não a clássica curva 80/20), informamos a nível de engenharia que a base atual de dados tem comportamento *sintético gerado aleatoriamente*, e os modelos estão parametrizados adequadamente para absorver dados orgânicos (reais) em produção sem distorção.

---

## 4. O Que Foi Melhorado

1. **Correção do Custo (Cost Price vs Sale Price):** Muitos produtos apresentavam lucro 100% pois as chaves do inventário não batiam. Resolvemos via merge por `product_variant_id` e normalização das descrições.
2. **Sistema de Encodings:** Scripts otimizados para ler arquivos sem quebrar por acentos da língua portuguesa (`latin1`, `utf-8-sig`).
3. **Remoção de Prophet:** Devido a instabilidades de instalação de compiladores C++ no Windows (dependências do Prophet), fizemos o pivot com sucesso para o `statsmodels` (Holt-Winters), garantindo acurácia sem a dor de cabeça de *build chains* complexas no servidor da LH Nautical.
4. **Dashboards Dinâmicos e Independentes:** Todo o layout de visualização foi condensado num único arquivo HTML, sem depender de PowerBI ou Tableau (licenças caras) para apresentação imediata, economizando *budget* da área.

---

## 5. Como Rodar o Projeto

1. Coloque os 24 arquivos `.csv` na pasta `1-lh_nautical_csv/`.
2. Rode `python run_all.py`
3. (Para testar o pipeline): Rode `python -m pytest tests/`
4. Abra `outputs/dashboard_lh_nautical.html` no seu navegador.
