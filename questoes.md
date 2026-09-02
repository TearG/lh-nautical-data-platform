# Desafio LH Nautical - Questões e Respostas para Estudo

## Questão 1 - EDA
**Cenário:** O Sr. Almir quer uma resposta simples: “Posso confiar nesses dados para tomar decisões?”. Realizar uma análise exploratória inicial na tabela `orders` e responder perguntas básicas sobre volume, distribuição e qualidade dos dados.

**Respostas Práticas (1.1, 1.2 e 1.3):**
* **Quantidade total de linhas:** 48.998 linhas
* **Intervalo de datas:** De `2020-01-01 01:19:28` a `2026-12-31 23:43:09`.
* **Coluna Total:** Valor mínimo (R$ 32,62), Valor máximo (R$ 127.262,02) e Valor médio (R$ 28.704,99).

**Interpretação (Diagnóstico):**
Sim, o Sr. Almir pode confiar nestes dados como ponto de partida. Não há nulos no faturamento nem na data e não há registros negativos, o que demonstra integridade. O outlier de R$ 127.262,02 é plausível pois no B2B Náutico existem vendas de alto ticket (embarcações). Porém, a tabela isolada requer tratamento prévio (JOINs com order_items, payments e returns) para análises reais de lucro e margem, deduzindo cancelamentos e custos.

**Código SQL (1.1):**
```sql
SELECT 
    COUNT(*) AS total_linhas,
    MIN(created_at) AS data_minima,
    MAX(created_at) AS data_maxima,
    MIN(total) AS valor_minimo,
    MAX(total) AS valor_maximo,
    AVG(total) AS valor_medio
FROM orders;
```

---

## Questão 2 - Schema
**Cenário:** Desenvolver um código que detecta as colunas de cada tabela a partir dos CSV e cria um arquivo final `.sql` com as instruções de criação de cada tabela para o PostgreSQL (apenas com Python puro, sem Pandas).

**Código Python:**
```python
import os
import csv
import re

def infer_type(value):
    value = value.strip()
    if not value: return None
    if re.match(r'^-?\d+$', value): return 'INTEGER'
    if re.match(r'^-?\d+\.\d+$', value): return 'NUMERIC'
    if re.match(r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?(\.\d+)?$', value): return 'TIMESTAMP'
    return 'VARCHAR'

def resolve_type(types_set):
    if not types_set: return 'VARCHAR'
    if 'VARCHAR' in types_set: return 'VARCHAR'
    if 'NUMERIC' in types_set and 'TIMESTAMP' in types_set: return 'VARCHAR'
    if 'NUMERIC' in types_set: return 'NUMERIC'
    if 'TIMESTAMP' in types_set: return 'TIMESTAMP'
    if 'INTEGER' in types_set: return 'INTEGER'
    return 'VARCHAR'

def process_csv(csv_path):
    table_name = os.path.basename(csv_path).replace('.csv', '')
    with open(csv_path, 'r', encoding='latin1') as f:
        reader = csv.reader(f)
        try: headers = next(reader)
        except StopIteration: return table_name, {}
        tracker = {header: set() for header in headers}
        for row_idx, row in enumerate(reader):
            if row_idx >= 100: break
            for i, value in enumerate(row):
                if i < len(headers):
                    detected_type = infer_type(value)
                    if detected_type: tracker[headers[i]].add(detected_type)
    return table_name, {header: resolve_type(tracker[header]) for header in headers}

def main():
    input_dir, output_file, sql_statements = '1-lh_nautical_csv', 'schema.sql', []
    for filename in sorted(os.listdir(input_dir)):
        if filename.endswith('.csv'):
            table_name, col_types = process_csv(os.path.join(input_dir, filename))
            if col_types:
                lines = [f"CREATE TABLE {table_name} ("]
                lines.append(",\n".join([f"    \"{col}\" {ctype}" for col, ctype in col_types.items()]))
                lines.append(");\n")
                sql_statements.append("\n".join(lines))
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(sql_statements))

if __name__ == '__main__':
    main()
```

---

## Questão 3 - Carregamento
**Cenário:** Escreva um script python para realizar o carregamento de todos os arquivos CSV respeitando o schema criado na questão anterior (sem limpar os dados originais).

