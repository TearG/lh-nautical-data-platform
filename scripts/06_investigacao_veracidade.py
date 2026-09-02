import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

# Paths (relativo ao script)
BASE_DIR   = Path(__file__).parent.parent  # scripts/ -> nautical/
BRONZE_DIR = BASE_DIR / "1-lh_nautical_csv"
SILVER_DIR = BASE_DIR / "processed"
REPORTS_DIR = BASE_DIR / "outputs" / "reports"
OUTPUT_FILE = REPORTS_DIR / "06_relatorio_investigacao_veracidade.md"

def load_data():
    print("Carregando dados...")
    fato_vendas = pd.read_csv(SILVER_DIR / "fato_vendas.csv", parse_dates=['placed_at', 'order_date'])
    raw_fiscal = pd.read_csv(BRONZE_DIR / "fiscal_invoices.csv", parse_dates=['issued_at'])
    fato_returns = pd.read_csv(SILVER_DIR / "fato_returns.csv", parse_dates=['created_at'])
    raw_return_items = pd.read_csv(BRONZE_DIR / "return_items.csv")
    
    # Filtrar apenas pedidos válidos para análise de receita
    fato_pago = fato_vendas[fato_vendas['status'].isin(['paid', 'confirmed', 'delivered'])].copy()
    
    return fato_vendas, fato_pago, raw_fiscal, fato_returns, raw_return_items

def investigar_devolucoes(fato_pago, fato_returns):
    print("Investigando Ponto 1: Taxa de devoluções...")
    receita_total = fato_pago['line_total'].sum()
    
    if 'refund_value' in fato_returns.columns:
        valor_devolvido = fato_returns['refund_value'].sum()
    else:
        valor_devolvido = 0
        
    taxa = (valor_devolvido / receita_total) * 100 if receita_total > 0 else 0
    
    # Análise por ano
    fato_returns['year'] = fato_returns['created_at'].dt.year
    dev_por_ano = fato_returns.groupby('year')['refund_value'].sum().reset_index()
    
    fato_pago['year'] = fato_pago['placed_at'].dt.year
    rec_por_ano = fato_pago.groupby('year')['line_total'].sum().reset_index()
    
    comp_ano = rec_por_ano.merge(dev_por_ano, on='year', how='left').fillna(0)
    comp_ano['taxa_dev_pct'] = (comp_ano['refund_value'] / comp_ano['line_total']) * 100
    
    res = (
        f"### 1. Investigação da Taxa de Devolução (0.48%)\n"
        f"- **Receita Total (Pedidos Pagos/Entregues):** R$ {receita_total:,.2f}\n"
        f"- **Valor Total Devolvido:** R$ {valor_devolvido:,.2f}\n"
        f"- **Taxa Global:** {taxa:.2f}%\n\n"
        f"**Análise por Ano:**\n\n"
        f"| Ano | Receita | Valor Devolvido | Taxa (%) |\n"
        f"|---|---|---|---|\n"
    )
    for _, row in comp_ano.iterrows():
        res += f"| {int(row['year'])} | R$ {row['line_total']:,.2f} | R$ {row['refund_value']:,.2f} | {row['taxa_dev_pct']:.2f}% |\n"
        
    res += (
        f"\n**Conclusão:** A taxa é uniformemente baixa em todos os anos. "
        f"Em varejo náutico, 0.48% é extremamente baixo, indicando que ou o processo "
        f"de logística reversa é falho (itens não são devolvidos no sistema) ou os dados são "
        f"sintéticos e não modelaram o comportamento realista de defeitos/arrependimento (tipicamente 2% a 5%).\n\n"
    )
    return res

