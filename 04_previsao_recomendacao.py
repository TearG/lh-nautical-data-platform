"""
=======================================================================
SCRIPT 04 - Previsao de Demanda + Sistema de Recomendacao - LH Nautical
=======================================================================
Stakeholders: Gabriel Santos (Tech Lead) + Marina Costa (Negocios)
Objetivo    : Modelos de IA para previsao de vendas futuras e
              recomendacao de produtos para cada cliente.

Modelos:
  [A] Previsao de Demanda - Serie temporal com Prophet (ou fallback XGBoost)
  [B] Sistema de Recomendacao - Filtragem Colaborativa (Matrix Factorization)
  [C] Segmentacao de Clientes - RFM (Recencia, Frequencia, Monetario)
=======================================================================
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
import warnings
warnings.filterwarnings('ignore')

from pathlib import Path

# ---- Caminhos (relativo ao script) ----
BASE_DIR    = Path(__file__).parent
PROC_DIR    = BASE_DIR / "processed"
FIG_DIR     = BASE_DIR / "outputs" / "figures"
REPORT_DIR  = BASE_DIR / "outputs" / "reports"

DARK_BG = '#0f1117'; CARD_BG = '#1a1d2e'
ACCENT1 = '#5a9fd4'; ACCENT2 = '#e05a6a'; ACCENT3 = '#7b5ea7'; ACCENT4 = '#4fca8b'

plt.rcParams.update({
    'figure.facecolor': DARK_BG, 'axes.facecolor': CARD_BG,
    'axes.edgecolor': '#3a3d5c', 'axes.labelcolor': '#c8cce0',
    'xtick.color': '#c8cce0',   'ytick.color': '#c8cce0',
    'text.color': '#ffffff',    'grid.color': '#2a2d3e',
    'grid.alpha': 0.5,          'font.family': 'sans-serif',
})

def fmt_brl(x, _=None):
    if x >= 1_000_000: return f'R$ {x/1e6:.1f}M'
    if x >= 1_000:     return f'R$ {x/1e3:.0f}K'
    return f'R$ {x:.0f}'

print("=" * 60)
print("  LH Nautical - Script 04: Previsao & Recomendacao")
print("=" * 60)

# ---- Carregamento ----
fato     = pd.read_csv(os.path.join(PROC_DIR, 'fato_vendas.csv'), parse_dates=['placed_at', 'order_date'])
clientes = pd.read_csv(os.path.join(PROC_DIR, 'dim_customers.csv'))
produtos = pd.read_csv(os.path.join(PROC_DIR, 'dim_products.csv'))
fato_pago = fato[fato['status'].isin(['paid', 'confirmed', 'delivered'])]

# ====================================================================
# [A] PREVISAO DE DEMANDA - SERIE TEMPORAL
# ====================================================================
print("\n[A] Previsao de Demanda - Serie Temporal...")

# Receita diaria agregada
ts = fato_pago.groupby('order_date')['line_total'].sum().reset_index()
ts.columns = ['ds', 'y']
ts = ts.sort_values('ds')

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

# Tenta usar Prophet; se nao estiver instalado, usa Holt-Winters ou Media Movel
try:
    from prophet import Prophet
    print("  [INFO] Usando Prophet para previsao...")

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
        seasonality_mode='multiplicative'
    )
    model.fit(ts)

    # Preve os proximos 90 dias
    future = model.make_future_dataframe(periods=90)
    forecast = model.predict(future)

    forecast_out = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(90)
    forecast_out.columns = ['data', 'previsao_receita', 'intervalo_inf', 'intervalo_sup']
    forecast_out.to_csv(os.path.join(REPORT_DIR, '04a_previsao_demanda_90d.csv'), index=False, encoding='utf-8-sig')

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor(DARK_BG)
    # Historico (ultimos 365 dias)
    historico = ts.tail(365)
    ax.plot(historico['ds'], historico['y'], color=ACCENT1, linewidth=1.2, label='Historico', alpha=0.8)
    # Previsao
    futuro = forecast[forecast['ds'] > ts['ds'].max()]
    ax.plot(futuro['ds'], futuro['yhat'], color=ACCENT4, linewidth=2, label='Previsao (Prophet)')
    ax.fill_between(futuro['ds'], futuro['yhat_lower'], futuro['yhat_upper'],
                    color=ACCENT4, alpha=0.2, label='Intervalo de Confianca')
    ax.set_title('Previsao de Receita Diaria - Proximos 90 Dias (Prophet)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Receita (R$)')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_brl))
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, '04a_previsao_demanda_prophet.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
    plt.close()
    print("  Previsao Prophet gerada com sucesso.")

except ImportError:
    print("  [AVISO] Prophet nao instalado. Tentando modelos alternativos...")
    
    # Preparacao para fallback
    ts_full = pd.date_range(start=ts['ds'].min(), end=ts['ds'].max(), freq='D')
    ts_full_df = pd.DataFrame({'ds': ts_full})
    ts_merged = ts_full_df.merge(ts, on='ds', how='left').fillna({'y': 0})
    
    if HAS_STATSMODELS:
        print("  Utilizando Holt-Winters (Statsmodels) para previsão com tendência.")
        try:
            hw_model = ExponentialSmoothing(
                np.asarray(ts_merged['y']),
                trend='add',
                seasonal=None,
                initialization_method="estimated"
            ).fit()
            
            future_dates = pd.date_range(start=ts['ds'].max() + pd.Timedelta(days=1), periods=90, freq='D')
            forecast_values = hw_model.forecast(90)
            residuals = hw_model.resid
            std_error = np.std(residuals)
            z_score = 1.96 
            
            forecast_out = pd.DataFrame({
                'data': future_dates,
                'previsao_receita': forecast_values.clip(lower=0),
                'intervalo_inf': (forecast_values - (z_score * std_error)).clip(lower=0),
                'intervalo_sup': (forecast_values + (z_score * std_error)).clip(lower=0)
            })
            forecast_out.to_csv(os.path.join(REPORT_DIR, '04a_previsao_demanda_90d.csv'), index=False, encoding='utf-8-sig')
            fig_name = '04a_previsao_demanda_hw.png'
            print("  Previsao por Holt-Winters gerada.")
        except Exception as e:
            print(f"  [AVISO] Erro no Holt-Winters: {e}. Fallback Média Móvel.")
            HAS_STATSMODELS = False

    if not HAS_STATSMODELS:
        # Fallback: Media Movel de 30 dias
        ts_merged['ma7']  = ts_merged['y'].rolling(7,  min_periods=1).mean()
        ts_merged['ma30'] = ts_merged['y'].rolling(30, min_periods=1).mean()

        baseline = ts_merged['y'].tail(30).mean()
        trend_daily = (ts_merged['y'].tail(60).mean() - ts_merged['y'].head(60).mean()) / len(ts_merged)
        future_dates = pd.date_range(start=ts['ds'].max() + pd.Timedelta(days=1), periods=90, freq='D')
        future_preds = [baseline + trend_daily * i for i in range(1, 91)]
        forecast_out = pd.DataFrame({
            'data':             future_dates,
            'previsao_receita': future_preds,
            'intervalo_inf':    [p * 0.85 for p in future_preds],
            'intervalo_sup':    [p * 1.15 for p in future_preds],
        })
        forecast_out.to_csv(os.path.join(REPORT_DIR, '04a_previsao_demanda_90d.csv'), index=False, encoding='utf-8-sig')
        fig_name = '04a_previsao_demanda_ma.png'
        print("  Previsao por Media Movel gerada.")

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor(DARK_BG)
    ax.plot(ts_merged['ds'].tail(365), ts_merged['y'].tail(365), color=ACCENT1, alpha=0.5, linewidth=0.8, label='Historico')
    ax.plot(forecast_out['data'], forecast_out['previsao_receita'], color=ACCENT4, linewidth=2, linestyle='--', label='Projecao 90d')
    ax.fill_between(forecast_out['data'], forecast_out['intervalo_inf'], forecast_out['intervalo_sup'],
                    color=ACCENT4, alpha=0.15, label='Intervalo +/-15%')
    ax.set_title('Previsao de Receita Diaria - Proximos 90 Dias (Holt-Winters)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Receita (R$)')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_brl))
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, '04a_previsao_demanda_ma.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
    plt.close()
    print("  Previsao por Media Movel gerada.")

# ====================================================================
# [B] SEGMENTACAO DE CLIENTES - ANALISE RFM
# ====================================================================
print("\n[B] Segmentacao RFM de Clientes...")
data_referencia = fato_pago['order_date'].max()

rfm = fato_pago.groupby('customer_id').agg(
    data_ultimo_pedido = ('order_date',    'max'),
    frequencia         = ('order_id',      'nunique'),
    monetario          = ('line_total',    'sum'),
).reset_index()

rfm['recency_days'] = (data_referencia - rfm['data_ultimo_pedido']).dt.days

# Pontuacao (1-5 para cada dimensao)
rfm['R_score'] = pd.qcut(rfm['recency_days'], q=5, labels=[5,4,3,2,1], duplicates='drop').astype(float)
rfm['F_score'] = pd.qcut(rfm['frequencia'],  q=5, labels=[1,2,3,4,5], duplicates='drop').astype(float)
rfm['M_score'] = pd.qcut(rfm['monetario'],   q=5, labels=[1,2,3,4,5], duplicates='drop').astype(float)

rfm['RFM_score'] = rfm['R_score'].fillna(1) + rfm['F_score'].fillna(1) + rfm['M_score'].fillna(1)

def classificar_rfm(score):
    if score >= 13: return 'Champions'
    if score >= 10: return 'Loyal Customers'
    if score >= 7:  return 'Potential Loyalist'
    if score >= 5:  return 'At Risk'
    return 'Lost'

rfm['segmento'] = rfm['RFM_score'].apply(classificar_rfm)
rfm = rfm.merge(clientes[['customer_id', 'legal_name', 'person_type']], on='customer_id', how='left')
rfm = rfm.sort_values('RFM_score', ascending=False)
rfm.to_csv(os.path.join(REPORT_DIR, '04b_segmentacao_rfm.csv'), index=False, encoding='utf-8-sig')

# Grafico de distribuicao por segmento
seg_counts = rfm['segmento'].value_counts()
seg_order  = ['Champions', 'Loyal Customers', 'Potential Loyalist', 'At Risk', 'Lost']
seg_colors = [ACCENT4, ACCENT1, ACCENT3, '#f0a830', ACCENT2]
seg_counts = seg_counts.reindex([s for s in seg_order if s in seg_counts.index])

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
fig.patch.set_facecolor(DARK_BG)

# Contagem
ax1.bar(seg_counts.index, seg_counts.values, color=seg_colors[:len(seg_counts)], edgecolor='none')
for i, v in enumerate(seg_counts.values):
    ax1.text(i, v + 1, str(v), ha='center', fontsize=10, color='white', fontweight='bold')
ax1.set_title('Distribuicao de Clientes por Segmento RFM', fontsize=11, fontweight='bold')
ax1.set_ylabel('N. de Clientes')
plt.setp(ax1.get_xticklabels(), rotation=20, ha='right', fontsize=9)

# Receita por segmento
seg_receita = rfm.groupby('segmento')['monetario'].sum().reindex(seg_order).dropna()
ax2.bar(seg_receita.index, seg_receita.values, color=seg_colors[:len(seg_receita)], edgecolor='none')
ax2.set_title('Receita Total por Segmento RFM', fontsize=11, fontweight='bold')
ax2.set_ylabel('Receita (R$)')
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_brl))
plt.setp(ax2.get_xticklabels(), rotation=20, ha='right', fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, '04b_segmentacao_rfm.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()
print(f"  Segmentos identificados: {rfm['segmento'].value_counts().to_dict()}")

# ====================================================================
# [C] SISTEMA DE RECOMENDACAO - FILTRAGEM COLABORATIVA (SVD)
# ====================================================================
print("\n[C] Sistema de Recomendacao por Filtragem Colaborativa (SVD)...")

# Cria matriz Cliente x Produto (frequencia de compra como "rating")
rating_matrix = fato_pago.groupby(['customer_id', 'product_id'])['quantity'].sum().reset_index()
rating_matrix.columns = ['customer_id', 'product_id', 'rating']

# Pivotagem - amostra dos clientes mais ativos para performance
top_customers = fato_pago.groupby('customer_id')['order_id'].nunique().nlargest(500).index
rating_sample = rating_matrix[rating_matrix['customer_id'].isin(top_customers)]

pivot = rating_sample.pivot_table(index='customer_id', columns='product_id', values='rating', fill_value=0)

# Normaliza
scaler = MinMaxScaler()
pivot_norm = pd.DataFrame(scaler.fit_transform(pivot), index=pivot.index, columns=pivot.columns)

# SVD (Decomposicao matricial com 20 componentes latentes)
n_components = min(20, min(pivot_norm.shape) - 1)
svd = TruncatedSVD(n_components=n_components, random_state=42)
latent_matrix = svd.fit_transform(pivot_norm)

# Reconstrucao para predicao de scores
predicted_ratings = pd.DataFrame(
    svd.inverse_transform(latent_matrix),
    index=pivot_norm.index,
    columns=pivot_norm.columns
)

# Gera top-5 recomendacoes para cada cliente (exclui produtos ja comprados)
recomendacoes = []
produto_nomes = produtos[['product_id', 'product_name', 'category_name']].drop_duplicates('product_id')

for cid in predicted_ratings.index[:100]:  # limita a 100 clientes para o relatorio
    ja_comprou = set(rating_sample[rating_sample['customer_id'] == cid]['product_id'])
    scores = predicted_ratings.loc[cid].drop(labels=list(ja_comprou), errors='ignore')
    top5 = scores.nlargest(5)
    for rank, (pid, score) in enumerate(top5.items(), 1):
        info = produto_nomes[produto_nomes['product_id'] == pid]
        nome = info['product_name'].values[0] if len(info) > 0 else f"Produto {pid}"
        cat  = info['category_name'].values[0] if len(info) > 0 else 'N/A'
        recomendacoes.append({
            'customer_id': cid, 'rank': rank, 'product_id': int(pid),
            'product_name': nome, 'category_name': cat, 'score_svd': round(float(score), 4)
        })

rec_df = pd.DataFrame(recomendacoes)
rec_df = rec_df.merge(clientes[['customer_id', 'legal_name']], on='customer_id', how='left')
rec_df.to_csv(os.path.join(REPORT_DIR, '04c_recomendacoes_por_cliente.csv'), index=False, encoding='utf-8-sig')
print(f"  Recomendacoes geradas para {rec_df['customer_id'].nunique()} clientes.")
print(f"  Variancia explicada pelo SVD: {svd.explained_variance_ratio_.sum()*100:.1f}%")

# Grafico de variancia explicada
fig, ax = plt.subplots(figsize=(9, 4))
fig.patch.set_facecolor(DARK_BG)
var_cum = np.cumsum(svd.explained_variance_ratio_) * 100
ax.plot(range(1, len(var_cum)+1), var_cum, marker='o', color=ACCENT1, linewidth=2)
ax.fill_between(range(1, len(var_cum)+1), var_cum, alpha=0.2, color=ACCENT1)
ax.axhline(y=80, color=ACCENT4, linestyle='--', alpha=0.7, label='80% explicado')
ax.set_title('Variancia Acumulada Explicada pelo SVD (Recomendacao)', fontsize=11, fontweight='bold')
ax.set_xlabel('Numero de Componentes Latentes')
ax.set_ylabel('Variancia Explicada (%)')
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, '04c_svd_variancia.png'), dpi=150, bbox_inches='tight', facecolor=DARK_BG)
plt.close()

print("\n[CONCLUIDO] Script 04 - Previsao & Recomendacao finalizado.")
print(f"  Relatorios: {REPORT_DIR}")
print(f"  Figuras:    {FIG_DIR}")
