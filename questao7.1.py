import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# 1. Carregar os datasets (usando encoding latin1 para evitar quebras nos arquivos brutos)
orders = pd.read_csv('1-lh_nautical_csv/orders.csv', encoding='latin1')
order_items = pd.read_csv('1-lh_nautical_csv/order_items.csv', encoding='latin1')
product_variants = pd.read_csv('1-lh_nautical_csv/product_variants.csv', encoding='latin1')
products = pd.read_csv('1-lh_nautical_csv/products.csv', encoding='latin1')

# 2. Construir o dataset unificado
merged = orders[['id', 'customer_id']].merge(order_items[['order_id', 'product_variant_id']], left_on='id', right_on='order_id')
merged = merged.merge(product_variants[['id', 'product_id']], left_on='product_variant_id', right_on='id')
merged = merged.merge(products[['id', 'name']], left_on='product_id', right_on='id')

# 3. Construir a Matriz Usuário x Item (Presença/Ausência)
# Contamos as aparições e definimos como 1 (comprou). Valores nulos viram 0.
user_product = merged.groupby(['customer_id', 'product_id']).size().reset_index()
user_product['purchased'] = 1
matrix = user_product.pivot(index='customer_id', columns='product_id', values='purchased').fillna(0)

# 4. Cálculo da Similaridade de Cosseno
# Transpomos a matriz para [Produtos x Usuários] para comparar produtos entre si
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
