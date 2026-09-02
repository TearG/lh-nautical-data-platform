import os
import time
import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ---- Configuração (relativo ao script) ----
BASE_DIR    = Path(__file__).parent
PROC_DIR    = BASE_DIR / "processed"
REPORT_DIR  = BASE_DIR / "outputs" / "reports"
os.makedirs(REPORT_DIR, exist_ok=True)

_t0_global = time.time()

def read_processed(name):
    return pd.read_csv(PROC_DIR / name)

def save_report(df, name):
    path = REPORT_DIR / name
    df.to_csv(path, index=False, encoding='utf-8-sig')
    print(f"  [RELATORIO] {name} gerado com {len(df)} linhas.")

def _log(secao):
    """Imprime a secao com tempo decorrido desde o inicio."""
    elapsed = time.time() - _t0_global
    print(f"\n[{elapsed:5.1f}s] {secao}")

print("=" * 60)
print("  LH Nautical - Script 07: Análise Fase 2 (Supply & RH)")
print("=" * 60)

# Carregando tabelas necessárias
dim_suppliers = read_processed('dim_suppliers.csv')
dim_employees = read_processed('dim_employees.csv')
dim_addresses = read_processed('dim_addresses.csv')
fato_compras = read_processed('fato_compras.csv')
fato_fiscal = read_processed('fato_fiscal.csv')
fato_vendas = read_processed('fato_vendas.csv')

# ====================================================================
# 7A. PERFORMANCE DE FORNECEDORES (Supply Chain)
# ====================================================================
_log("7A. Performance de Fornecedores (Supply Chain)")
# Calcula Total Gasto e Lead Time por Fornecedor
perf_forn = fato_compras.groupby('supplier_id').agg(
    qtd_compras=('purchase_order_id', 'nunique'),
    total_gasto=('total', 'sum'),
    lead_time_medio=('lead_time_days', 'mean'),
    atraso_medio=('delay_days', 'mean')
).reset_index()

perf_forn = perf_forn.merge(dim_suppliers[['supplier_id', 'legal_name', 'country']], on='supplier_id', how='left')
perf_forn = perf_forn[['supplier_id', 'legal_name', 'country', 'qtd_compras', 'total_gasto', 'lead_time_medio', 'atraso_medio']]
perf_forn = perf_forn.sort_values('total_gasto', ascending=False)
save_report(perf_forn, '07a_performance_fornecedores.csv')

# ====================================================================
# 7B. VENDAS POR ESTADO (Logística)
# ====================================================================
_log("7B. Vendas por Estado (Logistica)")
# Cruzando vendas com endereços — prioridade: shipping > billing > secondary
shipping_addr = dim_addresses[dim_addresses['address_type'] == 'shipping'].drop_duplicates('customer_id')
billing_addr  = dim_addresses[dim_addresses['address_type'] == 'billing'].drop_duplicates('customer_id')
outros_addr   = dim_addresses[~dim_addresses['address_type'].isin(['shipping', 'billing'])].drop_duplicates('customer_id')

# Stacking pela prioridade: shipping ganha; billing para quem nao tem shipping; outros no fallback
clientes_com_shipping = shipping_addr['customer_id']
clientes_com_billing  = billing_addr[~billing_addr['customer_id'].isin(clientes_com_shipping)]['customer_id']

billing_fallback = billing_addr[billing_addr['customer_id'].isin(clientes_com_billing)]
outros_fallback  = outros_addr[
    ~outros_addr['customer_id'].isin(clientes_com_shipping) &
    ~outros_addr['customer_id'].isin(clientes_com_billing)
]

enderecos_unicos = pd.concat([shipping_addr, billing_fallback, outros_fallback])[['customer_id', 'state', 'city', 'country']]

vendas_geoloc = fato_vendas.merge(enderecos_unicos, on='customer_id', how='left')
vendas_geoloc['state'] = vendas_geoloc['state'].fillna('Desconhecido')

vendas_estado = vendas_geoloc.groupby('state').agg(
    receita_total=('line_total', 'sum'),
    qtd_pedidos=('order_id', 'nunique')
).reset_index().sort_values('receita_total', ascending=False)
save_report(vendas_estado, '07b_vendas_por_estado.csv')

# ====================================================================
# 7C. PERFORMANCE DE VENDEDORES (RH)
# ====================================================================
_log("7C. Performance de Vendedores (RH)")
# Apenas vendas POS (Lojas físicas) e onde haja salesperson
fato_vendas_pos = fato_vendas[(fato_vendas['channel'] == 'pos') & (fato_vendas['salesperson_id'].notna())]

perf_vend = fato_vendas_pos.groupby('salesperson_id').agg(
    receita_gerada=('line_total', 'sum'),
    qtd_vendas=('order_id', 'nunique')
).reset_index()

perf_vend = perf_vend.merge(dim_employees[['employee_id', 'full_name', 'role', 'is_active']], left_on='salesperson_id', right_on='employee_id', how='left')
perf_vend = perf_vend[['salesperson_id', 'full_name', 'role', 'is_active', 'qtd_vendas', 'receita_gerada']]
perf_vend = perf_vend.sort_values('receita_gerada', ascending=False)
save_report(perf_vend, '07c_performance_vendedores.csv')

