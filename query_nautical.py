"""
=======================================================================
query_nautical.py - Demonstracao de Consultas via DuckDB
=======================================================================
Mostra como consultar as tabelas do LH Nautical diretamente via DuckDB,
sem precisar carregar os dados em Pandas.

Pre-requisito:
  pip install duckdb
  python run_all.py   (para gerar o banco nautical.duckdb)

Uso:
  python query_nautical.py
=======================================================================
"""

from pathlib import Path
import sys

try:
    import duckdb
except ImportError:
    print("[ERRO] duckdb nao instalado. Execute: pip install duckdb")
    sys.exit(1)

DB_PATH = Path(__file__).parent / "nautical.duckdb"

if not DB_PATH.exists():
    print(f"[ERRO] Banco {DB_PATH} nao encontrado.")
    print("       Execute 'python run_all.py' primeiro para gerar o banco.")
    sys.exit(1)

con = duckdb.connect(str(DB_PATH), read_only=True)

sep = "=" * 65

# --- Lista de tabelas disponíveis ---
print(sep)
print("  LH Nautical - DuckDB Analytics")
print(f"  Banco: {DB_PATH}")
print(sep)
tabelas = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
print(f"\n  Tabelas disponíveis ({len(tabelas)}):")
for t in sorted(tabelas):
    n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"    - {t:<40}  {n:>10,} linhas")

# =======================================================================
# CONSULTA 1: Top 10 produtos por receita total
# =======================================================================
print(f"\n{sep}")
print("  [1] Top 10 Produtos por Receita Total")
print(sep)
q1 = con.execute("""
    SELECT
        product_name,
        brand_name,
        category_name,
        SUM(line_total)         AS receita_total,
        SUM(gross_profit)       AS lucro_bruto,
        ROUND(AVG(margin_pct), 1) AS margem_media_pct
    FROM fato_vendas
    WHERE status IN ('paid', 'confirmed', 'delivered')
      AND line_total > 0
    GROUP BY product_name, brand_name, category_name
    ORDER BY receita_total DESC
    LIMIT 10
""").df()
print(q1.to_string(index=False))

# =======================================================================
# CONSULTA 2: Receita mensal 2024-2025 (tendência)
# =======================================================================
print(f"\n{sep}")
print("  [2] Receita Mensal (2024-2025)")
print(sep)
q2 = con.execute("""
    SELECT
        year,
        month,
        SUM(line_total)      AS receita,
        COUNT(DISTINCT order_id) AS pedidos,
        ROUND(SUM(line_total) / COUNT(DISTINCT order_id), 2) AS ticket_medio
    FROM fato_vendas
    WHERE status IN ('paid', 'confirmed', 'delivered')
      AND year IN (2024, 2025)
    GROUP BY year, month
    ORDER BY year, month
""").df()
print(q2.to_string(index=False))

# =======================================================================
# CONSULTA 3: Lead time médio por fornecedor (Supply Chain)
# =======================================================================
print(f"\n{sep}")
print("  [3] Lead Time e Atraso Medio por Fornecedor (Top 10 por volume)")
print(sep)
q3 = con.execute("""
    SELECT
        s.name                          AS fornecedor,
        COUNT(*)                        AS ordens_compra,
        ROUND(AVG(fc.lead_time_days), 1) AS lead_time_medio_dias,
        ROUND(AVG(fc.delay_days), 1)    AS atraso_medio_dias,
        SUM(fc.quantity_ordered)        AS qtd_comprada_total
    FROM fato_compras fc
    JOIN dim_suppliers s ON fc.supplier_id = s.supplier_id
    WHERE fc.lead_time_days IS NOT NULL
    GROUP BY s.name
    ORDER BY ordens_compra DESC
    LIMIT 10
""").df()
print(q3.to_string(index=False))

# =======================================================================
# CONSULTA 4: Reconciliacao fiscal (NF-e vs Pedidos pagos)
# =======================================================================
print(f"\n{sep}")
print("  [4] Reconciliacao Fiscal: Receita Pipeline vs NF-e")
print(sep)
receita_pipeline = con.execute("""
    SELECT SUM(line_total) FROM fato_vendas
    WHERE status IN ('paid', 'confirmed', 'delivered')
""").fetchone()[0]

receita_nfe = con.execute("""
    SELECT SUM(total_amount) FROM fato_fiscal
    WHERE status = 'authorized'
""").fetchone()[0] or 0

cobertura = receita_nfe / receita_pipeline * 100 if receita_pipeline else 0
print(f"  Receita pipeline (todos pagos):  R$ {receita_pipeline:>18,.2f}")
print(f"  Receita NF-e (só autorizadas):   R$ {receita_nfe:>18,.2f}")
print(f"  Cobertura fiscal:                {cobertura:>17.1f}%")
if cobertura < 70:
    print("  [ATENCAO] Cobertura fiscal abaixo de 70% — investigar NF-es pendentes.")

print(f"\n{sep}")
print("  Consultas concluidas. Use con = duckdb.connect('nautical.duckdb')")
print("  para criar suas proprias queries SQL no DuckDB.")
print(sep)

con.close()