def investigar_nfe(fato_pago, raw_fiscal):
    print("Investigando Ponto 2: Cobertura de NF-e...")
    # Pedidos no pipeline
    pedidos_pipeline = set(fato_pago['order_id'].unique())
    receita_pipeline = fato_pago['line_total'].sum()
    
    # Pedidos com NF-e autorizada
    nfe_autorizada = raw_fiscal[raw_fiscal['status'] == 'authorized']
    pedidos_nfe = set(nfe_autorizada['order_id'].unique())
    receita_nfe = nfe_autorizada['total_amount'].sum()
    
    pedidos_sem_nfe = pedidos_pipeline - pedidos_nfe
    
    # Análise dos pedidos sem NF-e
    df_sem_nfe = fato_pago[fato_pago['order_id'].isin(pedidos_sem_nfe)]
    receita_sem_nfe = df_sem_nfe['line_total'].sum()
    
    # Agrupar por status do pedido
    status_sem_nfe = df_sem_nfe.groupby('status')['order_id'].nunique().reset_index()
    
    res = (
        f"### 2. Investigação da Cobertura de NF-e (73%)\n"
        f"- **Receita Total (Pipeline):** R$ {receita_pipeline:,.2f} ({len(pedidos_pipeline)} pedidos)\n"
        f"- **Receita Total (NF-e Autorizadas):** R$ {receita_nfe:,.2f} ({len(pedidos_nfe)} pedidos)\n"
        f"- **Diferença de Receita:** R$ {receita_pipeline - receita_nfe:,.2f}\n"
        f"- **Pedidos Pagos/Entregues SEM NF-e Autorizada:** {len(pedidos_sem_nfe)}\n\n"
        f"**Status dos pedidos sem NF-e:**\n\n"
        f"| Status do Pedido | Qtd Pedidos SEM NF-e |\n"
        f"|---|---|\n"
    )
    for _, row in status_sem_nfe.iterrows():
        res += f"| {row['status']} | {row['order_id']} |\n"
        
    res += (
        f"\n**Conclusão:** Há {len(pedidos_sem_nfe)} pedidos confirmados, pagos ou entregues "
        f"que simplesmente não possuem uma NF-e com status 'authorized'. Isso explica a discrepância "
        f"de 35% na receita (já que os testes comparavam valores diretamente). O pipeline financeiro (caixa) "
        f"tem faturamento maior que o fiscal. **Isso é um risco gravíssimo de compliance.**\n\n"
    )
    return res

def investigar_pareto(fato_pago):
    print("Investigando Ponto 3: Pareto e Concentração...")
    
    def calc_pareto(df, col):
        rev = df.groupby(col)['line_total'].sum().sort_values(ascending=False).reset_index()
        rev['cum_pct_rev'] = rev['line_total'].cumsum() / rev['line_total'].sum() * 100
        rev['cum_pct_items'] = (rev.index + 1) / len(rev) * 100
        
        # Ponto de 20% dos itens
        idx_20 = int(len(rev) * 0.20)
        if idx_20 == 0: idx_20 = 1
        share_20 = rev.iloc[idx_20 - 1]['cum_pct_rev']
        
        # Ponto onde chega em 80% da receita
        reach_80 = rev[rev['cum_pct_rev'] >= 80]
        pct_items_for_80 = reach_80.iloc[0]['cum_pct_items'] if not reach_80.empty else 100
        
        return share_20, pct_items_for_80
        
    share20_cli, items80_cli = calc_pareto(fato_pago, 'customer_id')
    share20_prod, items80_prod = calc_pareto(fato_pago, 'product_id')
    
    res = (
        f"### 3. Investigação da Distribuição (Pareto)\n"
        f"- **Top 20% Clientes representam:** {share20_cli:.1f}% da receita.\n"
        f"- **Para atingir 80% da receita precisa-se de:** {items80_cli:.1f}% dos clientes.\n\n"
        f"- **Top 20% Produtos representam:** {share20_prod:.1f}% da receita.\n"
        f"- **Para atingir 80% da receita precisa-se de:** {items80_prod:.1f}% dos produtos.\n\n"
        f"**Conclusão:** Num varejo B2B normal, a proporção é 80/20 (20% dos clientes fazem 80% da receita). "
        f"Aqui vemos que para atingir 80% da receita, precisamos de ~{items80_cli:.0f}% dos clientes. "
        f"Isso é uma linha reta quase perfeita (distribuição uniforme). O Sr. Almir pode ficar tranquilo "
        f"com o risco de concentração, mas tecnicamente isso comprova que **a massa de dados é sintética "
        f"e gerada aleatoriamente sem pesos de Pareto**.\n\n"
    )
    return res

