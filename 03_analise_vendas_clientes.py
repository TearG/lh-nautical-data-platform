"""
=======================================================================
SCRIPT 03 - Analise de Vendas e Clientes - LH Nautical
=======================================================================
Stakeholders: Marina Costa (Gerente de Negocios) e Sr. Almir (Fundador)
Objetivo    : Gerar todos os indicadores de performance de vendas,
              margem de lucro, analise de clientes e ranking de produtos.

Analises:
  [A] Performance Geral de Vendas (2020-2026)
  [B] Vendas por Canal (ecommerce vs loja fisica vs pos)
  [C] Vendas por Dia da Semana (com dias sem venda zerados)
  [D] Ranking de Produtos por Prejuizo (margem negativa)
  [E] Clientes com Maior Lucro Acumulado (CLV)
  [F] Analise de Devolucoes
  [G] Performance por Loja/Local
=======================================================================
"""

import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import numpy as np
import warnings
warnings.filterwarnings('ignore')

from pathlib import Path

# ---- Caminhos (relativo ao script) ----
BASE_DIR    = Path(__file__).parent
PROC_DIR    = BASE_DIR / "processed"
FIG_DIR     = BASE_DIR / "outputs" / "figures"
REPORT_DIR  = BASE_DIR / "outputs" / "reports"

os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# ---- Estilo ----
DARK_BG   = '#0f1117'
CARD_BG   = '#1a1d2e'
ACCENT1   = '#5a9fd4'   # azul
ACCENT2   = '#e05a6a'   # vermelho/coral
ACCENT3   = '#7b5ea7'   # roxo
ACCENT4   = '#4fca8b'   # verde

plt.rcParams.update({
    'figure.facecolor': DARK_BG, 'axes.facecolor': CARD_BG,
    'axes.edgecolor': '#3a3d5c', 'axes.labelcolor': '#c8cce0',
    'xtick.color': '#c8cce0',   'ytick.color': '#c8cce0',
    'text.color': '#ffffff',    'grid.color': '#2a2d3e',
    'grid.alpha': 0.5,          'font.family': 'sans-serif',
})

def fmt_brl(x, _=None):
    """Formata numero como moeda BR."""
    if x >= 1_000_000:
        return f'R$ {x/1e6:.1f}M'
    if x >= 1_000:
        return f'R$ {x/1e3:.0f}K'
    return f'R$ {x:.0f}'

print("=" * 60)
print("  LH Nautical - Script 03: Analise de Vendas & Clientes")
print("=" * 60)

# ---- Carregamento das tabelas processadas ----
print("\n[LOAD] Carregando tabelas processadas...")
fato      = pd.read_csv(os.path.join(PROC_DIR, 'fato_vendas.csv'), parse_dates=['placed_at', 'order_date'])
clientes  = pd.read_csv(os.path.join(PROC_DIR, 'dim_customers.csv'))
produtos  = pd.read_csv(os.path.join(PROC_DIR, 'dim_products.csv'))
locais    = pd.read_csv(os.path.join(PROC_DIR, 'dim_locations.csv'))
retornos  = pd.read_csv(os.path.join(PROC_DIR, 'fato_returns.csv'), parse_dates=['created_at'])
calendar  = pd.read_csv(os.path.join(PROC_DIR, 'dim_calendar.csv'), parse_dates=['date'])

# Filtrar apenas pedidos pagos/confirmados para analise de receita
fato_pago = fato[fato['status'].isin(['paid', 'confirmed', 'delivered'])]

print(f"  Pedidos pagos: {fato_pago['order_id'].nunique():,} ordens | {len(fato_pago):,} linhas de itens")

# ====================================================================
# [A] PERFORMANCE GERAL DE VENDAS - Visao Ano a Ano
# ====================================================================
print("\n[A] Calculando performance geral de vendas...")
vendas_ano = fato_pago.groupby('year').agg(
    receita_total    = ('line_total',   'sum'),
    custo_total      = ('cost_total',   'sum'),
    lucro_bruto      = ('gross_profit', 'sum'),
    qtd_pedidos      = ('order_id',     'nunique'),
    qtd_itens        = ('order_item_id','count'),
    ticket_medio     = ('total',        'mean'),
).reset_index()
vendas_ano['margem_pct'] = (vendas_ano['lucro_bruto'] / vendas_ano['receita_total'] * 100).round(2)
vendas_ano.to_csv(os.path.join(REPORT_DIR, '03a_vendas_por_ano.csv'), index=False, encoding='utf-8-sig')

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.patch.set_facecolor(DARK_BG)
fig.suptitle('Performance de Vendas - Ano a Ano', fontsize=14, fontweight='bold', color='white', y=1.02)

