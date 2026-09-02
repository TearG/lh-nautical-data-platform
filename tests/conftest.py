# =============================================================================
# tests/conftest.py
#
# OBJETIVO  : Fixtures compartilhadas entre todos os testes do projeto.
#             Carrega amostras dos dados brutos e das tabelas processadas
#             uma única vez, disponibilizando para todos os módulos de teste.
#
# POR QUÊ  : Fixtures centralizadas evitam duplicação de código de setup.
#             O Gabriel Santos valoriza DRY (Don't Repeat Yourself) e 
#             organização — conftest.py é a solução idiomática do pytest.
# =============================================================================

import pytest
import pandas as pd
from pathlib import Path

# Caminhos relativos ao projeto (tests/ -> nautical/)
BASE_DIR    = Path(__file__).parent.parent
BRONZE_DIR  = BASE_DIR / "1-lh_nautical_csv"
SILVER_DIR  = BASE_DIR / "processed"
REPORTS_DIR = BASE_DIR / "outputs" / "reports"


# ---------------------------------------------------------------------------
# Fixtures — Dados BRUTOS (Bronze Layer)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def raw_orders():
    return pd.read_csv(BRONZE_DIR / "orders.csv")

@pytest.fixture(scope="session")
def raw_order_items():
    return pd.read_csv(BRONZE_DIR / "order_items.csv")

@pytest.fixture(scope="session")
def raw_customers():
    return pd.read_csv(BRONZE_DIR / "customers.csv")

@pytest.fixture(scope="session")
def raw_payments():
    return pd.read_csv(BRONZE_DIR / "payments.csv")

@pytest.fixture(scope="session")
def raw_products():
    return pd.read_csv(BRONZE_DIR / "products.csv")

@pytest.fixture(scope="session")
def raw_variants():
    return pd.read_csv(BRONZE_DIR / "product_variants.csv")

@pytest.fixture(scope="session")
def raw_returns():
    return pd.read_csv(BRONZE_DIR / "returns.csv")

@pytest.fixture(scope="session")
def raw_return_items():
    return pd.read_csv(BRONZE_DIR / "return_items.csv")

@pytest.fixture(scope="session")
def raw_fiscal():
    return pd.read_csv(BRONZE_DIR / "fiscal_invoices.csv")

@pytest.fixture(scope="session")
def raw_stock_levels():
    return pd.read_csv(BRONZE_DIR / "stock_levels.csv")

@pytest.fixture(scope="session")
def raw_stock_movements():
    return pd.read_csv(BRONZE_DIR / "stock_movements.csv")

@pytest.fixture(scope="session")
def raw_locations():
    return pd.read_csv(BRONZE_DIR / "locations.csv")

@pytest.fixture(scope="session")
def raw_suppliers():
    return pd.read_csv(BRONZE_DIR / "suppliers.csv")

@pytest.fixture(scope="session")
def raw_purchase_orders():
    return pd.read_csv(BRONZE_DIR / "purchase_orders.csv")

@pytest.fixture(scope="session")
def raw_purchase_order_items():
    return pd.read_csv(BRONZE_DIR / "purchase_order_items.csv")

@pytest.fixture(scope="session")
def raw_goods_receipt_items():
    return pd.read_csv(BRONZE_DIR / "goods_receipt_items.csv")


# ---------------------------------------------------------------------------
# Fixtures — Dados PROCESSADOS (Silver Layer)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def fato_vendas():
    return pd.read_csv(
        SILVER_DIR / "fato_vendas.csv",
        parse_dates=["placed_at", "order_date"]
    )

@pytest.fixture(scope="session")
def fato_payments():
    return pd.read_csv(SILVER_DIR / "fato_payments.csv")

@pytest.fixture(scope="session")
def fato_returns():
    return pd.read_csv(SILVER_DIR / "fato_returns.csv", parse_dates=["created_at"])

@pytest.fixture(scope="session")
def dim_customers():
    return pd.read_csv(SILVER_DIR / "dim_customers.csv")

@pytest.fixture(scope="session")
def dim_products():
    return pd.read_csv(SILVER_DIR / "dim_products.csv")

@pytest.fixture(scope="session")
def dim_locations():
    return pd.read_csv(SILVER_DIR / "dim_locations.csv")

@pytest.fixture(scope="session")
def dim_calendar():
    return pd.read_csv(SILVER_DIR / "dim_calendar.csv", parse_dates=["date"])

@pytest.fixture(scope="session")
def fato_stock():
    return pd.read_csv(SILVER_DIR / "fato_stock.csv")


# ---------------------------------------------------------------------------
# Fixtures — Relatórios (Gold Layer)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def report_vendas_ano():
    return pd.read_csv(REPORTS_DIR / "03a_vendas_por_ano.csv")

@pytest.fixture(scope="session")
def report_clv():
    return pd.read_csv(REPORTS_DIR / "03e_clv_clientes.csv")

@pytest.fixture(scope="session")
def report_rfm():
    return pd.read_csv(REPORTS_DIR / "04b_segmentacao_rfm.csv")

@pytest.fixture(scope="session")
def report_dia_semana():
    return pd.read_csv(REPORTS_DIR / "03c_vendas_por_dia_semana.csv")

@pytest.fixture(scope="session")
def report_canal():
    return pd.read_csv(REPORTS_DIR / "03b_vendas_por_canal.csv")

@pytest.fixture(scope="session")
def report_devolucoes():
    return pd.read_csv(REPORTS_DIR / "03f_devolucoes_por_ano.csv")

@pytest.fixture(scope="session")
def report_recomendacoes():
    return pd.read_csv(REPORTS_DIR / "04c_recomendacoes_por_cliente.csv")

# ====================================================================
# FASE 2: SUPPLY CHAIN, RH, LOGISTICA, FISCAL
# ====================================================================
@pytest.fixture(scope="session")
def dim_employees():
    return pd.read_csv(SILVER_DIR / "dim_employees.csv")

@pytest.fixture(scope="session")
def dim_suppliers():
    return pd.read_csv(SILVER_DIR / "dim_suppliers.csv")

@pytest.fixture(scope="session")
def dim_addresses():
    return pd.read_csv(SILVER_DIR / "dim_addresses.csv")

@pytest.fixture(scope="session")
def fato_compras():
    return pd.read_csv(SILVER_DIR / "fato_compras.csv")

@pytest.fixture(scope="session")
def fato_fiscal():
    return pd.read_csv(SILVER_DIR / "fato_fiscal.csv")