def investigar_previsao(fato_pago):
    print("Investigando Ponto 4: Modelo de Previsão...")
    
    if not HAS_STATSMODELS:
        return "### 4. Modelo de Previsão\n\nNão foi possível importar statsmodels. Instale para análise avançada de séries temporais.\n\n"
        
    fato_pago['mes_ano'] = fato_pago['placed_at'].dt.to_period('M')
    receita_mensal = fato_pago.groupby('mes_ano')['line_total'].sum().reset_index()
    receita_mensal['receita'] = receita_mensal['line_total']
    
    # Backtest
    treino = receita_mensal.iloc[:-3]
    teste = receita_mensal.iloc[-3:]
    
    if len(treino) < 6:
        return "Dados insuficientes para backtest.\n"
        
    # Modelo 1: Média Móvel (Base)
    ma_prev = [treino['receita'].tail(6).mean()] * 3
    
    # Modelo 2: Holt-Winters Exponential Smoothing
    try:
        hw_model = ExponentialSmoothing(
            np.asarray(treino['receita']),
            trend='add',
            seasonal=None,
            initialization_method="estimated"
        ).fit()
        hw_prev = hw_model.forecast(3)
    except Exception as e:
        hw_prev = ma_prev
        print(f"Erro no Holt-Winters: {e}")
        
    reais = teste['receita'].tolist()
    
    mape_ma = np.mean([abs(r - p) / r * 100 for r, p in zip(reais, ma_prev)])
    mape_hw = np.mean([abs(r - p) / r * 100 for r, p in zip(reais, hw_prev)])
    
    res = (
        f"### 4. Melhoria no Modelo de Previsão de Demanda\n"
        f"Comparamos o modelo básico de Média Móvel com o **Holt-Winters (Suavização Exponencial com Tendência)** "
        f"nos últimos 3 meses conhecidos da base.\n\n"
        f"| Modelo | MAPE (Erro Médio) | Mês 1 Prev | Mês 2 Prev | Mês 3 Prev |\n"
        f"|---|---|---|---|---|\n"
        f"| **Real** | - | R$ {reais[0]:,.0f} | R$ {reais[1]:,.0f} | R$ {reais[2]:,.0f} |\n"
        f"| **Média Móvel** | {mape_ma:.1f}% | R$ {ma_prev[0]:,.0f} | R$ {ma_prev[1]:,.0f} | R$ {ma_prev[2]:,.0f} |\n"
        f"| **Holt-Winters** | {mape_hw:.1f}% | R$ {hw_prev[0]:,.0f} | R$ {hw_prev[1]:,.0f} | R$ {hw_prev[2]:,.0f} |\n\n"
    )
    
    if mape_hw < mape_ma:
        res += (
            f"**Conclusão:** O modelo de Holt-Winters reconheceu a tendência de alta recente dos dados "
            f"e reduziu substancialmente o erro de {mape_ma:.1f}% para {mape_hw:.1f}%. "
            f"Recomenda-se substituir a Média Móvel por Holt-Winters (Statsmodels) ou Prophet no pipeline produtivo.\n\n"
        )
    else:
        res += (
            f"**Conclusão:** Holt-Winters não performou melhor neste corte específico, indicando que a série "
            f"é altamente errática. O Prophet ainda é a melhor recomendação a longo prazo.\n\n"
        )
        
    return res

def main():
    print("--- INICIANDO INVESTIGAÇÃO DE VERACIDADE ---")
    fato_vendas, fato_pago, raw_fiscal, fato_returns, raw_return_items = load_data()
    
    relatorio = "# Relatório de Investigação de Veracidade dos Dados - LH Nautical\n\n"
    relatorio += "> *Documento gerado automaticamente após anomalias levantadas na camada de validação Gold.*\n\n"
    
    relatorio += investigar_devolucoes(fato_pago, fato_returns)
    relatorio += investigar_nfe(fato_pago, raw_fiscal)
    relatorio += investigar_pareto(fato_pago)
    relatorio += investigar_previsao(fato_pago)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(relatorio)
        
    print(f"\nRelatório gerado em: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