# Receita
ax = axes[0]
ax.bar(vendas_ano['year'], vendas_ano['receita_total'], color=ACCENT1)
ax.set_title('Receita Total (R$)', fontsize=11)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_brl))
ax.set_xlabel('Ano')

# Lucro Bruto
ax = axes[1]
colors = [ACCENT4 if v >= 0 else ACCENT2 for v in vendas_ano['lucro_bruto']]
ax.bar(vendas_ano['year'], vendas_ano['lucro_bruto'], color=colors)
ax.set_title('Lucro Bruto (R$)', fontsize=11)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_brl))
ax.set_xlabel('Ano')

# Margem %
ax = axes[2]
ax.plot(vendas_ano['year'], vendas_ano['margem_pct'], marker='o', color=ACCENT3, linewidth=2.5)
ax.fill_between(vendas_ano['year'], vendas_ano['margem_pct'], alpha=0.2, color=ACCENT3)
ax.set_title('Margem Bruta (%)', fontsize=11)
ax.set_ylabel('%')
ax.set_xlabel('Ano')

plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, '03a_performance_anual.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()

# ====================================================================
# [B] VENDAS POR CANAL
# ====================================================================
print("[B] Analisando vendas por canal...")
vendas_canal = fato_pago.groupby('channel').agg(
    receita_total = ('line_total',   'sum'),
    lucro_bruto   = ('gross_profit', 'sum'),
    qtd_pedidos   = ('order_id',     'nunique'),
).reset_index()
vendas_canal['margem_pct'] = (vendas_canal['lucro_bruto'] / vendas_canal['receita_total'] * 100).round(2)
vendas_canal['share_receita_pct'] = (vendas_canal['receita_total'] / vendas_canal['receita_total'].sum() * 100).round(1)
vendas_canal.to_csv(os.path.join(REPORT_DIR, '03b_vendas_por_canal.csv'), index=False, encoding='utf-8-sig')

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
fig.patch.set_facecolor(DARK_BG)
canal_colors = [ACCENT1, ACCENT3, ACCENT4, ACCENT2]

wedges, texts, autotexts = ax1.pie(
    vendas_canal['receita_total'], labels=vendas_canal['channel'],
    autopct='%1.1f%%', startangle=90,
    colors=canal_colors[:len(vendas_canal)],
    textprops={'color': 'white', 'fontsize': 10},
    wedgeprops={'edgecolor': DARK_BG, 'linewidth': 2}
)
ax1.set_title('Participacao na Receita por Canal', fontsize=11, pad=15)
ax1.set_facecolor(DARK_BG)

ax2.bar(vendas_canal['channel'], vendas_canal['margem_pct'],
        color=canal_colors[:len(vendas_canal)], edgecolor='none')
ax2.set_title('Margem Bruta por Canal (%)', fontsize=11)
ax2.set_ylabel('%')
ax2.set_xlabel('Canal de Venda')
for i, (v, m) in enumerate(zip(vendas_canal['channel'], vendas_canal['margem_pct'])):
    ax2.text(i, m + 0.3, f'{m:.1f}%', ha='center', fontsize=9, color='white')

plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, '03b_vendas_por_canal.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()

# ====================================================================
# [C] VENDAS MEDIAS POR DIA DA SEMANA (com zeros para dias sem venda)
# ====================================================================
print("[C] Calculando vendas medias por dia da semana...")
# Todos os dias no periodo de dados
min_date = fato_pago['order_date'].min()
max_date = fato_pago['order_date'].max()

all_days = pd.date_range(start=min_date, end=max_date, freq='D')
all_days_df = pd.DataFrame({'order_date': all_days})
all_days_df['day_of_week'] = all_days_df['order_date'].dt.dayofweek

# Receita por dia
receita_dia = fato_pago.groupby('order_date')['line_total'].sum().reset_index()
receita_dia.columns = ['order_date', 'receita_dia']

# Merge com todos os dias (dias sem venda = 0)
receita_completa = all_days_df.merge(receita_dia, on='order_date', how='left')
receita_completa['receita_dia'] = receita_completa['receita_dia'].fillna(0)

