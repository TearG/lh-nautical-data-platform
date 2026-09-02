# 🚀 Portfólio / Case Study: LH Nautical Data Platform

**Cargo:** Lead Data Engineer & Data Scientist  
**Domínio:** Varejo Náutico B2B  
**Duração do Histórico de Dados:** 6 anos (2020-2026)  

---

## 📌 O Desafio
A **LH Nautical**, um varejo náutico fictício B2B, operava com seus dados fragmentados em 24 fontes distintas (arquivos CSV brutos). A diretoria enfrentava problemas clássicos de silos de dados:
* O Fundador precisava de reconciliação financeira (Caixa vs. Notas Fiscais) e visibilidade de Supply Chain.
* A área de Negócios precisava de inteligência de clientes (Segmentação, LTV e Recomendações de compra) e previsão de demanda.
* A Engenharia exigia uma arquitetura escalável, tipada, rastreável e à prova de falhas de processamento.

**Objetivo:** Construir uma Data Platform End-to-End capaz de ingerir os dados brutos, modelá-los, analisá-los, rodar algoritmos de Machine Learning e servir um dashboard executivo automatizado.

---

## 🏗️ Arquitetura da Solução (Medallion Architecture)

Implementei o pipeline utilizando o padrão **Medallion Architecture**, garantindo que o dado fosse gradativamente enriquecido e validado:

1. **🥉 Bronze Layer (`1-lh_nautical_csv/`)**: Ingestão de 100% das 24 fontes de dados (vendas, clientes, fiscal, devoluções, RH, produtos). Foram aplicados fallbacks de encoding (`latin1` → `utf-8`) para garantir ingestão segura.
2. **🥈 Silver Layer (`processed/`)**: Tratamento, limpeza e modelagem em um **Star Schema**.
   * Uso de tipos otimizados de dados (`int32`, `float32`, `category`) para redução extrema do consumo de memória.
   * Orquestração via `Pandas` e suporte nativo opcional a `DuckDB` para processamento analítico acelerado.
   * Resultado: 16 tabelas consolidadas (5 tabelas Fato, 9 tabelas Dimensão e auxiliares).
3. **🥇 Gold Layer (`outputs/reports/`)**: Geração de 21 relatórios agregados contendo os KPIs de negócios prontos para consumo.
4. **📊 Serving Layer**: Geração automatizada de um Dashboard HTML interativo via `Plotly` exportado como um artefato *standalone* (sem necessidade de servidor web).

---

## 🧠 Soluções de Data Science & Machine Learning

Para responder a perguntas complexas de negócio, apliquei técnicas de modelagem preditiva e sistemas de recomendação:

* **Previsão de Demanda (Séries Temporais):** Implementei um modelo **Holt-Winters (Exponential Smoothing)** via `statsmodels` para prever os próximos 90 dias de receita. O modelo superou a baseline (Média Móvel) reduzindo o **MAPE de 51.2% para 13.1%**. (A arquitetura também permite o uso de `Prophet` dinamicamente se detectado no ambiente).
* **Sistema de Recomendação:** Utilizando a biblioteca `scikit-surprise`, construí um algoritmo de **Filtragem Colaborativa (SVD)** para gerar 5 recomendações hiper-personalizadas para toda a base de clientes recorrentes.
* **Segmentação Avançada de Clientes:** Implementei um motor de **RFM (Recency, Frequency, Monetary)** para dividir os clientes em 5 clusters estratégicos (*Champions*, *Loyal*, *Potential*, *At Risk*, *Lost*), direcionando campanhas de marketing assertivas.

---

## 🛡️ Engenharia de Qualidade (QA & Testing)

O grande diferencial deste projeto foi o rigor com a confiabilidade dos dados. Construí uma suíte de testes ponta a ponta com **242 validações automatizadas** usando `Pytest`.

**O que o pipeline valida automaticamente:**
* **Integridade de Schema e Tipos:** Chaves primárias, restrições de chaves estrangeiras nulas.
* **Data Quality (ETL):** Confirma se os `JOINs` introduziram valores nulos fantasmas, multiplicaram linhas ou se ocorreu perda de granularidade.
* **Sanidade de Negócios (Silent Killers):** Previne margens de lucro > 100%, itens com quantidade negativa, ou pagamentos aprovados para pedidos cancelados.
* **Auditoria de Compliance (Risco Fiscal):** Detectou uma anomalia estrutural na base: **10.117 pedidos (R$ 300 Milhões em receita) sem Nota Fiscal emitida**, alertando os stakeholders automaticamente no relatório.

---

## 🛠️ Stack Tecnológico
* **Linguagem:** Python 3.10+
* **Processamento / ETL:** `pandas`, `numpy`, `duckdb` (opcional in-memory)
* **Machine Learning / Stats:** `statsmodels` (Séries temporais), `scikit-surprise` (SVD)
* **Visualização:** `plotly`, `matplotlib`, `seaborn`
* **Testes & QA:** `pytest` (242 testes)
* **Automação:** Orquestrador customizado em Python (`run_all.py` atuando como um mini-DAG local).

---

## 💡 Destaques do Código e Boas Práticas (Showcase)

1. **Gestão de Memória (`gc.collect()`):** Limpeza ativa de RAM após merges pesados de dataframes.
2. **Defensive Programming:** Testes falham (Fail-fast) se houver schema drift ou anomalias financeiras severas.
3. **Portabilidade:** Paths relativos (`Path(__file__)`) e um script (`convert_to_ipynb.py`) que transpila nativamente a base de código modularizada `.py` em um formato Notebook compatível com **Google Colab** em 1 clique.

---
*Projeto desenvolvido do zero para demonstrar habilidades Full-Stack em Dados: mapeamento de negócio, engenharia de pipelines confiáveis e aplicação prática de estatística/machine learning.*