**Código Python:**
```python
import os
import pandas as pd
from sqlalchemy import create_engine

DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME = 'postgres', 'sua_senha', 'localhost', '5432', 'lh_nautical'
DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(DATABASE_URI)

def load_data():
    input_dir = '1-lh_nautical_csv'
    for filename in sorted(os.listdir(input_dir)):
        if filename.endswith('.csv'):
            table_name = filename.replace('.csv', '')
            csv_path = os.path.join(input_dir, filename)
            try:
                df = pd.read_csv(csv_path, encoding='latin1')
                df.to_sql(name=table_name, con=engine, if_exists='append', index=False, chunksize=10000)
            except Exception as e:
                print(f"[ERRO] - Falha ao carregar a tabela '{table_name}': {e}")

if __name__ == "__main__":
    load_data()
```

**Validação (3.2): Total somado das linhas de customers, orders, order_items e payments**
* Total: **251.864** (customers: 2.000, orders: 48.998, order_items: 147.320, payments: 53.546).

---

## Questão 4 - Análise de clientes
**Cenário:** Filtrar os clientes de Elite (>= 13 categorias), rankear o Top 10 por maior Ticket Médio, e descobrir a categoria mais consumida por eles.

**Resultado:** A categoria com a maior quantidade de itens consumida por esse Top 10 específico é **Hélices (ID: 8)** com **492 itens**.

**Código SQL (4.1):**
```sql
WITH customer_orders AS (
    SELECT 
        customer_id,
        SUM(total) AS faturamento_total,
        COUNT(id) AS frequencia,
        SUM(total) / COUNT(id) AS ticket_medio
    FROM orders
    GROUP BY customer_id
),
customer_diversity AS (
    SELECT 
        o.customer_id,
        COUNT(DISTINCT p.category_id) AS diversidade_categorias
    FROM orders o
    JOIN order_items oi ON o.id = oi.order_id
    JOIN product_variants pv ON oi.product_variant_id = pv.id
    JOIN products p ON pv.product_id = p.id
    GROUP BY o.customer_id
),
elite_customers AS (
    SELECT 
        co.customer_id,
        co.faturamento_total,
        co.frequencia,
        co.ticket_medio,
        cd.diversidade_categorias
    FROM customer_orders co
    JOIN customer_diversity cd ON co.customer_id = cd.customer_id
    WHERE cd.diversidade_categorias >= 13
)
SELECT 
    customer_id,
    faturamento_total,
    frequencia,
    ticket_medio,
    diversidade_categorias
FROM elite_customers
ORDER BY ticket_medio DESC, customer_id ASC
LIMIT 10;
```

**Explicação Metodológica (4.2):**
1. **Mapeamento da cadeia:** O relacionamento é: `orders` -> `order_items` (`id=order_id`) -> `product_variants` (`product_variant_id=id`) -> `products` (`product_id=id`). Isso extrai a `category_id` exata de cada item comprado pelo `customer_id`.
2. **Lógica de diversidade:** Agrupei por cliente e utilizei `COUNT(DISTINCT category_id)`, garantindo contagem única por categoria independente de volume. O filtro final aplicou `WHERE diversidade >= 13`.
3. **Contagem dos Top 10:** Feita em dois estágios. Primeiro, fechei a lista dos 10 IDs exatos. No estágio final, utilizei uma cláusula restrita (`IN(ids_do_top_10)`) na base geral ANTES de somar a quantidade por categoria (`SUM(quantity)`), eliminando completamente as vendas fora deste grupo.

## Questão 5.1 - SQL Calendário de Vendas
**Cenário:** LEFT JOIN entre um calendário semanal em português e as vendas agregadas.
**Código SQL:**
`sql
WITH dias_semana AS (
    SELECT 0 AS dia_num, 'Domingo' AS dia_nome UNION ALL
    SELECT 1, 'Segunda-feira' UNION ALL
    SELECT 2, 'Terça-feira' UNION ALL
    SELECT 3, 'Quarta-feira' UNION ALL
    SELECT 4, 'Quinta-feira' UNION ALL
    SELECT 5, 'Sexta-feira' UNION ALL
    SELECT 6, 'Sábado'
),
vendas_por_dia AS (
    SELECT 
        EXTRACT(DOW FROM CAST(created_at AS TIMESTAMP)) AS dia_num,
        SUM(total) AS valor_venda
    FROM orders
    GROUP BY EXTRACT(DOW FROM CAST(created_at AS TIMESTAMP))
)
SELECT 
    d.dia_nome,
    COALESCE(v.valor_venda, 0) AS valor_venda
FROM dias_semana d
LEFT JOIN vendas_por_dia v ON d.dia_num = v.dia_num
ORDER BY d.dia_num;
`