# Media por dia da semana (incluindo zeros)
media_dow = receita_completa.groupby('day_of_week')['receita_dia'].mean().reset_index()
dia_nomes = ['Segunda', 'Terca', 'Quarta', 'Quinta', 'Sexta', 'Sabado', 'Domingo']
media_dow['dia_nome'] = media_dow['day_of_week'].map(lambda x: dia_nomes[x])
media_dow.to_csv(os.path.join(REPORT_DIR, '03c_vendas_por_dia_semana.csv'), index=False, encoding='utf-8-sig')

fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor(DARK_BG)
cores_dow = [ACCENT2 if i >= 5 else ACCENT1 for i in media_dow['day_of_week']]
bars = ax.bar(media_dow['dia_nome'], media_dow['receita_dia'], color=cores_dow, edgecolor='none')
for bar, val in zip(bars, media_dow['receita_dia']):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 200,
            fmt_brl(val), ha='center', va='bottom', fontsize=9, color='white')
ax.set_title('Receita Media por Dia da Semana\n(incluindo dias sem venda como zero)', fontsize=12, fontweight='bold')
ax.set_ylabel('Receita Media (R$)')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_brl))
ax.set_xlabel('Dia da Semana')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, '03c_vendas_dia_semana.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()

# ====================================================================
# [D] RANKING DE PRODUTOS POR PREJUIZO (margem negativa)
# ====================================================================
print("[D] Identificando produtos com prejuizo...")
prejuizo_produto = fato_pago.groupby(['product_id', 'product_name', 'category_name', 'brand_name']).agg(
    receita_total  = ('line_total',   'sum'),
    custo_total    = ('cost_total',   'sum'),
    lucro_bruto    = ('gross_profit', 'sum'),
    qtd_vendida    = ('quantity',     'sum'),
).reset_index()
prejuizo_produto['margem_pct'] = (prejuizo_produto['lucro_bruto'] / prejuizo_produto['receita_total'] * 100).round(2)
produtos_negativo = prejuizo_produto[prejuizo_produto['lucro_bruto'] < 0].sort_values('lucro_bruto')
produtos_negativo.to_csv(os.path.join(REPORT_DIR, '03d_produtos_com_prejuizo.csv'), index=False, encoding='utf-8-sig')
prejuizo_produto.sort_values('lucro_bruto', ascending=False).to_csv(
    os.path.join(REPORT_DIR, '03d_ranking_margem_produtos.csv'), index=False, encoding='utf-8-sig')

top_prejuizo = produtos_negativo.head(15)
if len(top_prejuizo) > 0:
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(DARK_BG)
    short_names = top_prejuizo['product_name'].str[:35]
    bars = ax.barh(short_names, top_prejuizo['lucro_bruto'], color=ACCENT2, edgecolor='none')
    for bar, val in zip(bars, top_prejuizo['lucro_bruto']):
        ax.text(bar.get_width() - abs(bar.get_width())*0.01, bar.get_y() + bar.get_height()/2,
                fmt_brl(val), ha='right', va='center', fontsize=8, color='white', fontweight='bold')
    ax.axvline(x=0, color='white', linewidth=0.8, linestyle='--', alpha=0.5)
    ax.set_title('Top Produtos com Maior Prejuizo (Lucro Bruto Negativo)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Lucro Bruto (R$)')
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_brl))
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, '03d_produtos_prejuizo.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
    plt.close()
else:
    # Exibe os de menor margem mesmo sem ser negativa
    top_menor_margem = prejuizo_produto.sort_values('margem_pct').head(15)
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(DARK_BG)
    bars = ax.barh(top_menor_margem['product_name'].str[:35], top_menor_margem['margem_pct'],
                   color=ACCENT2, edgecolor='none')
    ax.axvline(x=0, color='white', linewidth=0.8)
    ax.set_title('Top 15 Produtos - Menor Margem Bruta (%)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Margem Bruta (%)')
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, '03d_produtos_menor_margem.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
    plt.close()
print(f"  Produtos com lucro negativo: {len(produtos_negativo)}")

# ====================================================================
# [E] CLIENTES COM MAIOR LUCRO ACUMULADO (Customer Lifetime Value)
# ====================================================================
print("[E] Calculando CLV por cliente...")
clv = fato_pago.groupby('customer_id').agg(
    receita_total  = ('line_total',    'sum'),
    custo_total    = ('cost_total',    'sum'),
    lucro_bruto    = ('gross_profit',  'sum'),
    qtd_pedidos    = ('order_id',      'nunique'),
    qtd_itens      = ('order_item_id', 'count'),
    ticket_medio   = ('total',         'mean'),
).reset_index()
clv['margem_pct'] = (clv['lucro_bruto'] / clv['receita_total'] * 100).round(2)

