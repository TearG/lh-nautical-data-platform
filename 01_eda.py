"""
=======================================================================
SCRIPT 01 - EDA (Exploratory Data Analysis) - LH Nautical
=======================================================================
Responsavel : Gabriel Santos (Tech Lead) - Etapa de entendimento inicial
Objetivo    : Gerar um relatorio detalhado de qualidade dos dados brutos.
              Responde a pergunta: "Do que precisamos limpar antes de usar?"
=======================================================================
"""

import os
import sys
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Sem interface grafica
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import warnings
warnings.filterwarnings('ignore')

from pathlib import Path

# ---- Configuracao de caminhos (relativo ao script) ----
BASE_DIR    = Path(__file__).parent
CSV_DIR     = BASE_DIR / "1-lh_nautical_csv"
FIG_DIR     = BASE_DIR / "outputs" / "figures"
REPORT_DIR  = BASE_DIR / "outputs" / "reports"

os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# ---- Estilo de visualizacao ----
plt.rcParams.update({
    'figure.facecolor': '#0f1117',
    'axes.facecolor':   '#1a1d2e',
    'axes.edgecolor':   '#3a3d5c',
    'axes.labelcolor':  '#c8cce0',
    'xtick.color':      '#c8cce0',
    'ytick.color':      '#c8cce0',
    'text.color':       '#ffffff',
    'grid.color':       '#2a2d3e',
    'grid.alpha':       0.5,
    'font.family':      'sans-serif',
})

print("=" * 60)
print("  LH Nautical - Script 01: EDA & Qualidade dos Dados")
print("=" * 60)

# ---- 1. Carregamento de todos os CSVs ----
print("\n[1/4] Carregando arquivos CSV...")
csv_files = [f for f in os.listdir(CSV_DIR) if f.endswith('.csv')]
dataframes = {}
summary_rows = []

for fname in sorted(csv_files):
    path = os.path.join(CSV_DIR, fname)
    try:
        df = pd.read_csv(path)
        dataframes[fname] = df
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isnull().sum().sum()
        missing_pct = (missing_cells / total_cells * 100) if total_cells > 0 else 0
        dup_rows = df.duplicated().sum()
        summary_rows.append({
            "Arquivo":             fname.replace('.csv', ''),
            "Linhas":              df.shape[0],
            "Colunas":             df.shape[1],
            "Celulas_Nulas":       int(missing_cells),
            "Pct_Nula":            round(missing_pct, 2),
            "Linhas_Duplicadas":   int(dup_rows),
        })
        print(f"  [OK] {fname}: {df.shape[0]:>7,} linhas | {df.shape[1]:>2} colunas | {missing_pct:.1f}% nulo")
    except Exception as e:
        print(f"  [ERRO] {fname}: {e}")

# ---- 2. Relatorio de Qualidade ----
print("\n[2/4] Gerando relatorio de qualidade...")
summary_df = pd.DataFrame(summary_rows)
summary_df = summary_df.sort_values('Pct_Nula', ascending=False)
report_path = os.path.join(REPORT_DIR, "01_qualidade_dados.csv")
summary_df.to_csv(report_path, index=False, encoding='utf-8-sig')
print(f"  Relatorio salvo em: {report_path}")

# ---- 3. Grafico: % de Nulos por Tabela ----
print("\n[3/4] Gerando grafico de dados nulos...")
fig, ax = plt.subplots(figsize=(12, 6))
fig.patch.set_facecolor('#0f1117')

cores = ['#e05a6a' if x > 10 else '#5a9fd4' for x in summary_df['Pct_Nula']]
bars = ax.barh(summary_df['Arquivo'], summary_df['Pct_Nula'], color=cores, edgecolor='none')

for bar, val in zip(bars, summary_df['Pct_Nula']):
    if val > 0:
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f'{val:.1f}%', va='center', fontsize=8, color='#c8cce0')

ax.set_xlabel('% de celulas nulas', fontsize=10)
ax.set_title('Qualidade dos Dados - % de Nulos por Tabela', fontsize=13, fontweight='bold', pad=15)
ax.axvline(x=10, color='#e05a6a', linestyle='--', alpha=0.5, label='Limite 10%')
ax.legend(fontsize=8)
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
fig_path = os.path.join(FIG_DIR, "01_nulos_por_tabela.png")
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"  Figura salva em: {fig_path}")

# ---- 4. Grafico: Volume de Linhas por Tabela ----
print("\n[4/4] Gerando grafico de volume de dados...")
sorted_vol = summary_df.sort_values('Linhas', ascending=True)
fig, ax = plt.subplots(figsize=(12, 6))
fig.patch.set_facecolor('#0f1117')

bars = ax.barh(sorted_vol['Arquivo'], sorted_vol['Linhas'],
               color='#7b5ea7', edgecolor='none')

for bar, val in zip(bars, sorted_vol['Linhas']):
    ax.text(bar.get_width() + 200, bar.get_y() + bar.get_height() / 2,
            f'{val:,.0f}', va='center', fontsize=8, color='#c8cce0')

ax.set_xlabel('Numero de linhas', fontsize=10)
ax.set_title('Volume de Dados por Tabela', fontsize=13, fontweight='bold', pad=15)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
fig_path = os.path.join(FIG_DIR, "01_volume_por_tabela.png")
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"  Figura salva em: {fig_path}")

print("\n[CONCLUIDO] Script 01 - EDA finalizado com sucesso.")
print(f"  Relatorios em: {REPORT_DIR}")
print(f"  Figuras em:    {FIG_DIR}")
