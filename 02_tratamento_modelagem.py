"""
=======================================================================
SCRIPT 02 - Tratamento e Modelagem de Dados - LH Nautical
=======================================================================
Responsavel : Gabriel Santos (Tech Lead) - Etapa de Engenharia de Dados
Objetivo    : Limpar, tipar e modelar os dados brutos em tabelas
              prontas para analise (Fato de Vendas + Dimensoes).

              Premissas:
              - Datas convertidas para datetime
              - Valores monetarios como float
              - Nulos tratados com criterio (remover ou imputar)
              - Duplicatas removidas
              - Dados exportados para /processed/
=======================================================================
"""

import os
import gc
import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

try:
    import duckdb
    _DUCKDB_AVAILABLE = True
except ImportError:
    _DUCKDB_AVAILABLE = False

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

# ---- Configuracao (relativo ao script) ----
BASE_DIR    = Path(__file__).parent
CSV_DIR     = BASE_DIR / "1-lh_nautical_csv"
PROC_DIR    = BASE_DIR / "processed"
REPORT_DIR  = BASE_DIR / "outputs" / "reports"
DB_PATH     = BASE_DIR / "nautical.duckdb"

os.makedirs(PROC_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# ---- Conexao DuckDB (opcional) ----
_db = None
if _DUCKDB_AVAILABLE:
    _db = duckdb.connect(str(DB_PATH))
    print(f"  [DuckDB] Banco conectado: {DB_PATH}")
else:
    print("  [DuckDB] duckdb nao instalado — escrevendo apenas CSVs.")
    print("           Para ativar: pip install duckdb")

def _ram_mb() -> str:
    """Retorna uso atual de RAM em MB (requer psutil)."""
    if _PSUTIL_AVAILABLE:
        proc = psutil.Process(os.getpid())
        return f"{proc.memory_info().rss / 1_048_576:.0f} MB"
    return "N/A"

def read_csv(name: str, dtypes: dict | None = None) -> pd.DataFrame:
    """Leitura padrao de CSV com dtypes opcionais para economia de RAM."""
    return pd.read_csv(os.path.join(CSV_DIR, name), dtype=dtypes)

def save(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Salva DataFrame em /processed/ (CSV) e, se disponivel, no DuckDB."""
    path = os.path.join(PROC_DIR, name)
    df.to_csv(path, index=False, encoding='utf-8-sig')
    # --- Escrita no DuckDB (adicional, nao substitui o CSV) ---
    if _db is not None:
        table_name = name.replace('.csv', '')
        _db.execute(f"DROP TABLE IF EXISTS {table_name}")
        _db.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
    print(f"  [SALVO] {name}: {len(df):,} linhas  |  RAM: {_ram_mb()}")
    return df

print("=" * 60)
print("  LH Nautical - Script 02: Tratamento e Modelagem")
print("=" * 60)

# ====================================================================
# DIMENSAO: CLIENTES (dim_customers)
# ====================================================================
print("\n[1/8] Tratando dim_customers...")
customers = read_csv('customers.csv')
customers = customers.drop_duplicates(subset=['id'])
customers['created_at'] = pd.to_datetime(customers['created_at'], errors='coerce')
customers['updated_at'] = pd.to_datetime(customers['updated_at'], errors='coerce')
# Preenche trade_name ausente com legal_name (PF nao tem trade_name)
customers['trade_name'] = customers['trade_name'].fillna(customers['legal_name'])
# Mascara email ausente como 'sem_email@lhnautical.com'
customers['email'] = customers['email'].fillna('sem_email@lhnautical.com')
customers['phone'] = customers['phone'].fillna('N/A')
customers['state_registration'] = customers['state_registration'].fillna('NAO_INFORMADO')
dim_customers = customers.rename(columns={'id': 'customer_id'})
save(dim_customers, 'dim_customers.csv')

# ====================================================================
# DIMENSAO: PRODUTOS (dim_products)
# ====================================================================
print("\n[2/8] Tratando dim_products...")
products  = read_csv('products.csv')
brands    = read_csv('brands.csv')[['id', 'name']].rename(columns={'id': 'brand_id', 'name': 'brand_name'})
categories = read_csv('categories.csv')[['id', 'name']].rename(columns={'id': 'category_id', 'name': 'category_name'})
variants  = read_csv('product_variants.csv')

products = products.drop_duplicates(subset=['id'])
products['description'] = products['description'].fillna('Sem descricao')
products = products.merge(brands, on='brand_id', how='left')
products = products.merge(categories, on='category_id', how='left')
products['brand_name'] = products['brand_name'].fillna('Marca Desconhecida')
products['category_name'] = products['category_name'].fillna('Categoria Desconhecida')

# Junta variantes (SKU, custo, preco) com produtos
variants = variants.drop_duplicates(subset=['id'])
variants_slim = variants[['id', 'product_id', 'sku', 'cost_price', 'sale_price', 'weight_kg', 'is_active']].rename(
    columns={'id': 'variant_id', 'sale_price': 'selling_price'}
)
dim_products = variants_slim.merge(
    products[['id', 'name', 'brand_name', 'category_name', 'unit_of_measure', 'is_active']].rename(
        columns={'id': 'product_id', 'name': 'product_name', 'is_active': 'product_active'}
    ),
    on='product_id', how='left'
)
save(dim_products, 'dim_products.csv')

# ====================================================================
# DIMENSAO: LOCAIS (dim_locations)
# ====================================================================
print("\n[3/8] Tratando dim_locations...")
locations = read_csv('locations.csv')
locations = locations.drop_duplicates(subset=['id'])
locations['complement'] = locations['complement'].fillna('')
dim_locations = locations.rename(columns={'id': 'location_id'})
save(dim_locations, 'dim_locations.csv')

# ====================================================================
# DIMENSAO: TEMPO (dim_calendar) - Preenchida a partir das datas de pedidos
# ====================================================================
print("\n[4/8] Construindo dim_calendar...")
orders = read_csv('orders.csv')
orders['placed_at'] = pd.to_datetime(orders['placed_at'], errors='coerce')
date_range = pd.date_range(start='2020-01-01', end='2026-12-31', freq='D')
dim_calendar = pd.DataFrame({'date': date_range})
dim_calendar['year']        = dim_calendar['date'].dt.year
dim_calendar['quarter']     = dim_calendar['date'].dt.quarter
dim_calendar['month']       = dim_calendar['date'].dt.month
dim_calendar['month_name']  = dim_calendar['date'].dt.strftime('%B')
dim_calendar['week']        = dim_calendar['date'].dt.isocalendar().week.astype(int)
dim_calendar['day_of_week'] = dim_calendar['date'].dt.dayofweek         # 0=Segunda
dim_calendar['day_name']    = dim_calendar['date'].dt.strftime('%A')
dim_calendar['is_weekend']  = dim_calendar['day_of_week'].isin([5, 6])
save(dim_calendar, 'dim_calendar.csv')

# ====================================================================
# FATO: VENDAS (fato_vendas)  — OTIMIZADO PARA MEMORIA
# ====================================================================
print("\n[5/8] Construindo fato_vendas...")
print(f"  [RAM] Antes do join: {_ram_mb()}")

# Dtypes otimizados: colunas de alta cardinalidade como category,
# IDs como int32, monetarios como float32  -->  ~40-60% menos RAM
_orders_dtypes = {
    'id':              'int32',
    'customer_id':     'int32',
    'location_id':     'Int32',   # nullable int (pode ter nulos)
    'salesperson_id':  'Int32',
    'channel':         'category',
    'status':          'category',
}
_items_dtypes = {
    'id':                 'int32',
    'order_id':           'int32',
    'product_variant_id': 'Int32',
    'quantity':           'int32',
    'unit_price':         'float32',
    'line_total':         'float32',
}

order_items = read_csv('order_items.csv', dtypes=_items_dtypes)
orders['placed_at']   = pd.to_datetime(orders['placed_at'],   errors='coerce')
orders['created_at']  = pd.to_datetime(orders['created_at'],  errors='coerce')
orders['updated_at']  = pd.to_datetime(orders['updated_at'],  errors='coerce')

# Remove pedidos sem data valida
orders = orders.dropna(subset=['placed_at'])
orders = orders.drop_duplicates(subset=['id'])
order_items = order_items.drop_duplicates(subset=['id'])

# Junta itens com pedidos (apenas as colunas necessarias para reduzir footprint)
_orders_slim = orders[[
    'id', 'order_number', 'channel', 'customer_id', 'salesperson_id',
    'location_id', 'status', 'discount_amount', 'total', 'placed_at'
]].copy()

fato_vendas = order_items.merge(
    _orders_slim,
    left_on='order_id', right_on='id', how='inner', suffixes=('', '_order')
)
fato_vendas = fato_vendas.rename(columns={'id': 'order_item_id', 'order_id': 'order_id'})

# Libera memoria dos DataFrames intermediarios que nao serao mais usados
del _orders_slim, order_items
gc.collect()
print(f"  [RAM] Apos merge ordens+itens: {_ram_mb()}")

# Junta custo do produto (variante)
cost_data = dim_products[['variant_id', 'cost_price', 'product_name', 'brand_name', 'category_name', 'product_id']].copy()
fato_vendas = fato_vendas.merge(cost_data, left_on='product_variant_id', right_on='variant_id', how='left')

# Calculo de margem
fato_vendas['cost_total']   = (fato_vendas['cost_price'] * fato_vendas['quantity']).astype('float32')
fato_vendas['gross_profit'] = (fato_vendas['line_total'] - fato_vendas['cost_total']).astype('float32')
fato_vendas['margin_pct']   = (fato_vendas['gross_profit'] / fato_vendas['line_total'] * 100).round(2)

# Data como coluna Date para cruzamento com dim_calendar
fato_vendas['order_date']   = fato_vendas['placed_at'].dt.normalize()
fato_vendas['year']         = fato_vendas['placed_at'].dt.year.astype('int16')
fato_vendas['month']        = fato_vendas['placed_at'].dt.month.astype('int8')
fato_vendas['day_of_week']  = fato_vendas['placed_at'].dt.dayofweek.astype('int8')

print(f"  [RAM] Apos join de custo: {_ram_mb()}")
save(fato_vendas, 'fato_vendas.csv')

# ====================================================================
# FATO: PAGAMENTOS (fato_payments)
# ====================================================================
print("\n[6/8] Tratando fato_payments...")
payments = read_csv('payments.csv')
payments = payments.drop_duplicates(subset=['id'])
payments['paid_at']    = pd.to_datetime(payments['paid_at'],    errors='coerce')
payments['created_at'] = pd.to_datetime(payments['created_at'], errors='coerce')
fato_payments = payments.merge(
    orders[['id', 'customer_id', 'placed_at', 'channel', 'location_id']],
    left_on='order_id', right_on='id', how='left', suffixes=('', '_order')
)
save(fato_payments, 'fato_payments.csv')

# ====================================================================
# FATO: DEVOLUCOES (fato_returns)
# ====================================================================
print("[7/8] Tratando fato_returns...")
returns      = read_csv('returns.csv')
return_items = read_csv('return_items.csv')
returns = returns.drop_duplicates(subset=['id'])
returns['created_at'] = pd.to_datetime(returns['created_at'], errors='coerce')
returns['updated_at'] = pd.to_datetime(returns['updated_at'], errors='coerce')

# return_items nao tem product_variant_id direto; faz join via order_items
order_items_slim = read_csv('order_items.csv')[['id', 'product_variant_id']].rename(columns={'id': 'order_item_id'})
return_items = return_items.merge(order_items_slim, on='order_item_id', how='left')

fato_returns = return_items.merge(
    returns[['id', 'order_id', 'customer_id', 'reason', 'status', 'total_refund_amount', 'created_at']],
    left_on='return_id', right_on='id', how='left'
)
fato_returns = fato_returns.merge(
    cost_data[['variant_id', 'cost_price', 'product_name']],
    left_on='product_variant_id', right_on='variant_id', how='left'
)
fato_returns['refund_value'] = fato_returns['quantity'] * fato_returns['unit_refund_amount']

# --- Normaliza motivos de devolucao para evitar fragmentacao na analise ---
def _normalizar_motivo(motivo):
    """Lower, strip, corrige typos frequentes e padroniza para texto canonical."""
    if not isinstance(motivo, str):
        return 'Outros'
    m = motivo.strip().lower()
    m = m.replace('  ', ' ')  # espaco duplo
    # Mapeamento de variantes conhecidas para canonical
    canonical = {
        'cliente desistiu da compra':        ['cliente desistiu da compra', 'cliente desistiu', 'cliente desistui da compra'],
        'compra duplicada':                  ['compra duplicada'],
        'produto avariado no transporte':    ['produto avariado no transporte', 'produt oavariado no transporte', 'produto variado no transporte'],
        'item nao corresponde a descricao':  ['item nao corresponde a descricao', 'item nao corresponde a descricao', 'item nao corressponde a descricao', 'item nao corresponde a descricaoo'],
        'tamanho/cor incorretos':            ['tamanho/cor incorretos', 'tamanho/cor iincorretos', 'tamanho/coor incorretos', 'tamanho/cor incorretoos', 'tamanho/cor iincorretos'],
        'produto com defeito de fabrica':    ['produto com defeito de fabrica', 'produto com  defeito de fabrica', 'produto com defeitoo de fabrica', 'produto ccom defeito de fabrica', 'produt ocom defeito de fabrica'],
    }
    # Remove acentos para comparacao robusta
    import unicodedata
    def sem_acento(s):
        return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode()
    m_norm = sem_acento(m)
    for canonical_name, variantes in canonical.items():
        for v in variantes:
            if m_norm == sem_acento(v):
                return canonical_name
    return m if m else 'Outros'

fato_returns['reason'] = fato_returns['reason'].apply(_normalizar_motivo)

save(fato_returns, 'fato_returns.csv')

# ====================================================================
# FATO: ESTOQUE (fato_stock)
# ====================================================================
print("\n[8/8] Tratando fato_stock...")
stock_levels = read_csv('stock_levels.csv')
stock_mvmt   = read_csv('stock_movements.csv')
# stock_levels nao tem coluna 'id'; chave natural e product_variant_id + location_id
stock_levels = stock_levels.drop_duplicates(subset=['product_variant_id', 'location_id'])
stock_mvmt   = stock_mvmt.drop_duplicates(subset=['id'])
stock_mvmt['occurred_at'] = pd.to_datetime(stock_mvmt['occurred_at'], errors='coerce')
fato_stock = stock_mvmt.merge(
    cost_data[['variant_id', 'cost_price', 'product_name']],
    left_on='product_variant_id', right_on='variant_id', how='left'
)
# Salva niveis de estoque atual separado
stock_levels.to_csv(os.path.join(PROC_DIR, 'dim_stock_levels.csv'), index=False, encoding='utf-8-sig')
print(f"  [SALVO] dim_stock_levels.csv: {len(stock_levels):,} linhas")
save(fato_stock, 'fato_stock.csv')

# ====================================================================
# FASE 2: SUPPLY CHAIN, RH, FISCAL, LOGISTICA
# ====================================================================
print("\n[9/8] Tratando Phase 2 (RH, Fornecedores, Compras, Fiscal, Logistica)...")

# 1. dim_employees
employees = read_csv('employees.csv')
employees = employees.drop_duplicates(subset=['id'])
employees['hire_date']        = pd.to_datetime(employees['hire_date'],        errors='coerce')
employees['termination_date'] = pd.to_datetime(employees['termination_date'], errors='coerce')
dim_employees = employees.rename(columns={'id': 'employee_id'})
save(dim_employees, 'dim_employees.csv')

# 2. dim_suppliers
suppliers = read_csv('suppliers.csv')
suppliers = suppliers.drop_duplicates(subset=['id'])
dim_suppliers = suppliers.rename(columns={'id': 'supplier_id'})
save(dim_suppliers, 'dim_suppliers.csv')

# 3. dim_addresses
addresses = read_csv('addresses.csv')
addresses = addresses.drop_duplicates(subset=['id'])
dim_addresses = addresses.rename(columns={'id': 'address_id'})
save(dim_addresses, 'dim_addresses.csv')

# 4. fato_compras e goods_receipt_items
purchase_orders = read_csv('purchase_orders.csv')
purchase_order_items = read_csv('purchase_order_items.csv')
goods_receipts = read_csv('goods_receipts.csv')
goods_receipt_items = read_csv('goods_receipt_items.csv')

po_slim = purchase_orders.drop_duplicates(subset=['id'])
po_slim['placed_at'] = pd.to_datetime(po_slim['placed_at'], errors='coerce')
po_slim['expected_delivery_at'] = pd.to_datetime(po_slim['expected_delivery_at'], errors='coerce')

# Pega apenas o primeiro recebimento por PO para simplificar lead time
gr_slim = goods_receipts.sort_values('received_at').drop_duplicates(subset=['purchase_order_id'])
gr_slim['received_at'] = pd.to_datetime(gr_slim['received_at'], errors='coerce')

po_gr = po_slim.merge(gr_slim[['id', 'purchase_order_id', 'received_at']], left_on='id', right_on='purchase_order_id', how='left')
po_gr = po_gr.rename(columns={'id_x': 'id', 'id_y': 'goods_receipt_id'})

# Calcula tempo de entrega em dias
po_gr['lead_time_days'] = (po_gr['received_at'] - po_gr['placed_at']).dt.days
po_gr['delay_days'] = (po_gr['received_at'] - po_gr['expected_delivery_at']).dt.days

fato_compras = purchase_order_items.merge(
    po_gr,
    left_on='purchase_order_id', right_on='id', how='left', suffixes=('', '_po')
)

# Adiciona o volume recebido vs comprado
gri_slim = goods_receipt_items.groupby('purchase_order_item_id')['quantity_received'].sum().reset_index()
fato_compras = fato_compras.merge(gri_slim, left_on='id', right_on='purchase_order_item_id', how='left')
fato_compras['quantity_received'] = fato_compras['quantity_received'].fillna(0)

save(fato_compras, 'fato_compras.csv')

# 5. fato_fiscal
fiscal_invoices = read_csv('fiscal_invoices.csv')
fiscal_invoices = fiscal_invoices.drop_duplicates(subset=['id'])
fiscal_invoices['issued_at'] = pd.to_datetime(fiscal_invoices['issued_at'], errors='coerce')
fato_fiscal = fiscal_invoices.rename(columns={'id': 'invoice_id'})
save(fato_fiscal, 'fato_fiscal.csv')

# 6. dim_product_attributes
attributes = read_csv('attributes.csv')
var_attr_values = read_csv('variant_attribute_values.csv')
dim_product_attributes = var_attr_values.merge(attributes[['id', 'name']], left_on='attribute_id', right_on='id', how='left')
dim_product_attributes = dim_product_attributes.rename(columns={'name': 'attribute_name'}).drop(columns=['id'])

# --- Remove valores de atributo invalidos (dados de cadastro com lixo) ---
VALORES_INVALIDOS = {'fixme', 'test', 'todo', '?', '??', '???', '', 'nan'}
def _eh_invalido(val):
    if not isinstance(val, str):
        return True
    v = val.strip().lower()
    if v in VALORES_INVALIDOS:
        return True
    # Valores claramente errados: menos de 2 chars ou com caracteres especiais de debug
    if len(v) <= 1:
        return True
    return False

n_antes = len(dim_product_attributes)
dim_product_attributes = dim_product_attributes[~dim_product_attributes['value'].apply(_eh_invalido)]
n_filtrados = n_antes - len(dim_product_attributes)
if n_filtrados > 0:
    print(f"  [LIMPEZA] dim_product_attributes: {n_filtrados} registros com valores invalidos removidos")

save(dim_product_attributes, 'dim_product_attributes.csv')

# 7. dim_product_suppliers
prod_suppliers = read_csv('product_suppliers.csv')
dim_product_suppliers = prod_suppliers.drop_duplicates(subset=['product_variant_id', 'supplier_id'])
save(dim_product_suppliers, 'dim_product_suppliers.csv')

print("\n[CONCLUIDO] Script 02 - Tratamento e Modelagem finalizado.")
print(f"  Tabelas processadas em: {PROC_DIR}")
print("\n  Tabelas geradas:")
print("   - dim_customers.csv   (Dimensao de Clientes)")
print("   - dim_products.csv    (Dimensao de Produtos + Variantes)")
print("   - dim_locations.csv   (Dimensao de Locais / Lojas)")
print("   - dim_calendar.csv    (Dimensao de Tempo 2020-2026)")
print("   - dim_employees.csv   (Dimensao de Funcionarios)")
print("   - dim_suppliers.csv   (Dimensao de Fornecedores)")
print("   - dim_addresses.csv   (Dimensao de Enderecos)")
print("   - dim_product_attributes.csv (Atributos Fisicos dos Produtos)")
print("   - dim_product_suppliers.csv  (Fornecedores Homologados por Produto)")
print("   - fato_vendas.csv     (Fato Principal - Itens Vendidos)")
print("   - fato_payments.csv   (Fato de Pagamentos)")
print("   - fato_returns.csv    (Fato de Devolucoes)")
print("   - fato_stock.csv      (Fato de Movimentacao de Estoque)")
print("   - fato_compras.csv    (Fato de Pedidos de Compra a Fornecedores)")
print("   - fato_fiscal.csv     (Fato de Notas Fiscais Emitidas)")

if _db is not None:
    tabelas_db = [r[0] for r in _db.execute("SHOW TABLES").fetchall()]
    _db.close()
    print(f"\n  [DuckDB] {len(tabelas_db)} tabelas gravadas em: {DB_PATH}")
    print(f"           Tabelas: {', '.join(sorted(tabelas_db))}")
    print("  [DuckDB] Para consultar: python query_nautical.py")
