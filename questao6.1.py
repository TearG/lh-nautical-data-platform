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

print("=== TRIMESTRE DE TESTE (Q1 2026) ===")
print(test_period[['year_month', 'quantity', 'moving_avg_3m']])
print(f"\nMAE (Mean Absolute Error): {mae:.2f}")