# Junta nome do cliente
clv = clv.merge(clientes[['customer_id', 'legal_name', 'person_type', 'email']], on='customer_id', how='left')
clv = clv.sort_values('lucro_bruto', ascending=False)
clv.to_csv(os.path.join(REPORT_DIR, '03e_clv_clientes.csv'), index=False, encoding='utf-8-sig')

# Grafico Top 20 clientes
top20 = clv.head(20)
fig, ax = plt.subplots(figsize=(12, 7))
fig.patch.set_facecolor(DARK_BG)
labels = top20.apply(lambda r: f"{r['legal_name'][:25]} ({r['person_type']})", axis=1)
bars = ax.barh(labels[::-1], top20['lucro_bruto'][::-1],
               color=ACCENT4, edgecolor='none')
for bar, val in zip(bars, top20['lucro_bruto'][::-1]):
    ax.text(bar.get_width() + 100, bar.get_y() + bar.get_height()/2,
            fmt_brl(val), va='center', fontsize=8, color='white')
ax.set_title('Top 20 Clientes - Maior Lucro Bruto Acumulado', fontsize=12, fontweight='bold')
ax.set_xlabel('Lucro Bruto (R$)')
ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_brl))
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, '03e_top_clientes_lucro.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()

# ====================================================================
# [F] ANALISE DE DEVOLUCOES
# ====================================================================
print("[F] Analisando devolucoes...")
retornos['ano_retorno'] = retornos['created_at'].dt.year
ret_ano = retornos.groupby('ano_retorno').agg(
    qtd_devolucoes = ('return_id', 'count'),
    valor_devolvido = ('refund_value', 'sum'),
).reset_index()
ret_motivo = retornos.groupby('reason').agg(
    qtd = ('return_id', 'count'),
    valor = ('refund_value', 'sum'),
).reset_index().sort_values('qtd', ascending=False)
ret_ano.to_csv(os.path.join(REPORT_DIR, '03f_devolucoes_por_ano.csv'), index=False, encoding='utf-8-sig')
ret_motivo.to_csv(os.path.join(REPORT_DIR, '03f_devolucoes_por_motivo.csv'), index=False, encoding='utf-8-sig')

# ====================================================================
# [G] PERFORMANCE POR LOCAL/LOJA
# ====================================================================
print("[G] Calculando performance por loja...")
perf_local = fato_pago.groupby('location_id').agg(
    receita_total = ('line_total',   'sum'),
    lucro_bruto   = ('gross_profit', 'sum'),
    qtd_pedidos   = ('order_id',     'nunique'),
).reset_index()
perf_local = perf_local.merge(locais[['location_id', 'name', 'location_type', 'city', 'state']], on='location_id', how='left')
perf_local['margem_pct'] = (perf_local['lucro_bruto'] / perf_local['receita_total'] * 100).round(2)
perf_local.to_csv(os.path.join(REPORT_DIR, '03g_performance_por_loja.csv'), index=False, encoding='utf-8-sig')

# ====================================================================
# RESUMO EXECUTIVO (para o Sr. Almir)
# ====================================================================
print("\n[RESUMO EXECUTIVO - SR. ALMIR]")
print("-" * 50)
print(f"  Receita Total (historico):  {fmt_brl(fato_pago['line_total'].sum())}")
print(f"  Lucro Bruto Total:          {fmt_brl(fato_pago['gross_profit'].sum())}")
print(f"  Margem Bruta Media:         {(fato_pago['gross_profit'].sum()/fato_pago['line_total'].sum()*100):.1f}%")
print(f"  Total de Pedidos (pagos):   {fato_pago['order_id'].nunique():,}")
print(f"  Clientes Unicos:            {fato_pago['customer_id'].nunique():,}")
print(f"  Produtos com Prejuizo:      {len(produtos_negativo):,}")
best_client = clv.iloc[0]
print(f"  Melhor Cliente (lucro):     {best_client['legal_name']} ({fmt_brl(best_client['lucro_bruto'])})")
best_day = media_dow.loc[media_dow['receita_dia'].idxmax()]
print(f"  Melhor dia da semana:       {best_day['dia_nome']} (media {fmt_brl(best_day['receita_dia'])})")
print("-" * 50)

print("\n[CONCLUIDO] Script 03 - Analise de Vendas & Clientes finalizado.")