## Questão 5.2 - Explicação Calendário
**1. Por que usar tabela calendário em vez de agrupar direto?**
Se agruparmos diretamente a tabela de vendas, os dias em que não houveram vendas não aparecerão no resultado (as linhas somem). O calendário atua como uma "espinha dorsal" (spine), garantindo que todos os dias da semana sejam representados no relatório. O LEFT JOIN acopla as vendas existentes e deixa nulos (convertidos para zero) os dias sem vendas.

**2. O que aconteceria com a média de vendas?**
Se não usássemos o calendário, os dias com "zero vendas" seriam ignorados no cálculo do denominador da média, o que inflaria (aumentaria artificialmente) a média de vendas. Por exemplo, vender R$ 100 na segunda e R$ 0 na terça dá uma média real de R$ 50/dia. Sem o calendário, a terça some e a média calculada pelo banco será de R$ 100/dia. O calendário força a inclusão dos zeros, garantindo a acurácia estatística.

## Questão 6.1 - Código Python do Modelo de Previsão
**Código em Python:**
```python
import pandas as pd
from sklearn.metrics import mean_absolute_error

orders = pd.read_csv('1-lh_nautical_csv/orders.csv', encoding='latin1')
order_items = pd.read_csv('1-lh_nautical_csv/order_items.csv', encoding='latin1')
product_variants = pd.read_csv('1-lh_nautical_csv/product_variants.csv', encoding='latin1')
products = pd.read_csv('1-lh_nautical_csv/products.csv', encoding='latin1')

prod_bussola = products[products['name'].str.contains('702', na=False) & products['name'].str.contains('Bordo', na=False)]
prod_bussola = prod_bussola[~prod_bussola['name'].str.contains('7024')]

bussola_variants = product_variants[product_variants['product_id'].isin(prod_bussola['id'])]
bussola_items = order_items[order_items['product_variant_id'].isin(bussola_variants['id'])]

df_bussola = bussola_items.merge(orders[['id', 'created_at']], left_on='order_id', right_on='id')
df_bussola['created_at'] = pd.to_datetime(df_bussola['created_at'])

df_bussola['year_month'] = df_bussola['created_at'].dt.to_period('M')
monthly_sales = df_bussola.groupby('year_month')['quantity'].sum().reset_index()

all_months = pd.period_range(start=monthly_sales['year_month'].min(), end=pd.Period('2026-03', 'M'))
monthly_sales = monthly_sales.set_index('year_month').reindex(all_months, fill_value=0).reset_index()
monthly_sales.rename(columns={'index': 'year_month'}, inplace=True)

monthly_sales['moving_avg_3m'] = monthly_sales['quantity'].rolling(window=3).mean().shift(1)

test_period = monthly_sales[monthly_sales['year_month'].between(pd.Period('2026-01', 'M'), pd.Period('2026-03', 'M'))]

mae = mean_absolute_error(test_period['quantity'], test_period['moving_avg_3m'])
print(test_period)
print(f"MAE: {mae:.2f}")
```

## Questão 6.2 - Validação da Previsão
**Soma total da previsão de vendas (arredondada):** 149

## Questão 7 - Sistema de Recomendação
**Cenário:** Identificar qual produto deve ser recomendado junto ao item "Motor de Popa 1949", com base na similaridade de comportamento de compra dos clientes, utilizando Similaridade de Cosseno em uma Matriz Usuário x Produto.

**Top 5 Recomendações para "Motor de Popa 1949":**
1. Motor de Popa 5331
2. Cabo Náutico 2105
3. Vela Mestra 1913
4. Cabo Náutico 9048
5. GPS Plotter 6249

