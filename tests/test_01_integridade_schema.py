# =============================================================================
# tests/test_01_integridade_schema.py
#
# FRENTE   : EDA e Tratamento de Dados
# OBJETIVO : Valida a integridade estrutural dos dados brutos (Bronze Layer).
#            Estes são os testes de P0 — se falharem, o pipeline não deve rodar.
#
# STAKEHOLDER: Gabriel Santos (Tech Lead) — "Quero saber onde o dado quebra
#              antes de qualquer análise."
# =============================================================================

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

BRONZE_DIR = Path(__file__).parent.parent / "1-lh_nautical_csv"


# =============================================================================
# Bloco A — Presença dos arquivos obrigatórios
# =============================================================================

class TestPresencaArquivos:
    """Garante que todos os 24 CSVs esperados estão presentes na pasta bronze."""

    ARQUIVOS_OBRIGATORIOS = [
        "orders.csv", "order_items.csv", "customers.csv", "payments.csv",
        "products.csv", "product_variants.csv", "returns.csv", "return_items.csv",
        "fiscal_invoices.csv", "stock_levels.csv", "stock_movements.csv",
        "locations.csv", "employees.csv", "brands.csv", "categories.csv",
        "addresses.csv", "suppliers.csv", "product_suppliers.csv",
        "purchase_orders.csv", "purchase_order_items.csv",
        "goods_receipts.csv", "goods_receipt_items.csv",
        "attributes.csv", "variant_attribute_values.csv",
    ]

    @pytest.mark.parametrize("arquivo", ARQUIVOS_OBRIGATORIOS)
    def test_arquivo_existe(self, arquivo):
        """Verifica se cada CSV obrigatório existe na pasta de dados brutos."""
        path = BRONZE_DIR / arquivo
        assert path.exists(), f"ARQUIVO FALTANDO: {arquivo} não encontrado em {BRONZE_DIR}"

    def test_total_24_arquivos(self):
        """Confirma que há exatamente 24 arquivos CSV na pasta bronze."""
        csvs = list(BRONZE_DIR.glob("*.csv"))
        assert len(csvs) == 24, f"Esperado 24 CSVs, encontrado: {len(csvs)}"


# =============================================================================
# Bloco B — Colunas obrigatórias (Contrato de Schema)
# =============================================================================

class TestSchemaColunas:
    """
    Valida que cada tabela contém as colunas mínimas esperadas.
    POR QUÊ: Schema drift é silencioso e perigoso — uma coluna renomeada
    em produção pode corromper todas as análises downstream sem aviso.
    """

    @pytest.mark.parametrize("col", ["id", "order_number", "channel",
                                      "customer_id", "location_id", "status",
                                      "subtotal", "total", "placed_at"])
    def test_orders_tem_colunas_obrigatorias(self, raw_orders, col):
        assert col in raw_orders.columns, f"orders.csv: coluna '{col}' ausente"

    @pytest.mark.parametrize("col", ["id", "order_id", "product_variant_id",
                                      "quantity", "unit_price", "line_total"])
    def test_order_items_tem_colunas_obrigatorias(self, raw_order_items, col):
        assert col in raw_order_items.columns, f"order_items.csv: coluna '{col}' ausente"

    @pytest.mark.parametrize("col", ["id", "person_type", "legal_name",
                                      "tax_id", "is_active"])
    def test_customers_tem_colunas_obrigatorias(self, raw_customers, col):
        assert col in raw_customers.columns, f"customers.csv: coluna '{col}' ausente"

    @pytest.mark.parametrize("col", ["id", "product_id", "sku",
                                      "cost_price", "sale_price", "is_active"])
    def test_variants_tem_colunas_obrigatorias(self, raw_variants, col):
        assert col in raw_variants.columns, f"product_variants.csv: coluna '{col}' ausente"

    @pytest.mark.parametrize("col", ["product_variant_id", "location_id", "quantity_on_hand"])
    def test_stock_levels_tem_colunas_obrigatorias(self, raw_stock_levels, col):
        assert col in raw_stock_levels.columns, f"stock_levels.csv: coluna '{col}' ausente"


# =============================================================================
# Bloco C — Chaves Primárias (P0 — crítico)
# =============================================================================

