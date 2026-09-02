import pandas as pd

orders = pd.read_csv('1-lh_nautical_csv/orders.csv', encoding='latin1')
order_items = pd.read_csv('1-lh_nautical_csv/order_items.csv', encoding='latin1')
product_variants = pd.read_csv('1-lh_nautical_csv/product_variants.csv', encoding='latin1')
products = pd.read_csv('1-lh_nautical_csv/products.csv', encoding='latin1')
categories = pd.read_csv('1-lh_nautical_csv/categories.csv', encoding='latin1')

customer_orders = orders.groupby('customer_id').agg(
    faturamento_total=('total', 'sum'),
    frequencia=('id', 'count')
).reset_index()

customer_orders['ticket_medio'] = customer_orders['faturamento_total'] / customer_orders['frequencia']

# order_items has product_variant_id
merged = orders[['id', 'customer_id']].merge(order_items[['order_id', 'product_variant_id', 'quantity']], left_on='id', right_on='order_id')
merged = merged.merge(product_variants[['id', 'product_id']], left_on='product_variant_id', right_on='id')
merged = merged.merge(products[['id', 'category_id']], left_on='product_id', right_on='id')

customer_cats = merged.groupby('customer_id')['category_id'].nunique().reset_index()
customer_cats.rename(columns={'category_id': 'diversidade_categorias'}, inplace=True)

customer_stats = customer_orders.merge(customer_cats, on='customer_id')

elite = customer_stats[customer_stats['diversidade_categorias'] >= 13]
top_10 = elite.sort_values(by=['ticket_medio', 'customer_id'], ascending=[False, True]).head(10)
top_10_ids = top_10['customer_id'].tolist()

top_10_merged = merged[merged['customer_id'].isin(top_10_ids)]
cat_quantity = top_10_merged.groupby('category_id')['quantity'].sum().reset_index()
best_cat = cat_quantity.sort_values(by='quantity', ascending=False).iloc[0]

best_cat_id = int(best_cat['category_id'])
cat_name = categories[categories['id'] == best_cat_id]['name'].values[0]

print("=== TOP 10 CLIENTES ===")
for _, row in top_10.iterrows():
    print(f"Customer {int(row['customer_id'])} | Ticket: {row['ticket_medio']:.2f} | Categorias: {int(row['diversidade_categorias'])}")

print(f"\n=== CATEGORIA MAIS COMPRADA PELO TOP 10 ===")
print(f"Categoria ID: {best_cat_id}")
print(f"Nome: {cat_name}")
print(f"Quantidade: {best_cat['quantity']}")