## Questão 7.1 - Código Python do Sistema de Recomendação
**Código em Python:**
```python
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# 1. Carregar os datasets
orders = pd.read_csv('1-lh_nautical_csv/orders.csv', encoding='latin1')
order_items = pd.read_csv('1-lh_nautical_csv/order_items.csv', encoding='latin1')
product_variants = pd.read_csv('1-lh_nautical_csv/product_variants.csv', encoding='latin1')
products = pd.read_csv('1-lh_nautical_csv/products.csv', encoding='latin1')

# 2. Construir o dataset unificado
merged = orders[['id', 'customer_id']].merge(order_items[['order_id', 'product_variant_id']], left_on='id', right_on='order_id')
merged = merged.merge(product_variants[['id', 'product_id']], left_on='product_variant_id', right_on='id')
merged = merged.merge(products[['id', 'name']], left_on='product_id', right_on='id')

# 3. Construir a Matriz Usuário x Item (Presença/Ausência)
user_product = merged.groupby(['customer_id', 'product_id']).size().reset_index()
user_product['purchased'] = 1
matrix = user_product.pivot(index='customer_id', columns='product_id', values='purchased').fillna(0)

# 4. Cálculo da Similaridade de Cosseno
product_item_matrix = matrix.T
similarity_matrix = cosine_similarity(product_item_matrix)
similarity_df = pd.DataFrame(similarity_matrix, index=product_item_matrix.index, columns=product_item_matrix.index)

# 5. Recuperar o ID do Produto Alvo
motor = products[products['name'].str.contains('Motor de Popa 1949', na=False, regex=False)]
motor_id = motor['id'].values[0]

# 6. Gerar o Ranking de Similaridade (Desconsiderando ele mesmo)
similar_scores = similarity_df[motor_id].sort_values(ascending=False)
similar_scores = similar_scores.drop(motor_id)
top_5_ids = similar_scores.head(5).index

print("=== TOP 5 RECOMENDAÇÕES PARA 'Motor de Popa 1949' ===")
for pid in top_5_ids:
    pname = products[products['id'] == pid]['name'].values[0]
    score = similar_scores[pid]
    print(f"Produto: {pname} | Score: {score:.4f}")
```

## Questão 7.2 - Validação do Produto
**Produto mais similar ao Motor de Popa 1949:** Motor de Popa 5331

## Questão 7.3 - Explicação Metodológica
**1. Como a matriz foi construída?**
Realizamos um join entre as tabelas de pedidos e produtos para mapear o par (id_cliente, id_produto). Agrupamos os dados para marcar com "1" caso o cliente tenha comprado o produto ao menos uma vez na vida. Em seguida, usamos a função de Pivot para transformar a base em uma matriz larga (linhas = clientes, colunas = produtos), preenchendo com "0" as interseções de produtos que não foram comprados.

**2. O que significa a similaridade de cosseno nesse contexto?**
A similaridade de cosseno mede o "ângulo" entre dois vetores de produtos no espaço multidimensional de clientes. Em termos de negócio, ela calcula o quão sobreposta é a base de compradores de dois itens. Se o Motor A e o Cabo B possuem uma similaridade próxima de 1, significa que eles compartilham quase exatamente os mesmos clientes (quem compra um, quase sempre compra o outro).

**3. Uma limitação desse método de recomendação.**
O problema do **"Cold Start" (Início Frio)** e o **Sparsity (Matriz Esparsa)**. Esse modelo é totalmente cego para as características físicas do produto. Se a LH Nautical lançar um motor novo e incrivelmente bom hoje, o algoritmo jamais o recomendará, pois como o produto não possui histórico de vendas, seu vetor será inteiramente zerado, e a similaridade de cosseno com os outros itens será 0.

## Pergunta Bônus / Feedback
**Em qual questão você teve mais facilidade?**
A **Questão 1 (EDA)** e a **Questão 3 (Carregamento dos CSVs)** foram as que trouxeram maior facilidade. Como elas exigiam apenas comandos lineares e diretos (agregações simples em SQL e iteração de ingestão bruta em Python), não houve necessidade de mapear toda a cadeia relacional do banco de dados (Star Schema) nem aplicar transformações matemáticas complexas, como aconteceu nos modelos de previsão (Média Móvel) e no sistema de recomendação (Similaridade de Cosseno).

## Notas Finais / Entregáveis do Projeto
**Sobre o Dashboard (Restrição de Plataformas de BI):**
Durante a entrega, fomos solicitados a enviar um arquivo de BI proprietário (como o .pbix do Power BI). Como escolhemos desenvolver o projeto de forma 100% programática usando Python para demonstrar habilidades avançadas de codificação e independência de licenças pagas, nossa estratégia foi exportar o Dashboard HTML em formato PDF. Isso atendeu às restrições de upload da plataforma e ao mesmo tempo preservou o design e a integridade visual da solução técnica.

**Justificativa de Defesa Técnica (Para entrevistas futuras):**
1. **Dashboard Programático:** Escolhido para provar domínio em bibliotecas de DataViz ponta a ponta.
2. **Modelagem Matemática:** A Previsão de Demanda e o Sistema de Recomendação foram escritos "do zero", operando diretamente sobre o Star Schema.
3. **Visão de Negócio:** O relatório executivo priorizou achar "falhas no negócio" além de apenas responder as métricas (ex: itens sem NF-e apontados durante o EDA inicial).

---
*Desafio LH Nautical concluído com sucesso!*