# ====================================================================
# 7D. RISCO FISCAL POR MÊS (Auditoria)
# ====================================================================
_log("7D. Risco Fiscal por Mes (Auditoria)")
# Identifica vendas pagas/entregues sem NF-e
vendas_pagas = fato_vendas[fato_vendas['status'].isin(['paid', 'confirmed', 'delivered'])]
nfe_autorizada = fato_fiscal[fato_fiscal['status'] == 'authorized']

pedidos_pagos = vendas_pagas[['order_id', 'year', 'month', 'line_total']].copy()
pedidos_com_nfe = nfe_autorizada['order_id'].unique()

pedidos_pagos['tem_nfe'] = pedidos_pagos['order_id'].isin(pedidos_com_nfe)
pedidos_risco = pedidos_pagos[~pedidos_pagos['tem_nfe']]

risco_mes = pedidos_risco.groupby(['year', 'month']).agg(
    qtd_pedidos_sem_nfe=('order_id', 'nunique'),
    receita_nao_faturada=('line_total', 'sum')
).reset_index().sort_values(['year', 'month'])
save_report(risco_mes, '07d_risco_fiscal_por_mes.csv')

# ====================================================================
# 7E. ATRIBUTOS DOS PRODUTOS MAIS VENDIDOS
# ====================================================================
_log("7E. Atributos dos Produtos Mais Vendidos")
dim_product_attributes = read_processed('dim_product_attributes.csv')
dim_products = read_processed('dim_products.csv')

# Receita por variante
receita_variante = fato_vendas.groupby('product_variant_id').agg(
    receita_total=('line_total', 'sum'),
    qtd_vendida=('quantity', 'sum')
).reset_index()

# Junta atributos com receita
atrib_receita = dim_product_attributes.merge(
    receita_variante,
    on='product_variant_id',
    how='inner'
)

# Ranking de valores de atributo por receita
atrib_ranking = atrib_receita.groupby(['attribute_name', 'value']).agg(
    receita_total=('receita_total', 'sum'),
    qtd_vendida=('qtd_vendida', 'sum'),
    qtd_skus=('product_variant_id', 'nunique')
).reset_index().sort_values(['attribute_name', 'receita_total'], ascending=[True, False])

save_report(atrib_ranking, '07e_atributos_produtos_top.csv')

# ====================================================================
# 7F. MATRIZ PRODUTO x FORNECEDOR PREFERENCIAL
# ====================================================================
_log("7F. Matriz Produto x Fornecedor Preferencial")
dim_product_suppliers = read_processed('dim_product_suppliers.csv')

# Foca nos fornecedores preferenciais
prod_forn_pref = dim_product_suppliers[dim_product_suppliers['is_preferred'] == True].copy()

# Junta com receita por variante e nome do produto
prod_forn_pref = prod_forn_pref.merge(
    receita_variante,
    on='product_variant_id',
    how='left'
).merge(
    dim_products[['variant_id', 'product_name', 'category_name', 'brand_name']].rename(columns={'variant_id': 'product_variant_id'}),
    on='product_variant_id',
    how='left'
).merge(
    dim_suppliers[['supplier_id', 'legal_name']].rename(columns={'legal_name': 'supplier_name'}),
    on='supplier_id',
    how='left'
)

prod_forn_pref = prod_forn_pref[[
    'product_variant_id', 'product_name', 'category_name', 'brand_name',
    'supplier_id', 'supplier_name', 'last_quoted_cost', 'lead_time_days',
    'receita_total', 'qtd_vendida'
]].sort_values('receita_total', ascending=False)

save_report(prod_forn_pref, '07f_matriz_produto_fornecedor.csv')

# ====================================================================
# 7G. POSICAO ATUAL DE ESTOQUE POR PRODUTO E LOCAL
# ====================================================================
_log("7G. Posicao Atual de Estoque por Produto e Local")
dim_stock_levels  = read_processed('dim_stock_levels.csv')
dim_locations_df  = read_processed('dim_locations.csv')

estoque_atual = dim_stock_levels.merge(
    dim_products[['variant_id', 'product_name', 'category_name', 'brand_name', 'cost_price', 'selling_price']].rename(columns={'variant_id': 'product_variant_id'}),
    on='product_variant_id',
    how='left'
).merge(
    dim_locations_df[['location_id', 'name']].rename(columns={'name': 'location_name'}),
    on='location_id',
    how='left'
)

estoque_atual['estoque_valor_custo'] = estoque_atual['quantity_on_hand'] * estoque_atual['cost_price']
estoque_atual['estoque_valor_venda']  = estoque_atual['quantity_on_hand'] * estoque_atual['selling_price']

# Flag de alerta para estoque abaixo do mínimo
estoque_atual['alerta_estoque_baixo'] = (
    estoque_atual['quantity_on_hand'] <= estoque_atual['reorder_point'].fillna(0)
)

estoque_saida = estoque_atual[[
    'product_variant_id', 'product_name', 'category_name', 'brand_name',
    'location_id', 'location_name', 'quantity_on_hand', 'reorder_point',
    'alerta_estoque_baixo', 'estoque_valor_custo', 'estoque_valor_venda'
]].sort_values('estoque_valor_venda', ascending=False)

save_report(estoque_saida, '07g_posicao_estoque_atual.csv')

total = time.time() - _t0_global
print(f"\n[CONCLUIDO] Script 07 finalizado em {total:.1f}s com sucesso.")