class TestChavesPrimarias:
    """
    Verifica integridade das chaves primárias.
    POR QUÊ: PKs nulas ou duplicadas quebram todos os JOINs do pipeline.
    """

    def test_orders_pk_sem_nulos(self, raw_orders):
        nulos = raw_orders['id'].isnull().sum()
        assert nulos == 0, f"orders.id tem {nulos} valores NULOS — PK inválida!"

    def test_orders_pk_sem_duplicatas(self, raw_orders):
        dups = raw_orders['id'].duplicated().sum()
        assert dups == 0, f"orders.id tem {dups} DUPLICATAS — PK inválida!"

    def test_order_items_pk_sem_nulos(self, raw_order_items):
        assert raw_order_items['id'].isnull().sum() == 0

    def test_order_items_pk_sem_duplicatas(self, raw_order_items):
        assert raw_order_items['id'].duplicated().sum() == 0

    def test_customers_pk_sem_nulos(self, raw_customers):
        assert raw_customers['id'].isnull().sum() == 0

    def test_customers_pk_sem_duplicatas(self, raw_customers):
        assert raw_customers['id'].duplicated().sum() == 0

    def test_payments_pk_sem_nulos(self, raw_payments):
        assert raw_payments['id'].isnull().sum() == 0

    def test_products_pk_sem_nulos(self, raw_products):
        assert raw_products['id'].isnull().sum() == 0

    def test_variants_pk_sem_nulos(self, raw_variants):
        assert raw_variants['id'].isnull().sum() == 0

    def test_stock_levels_chave_natural_sem_duplicatas(self, raw_stock_levels):
        """
        stock_levels não tem coluna 'id'; a chave natural é composta.
        POR QUÊ: Dois registros de nível de estoque para o mesmo
        produto+local seria uma inconsistência operacional.
        """
        dups = raw_stock_levels.duplicated(subset=['product_variant_id', 'location_id']).sum()
        assert dups == 0, f"stock_levels tem {dups} combinações product+location duplicadas"


# =============================================================================
# Bloco D — Integridade Referencial (Chaves Estrangeiras)
# =============================================================================

class TestIntegridadeReferencial:
    """
    Verifica que FKs referenciam registros que existem.
    POR QUÊ: Dados órfãos causam métricas erradas silenciosamente.
    """

    def test_order_items_fk_orders(self, raw_order_items, raw_orders):
        """Todo item de pedido deve ter um pedido pai válido."""
        order_ids  = set(raw_orders['id'])
        item_fks   = set(raw_order_items['order_id'].dropna())
        orfaos     = item_fks - order_ids
        assert len(orfaos) == 0, (
            f"{len(orfaos)} order_items com order_id inexistente em orders: "
            f"{list(orfaos)[:5]}"
        )

    def test_payments_fk_orders(self, raw_payments, raw_orders):
        """Todo pagamento deve referenciar um pedido válido."""
        order_ids = set(raw_orders['id'])
        pay_fks   = set(raw_payments['order_id'].dropna())
        orfaos    = pay_fks - order_ids
        assert len(orfaos) == 0, f"{len(orfaos)} payments com order_id inválido"

    def test_returns_fk_orders(self, raw_returns, raw_orders):
        """Toda devolução deve referenciar um pedido existente."""
        order_ids  = set(raw_orders['id'])
        return_fks = set(raw_returns['order_id'].dropna())
        orfaos     = return_fks - order_ids
        assert len(orfaos) == 0, f"{len(orfaos)} devoluções sem pedido correspondente"

    def test_fiscal_fk_orders(self, raw_fiscal, raw_orders):
        """Toda NF-e deve referenciar um pedido válido."""
        order_ids = set(raw_orders['id'])
        nfe_fks   = set(raw_fiscal['order_id'].dropna())
        orfaos    = nfe_fks - order_ids
        assert len(orfaos) == 0, f"{len(orfaos)} NF-es sem pedido correspondente"

    def test_order_items_fk_variants(self, raw_order_items, raw_variants):
        """Todo item deve referenciar uma variante de produto válida."""
        variant_ids = set(raw_variants['id'])
        item_fks    = set(raw_order_items['product_variant_id'].dropna())
        orfaos      = item_fks - variant_ids
        assert len(orfaos) == 0, f"{len(orfaos)} itens com product_variant_id inválido"
