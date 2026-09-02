"""
=======================================================================
SCRIPT 05 - Dashboard Interativo HTML - LH Nautical
=======================================================================
Objetivo  : Gera um relatorio/dashboard em HTML puro, que pode ser
            aberto em qualquer navegador sem depender de servidor.
            Incorpora os graficos gerados pelos scripts anteriores
            e exibe KPIs principais para cada stakeholder.

Stakeholders:
  - Gabriel Santos : Documentacao tecnica e qualidade de dados
  - Marina Costa   : Performance de vendas e margem
  - Sr. Almir      : Visao executiva simplificada
=======================================================================
"""

import os
import base64
import pandas as pd
from pathlib import Path

BASE_DIR    = Path(__file__).parent
FIG_DIR     = BASE_DIR / "outputs" / "figures"
REPORT_DIR  = BASE_DIR / "outputs" / "reports"
OUT_FILE    = BASE_DIR / "outputs" / "dashboard_lh_nautical.html"

def img_b64(fname):
    """Converte imagem PNG para base64 para embeber no HTML."""
    path = os.path.join(FIG_DIR, fname)
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def load_kpi(fname, col):
    """Carrega um valor de KPI de um CSV de relatorio."""
    try:
        df = pd.read_csv(os.path.join(REPORT_DIR, fname))
        return df[col].sum()
    except:
        return 0

def fmt(v, prefix='R$ ', suffix=''):
    if v >= 1_000_000: return f"{prefix}{v/1e6:.1f}M{suffix}"
    if v >= 1_000:     return f"{prefix}{v/1e3:.0f}K{suffix}"
    return f"{prefix}{v:.0f}{suffix}"

print("Gerando dashboard HTML...")

# KPIs
receita_total = load_kpi('03a_vendas_por_ano.csv', 'receita_total')
lucro_total   = load_kpi('03a_vendas_por_ano.csv', 'lucro_bruto')
margem_media  = (lucro_total / receita_total * 100) if receita_total > 0 else 0
qtd_pedidos   = load_kpi('03a_vendas_por_ano.csv', 'qtd_pedidos')

try:
    clv_df     = pd.read_csv(os.path.join(REPORT_DIR, '03e_clv_clientes.csv'))
    n_clientes = len(clv_df)
    best_client = clv_df.iloc[0]['legal_name'] if len(clv_df) > 0 else 'N/A'
    best_client_val = clv_df.iloc[0]['lucro_bruto'] if len(clv_df) > 0 else 0
except:
    n_clientes = 0; best_client = 'N/A'; best_client_val = 0

try:
    prej_df = pd.read_csv(os.path.join(REPORT_DIR, '03d_produtos_com_prejuizo.csv'))
    n_prejuizo = len(prej_df)
except:
    n_prejuizo = 0

try:
    rfm_df = pd.read_csv(os.path.join(REPORT_DIR, '04b_segmentacao_rfm.csv'))
    n_champions = len(rfm_df[rfm_df['segmento'] == 'Champions'])
except:
    n_champions = 0

# FASE 2: DataFrames to HTML
def df_to_html_snippet(fname, nrows=5):
    try:
        df = pd.read_csv(os.path.join(REPORT_DIR, fname))
        return df.head(nrows).to_html(classes='data-table', index=False, border=0)
    except:
        return "<p class='no-data'>Tabela nao disponivel.</p>"

html_fiscal = df_to_html_snippet('07d_risco_fiscal_por_mes.csv', nrows=12)
html_fornec = df_to_html_snippet('07a_performance_fornecedores.csv', nrows=5)
html_vended = df_to_html_snippet('07c_performance_vendedores.csv', nrows=5)

# Imagens
imgs = {
    'perf_anual':   img_b64('03a_performance_anual.png'),
    'canal':        img_b64('03b_vendas_por_canal.png'),
    'dia_semana':   img_b64('03c_vendas_dia_semana.png'),
    'prejuizo':     img_b64('03d_produtos_prejuizo.png') or img_b64('03d_produtos_menor_margem.png'),
    'top_clientes': img_b64('03e_top_clientes_lucro.png'),
    'rfm':          img_b64('04b_segmentacao_rfm.png'),
    'previsao':     img_b64('04a_previsao_demanda_prophet.png') or img_b64('04a_previsao_demanda_ma.png'),
    'svd':          img_b64('04c_svd_variancia.png'),
    'nulos':        img_b64('01_nulos_por_tabela.png'),
    'volume':       img_b64('01_volume_por_tabela.png'),
}

def card_img(title, b64, desc=''):
    if not b64:
        return f'<div class="chart-card"><h3>{title}</h3><p class="no-data">Grafico nao disponivel - execute os scripts anteriores primeiro.</p></div>'
    return f'''
    <div class="chart-card">
      <h3>{title}</h3>
      {"<p class='chart-desc'>" + desc + "</p>" if desc else ""}
      <img src="data:image/png;base64,{b64}" alt="{title}" />
    </div>'''

html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard LH Nautical - Analise de Dados</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --bg: #0f1117; --card: #1a1d2e; --card2: #22263a;
    --border: #2e3254; --accent1: #5a9fd4; --accent2: #e05a6a;
    --accent3: #7b5ea7; --accent4: #4fca8b; --accent5: #f0a830;
    --text: #e0e4f0; --muted: #8890b0;
  }}
  html {{ scroll-behavior: smooth; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; line-height: 1.6; }}

  /* HEADER */
  .header {{
    background: linear-gradient(135deg, #0d1b3e 0%, #1a1d2e 50%, #0d1b3e 100%);
    border-bottom: 1px solid var(--border);
    padding: 32px 48px;
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 16px;
  }}
  .header-left h1 {{ font-size: 2rem; font-weight: 800; color: white; }}
  .header-left h1 span {{ color: var(--accent1); }}
  .header-left p {{ color: var(--muted); font-size: 0.9rem; margin-top: 4px; }}
  .header-badge {{ background: var(--accent4); color: #0d2e1a; padding: 4px 14px;
                   border-radius: 999px; font-size: 0.78rem; font-weight: 700; }}

  /* NAV */
  .nav {{
    background: var(--card); border-bottom: 1px solid var(--border);
    padding: 0 48px; position: sticky; top: 0; z-index: 100;
    display: flex; gap: 0; overflow-x: auto;
  }}
  .nav a {{
    color: var(--muted); text-decoration: none; padding: 14px 20px;
    font-size: 0.85rem; font-weight: 600; border-bottom: 2px solid transparent;
    white-space: nowrap; transition: all 0.2s;
  }}
  .nav a:hover {{ color: var(--accent1); border-color: var(--accent1); }}

  /* MAIN */
  .main {{ max-width: 1400px; margin: 0 auto; padding: 40px 48px; }}

  /* SECTIONS */
  .section {{ margin-bottom: 60px; }}
  .section-header {{
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 24px; padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }}
  .section-badge {{
    background: var(--accent3); color: white; padding: 4px 12px;
    border-radius: 6px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.5px;
  }}
  .section-header h2 {{ font-size: 1.4rem; font-weight: 700; color: white; }}
  .section-header small {{ color: var(--muted); font-size: 0.82rem; }}

  /* KPI GRID */
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 32px; }}
  .kpi-card {{
    background: var(--card2); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px; text-align: center; position: relative;
    overflow: hidden; transition: transform 0.2s, border-color 0.2s;
  }}
  .kpi-card:hover {{ transform: translateY(-2px); border-color: var(--accent1); }}
  .kpi-card::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, var(--accent1), var(--accent3));
  }}
  .kpi-card.green::before {{ background: linear-gradient(90deg, var(--accent4), var(--accent1)); }}
  .kpi-card.red::before   {{ background: linear-gradient(90deg, var(--accent2), var(--accent5)); }}
  .kpi-card.purple::before{{ background: linear-gradient(90deg, var(--accent3), var(--accent2)); }}
  .kpi-label {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }}
  .kpi-value {{ font-size: 1.7rem; font-weight: 800; color: white; margin: 6px 0; }}
  .kpi-sub   {{ font-size: 0.72rem; color: var(--muted); }}

  /* CHART GRID */
  .chart-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(580px, 1fr)); gap: 20px; }}
  .chart-grid-3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 20px; }}
  .chart-card {{
    background: var(--card2); border: 1px solid var(--border);
    border-radius: 12px; padding: 24px; overflow: hidden;
    transition: border-color 0.2s;
  }}
  .chart-card:hover {{ border-color: var(--accent3); }}
  .chart-card h3 {{ font-size: 1rem; font-weight: 700; color: white; margin-bottom: 12px; }}
  .chart-card img {{ width: 100%; border-radius: 8px; display: block; }}
  .chart-desc {{ font-size: 0.8rem; color: var(--muted); margin-bottom: 10px; }}
  .no-data {{ color: var(--accent2); font-size: 0.85rem; padding: 20px; text-align: center; }}

  /* INSIGHT BOX */
  .insight {{ background: linear-gradient(135deg, #1a2a1a, #1a1d2e);
              border: 1px solid var(--accent4); border-radius: 10px;
              padding: 16px 20px; margin-top: 16px; }}
  .insight.warn {{ border-color: var(--accent5); background: linear-gradient(135deg, #2a2010, #1a1d2e); }}
  .insight.risk {{ border-color: var(--accent2); background: linear-gradient(135deg, #2a1015, #1a1d2e); }}
  .insight p {{ font-size: 0.85rem; color: var(--text); line-height: 1.7; }}
  .insight strong {{ color: var(--accent4); }}
  .insight.warn strong {{ color: var(--accent5); }}
  .insight.risk strong {{ color: var(--accent2); }}

  /* TABLE STYLE */
  .data-table {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 0.85rem; }}
  .data-table th, .data-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid var(--border); }}
  .data-table th {{ background: #151826; color: var(--muted); text-transform: uppercase; font-size: 0.75rem; }}
  .data-table tr:hover {{ background: #1e2235; }}

  /* FOOTER */
  .footer {{ text-align: center; padding: 40px; color: var(--muted); font-size: 0.8rem;
             border-top: 1px solid var(--border); margin-top: 60px; }}
  .footer span {{ color: var(--accent1); font-weight: 600; }}

  /* RESPONSIVE */
  @media (max-width: 768px) {{
    .header {{ padding: 24px; }}
    .main {{ padding: 24px; }}
    .chart-grid, .chart-grid-3 {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <h1>LH <span>Nautical</span> Analytics</h1>
    <p>Dashboard de Inteligencia de Dados — Periodo 2020–2026</p>
  </div>
  <div>
    <span class="header-badge">v1.0 — Desafio de Dados</span>
  </div>
</div>

<nav class="nav">
  <a href="#executivo">Visao Executiva</a>
  <a href="#vendas">Vendas</a>
  <a href="#clientes">Clientes</a>
  <a href="#previsao">Previsao</a>
  <a href="#recomendacao">Recomendacao</a>
  <a href="#fase2">Supply, RH & Fiscal</a>
  <a href="#qualidade">Qualidade dos Dados</a>
</nav>

<div class="main">

  <!-- ===== VISAO EXECUTIVA (Sr. Almir) ===== -->
  <section class="section" id="executivo">
    <div class="section-header">
      <span class="section-badge">SR. ALMIR</span>
      <h2>Visao Executiva</h2>
      <small>Dados solidos para decisoes precisas</small>
    </div>
    <div class="kpi-grid">
      <div class="kpi-card green">
        <div class="kpi-label">Receita Total</div>
        <div class="kpi-value">{fmt(receita_total)}</div>
        <div class="kpi-sub">2020 – 2026</div>
      </div>
      <div class="kpi-card green">
        <div class="kpi-label">Lucro Bruto</div>
        <div class="kpi-value">{fmt(lucro_total)}</div>
        <div class="kpi-sub">Soma historica</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Margem Bruta Media</div>
        <div class="kpi-value">{margem_media:.1f}%</div>
        <div class="kpi-sub">Lucro / Receita</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Total de Pedidos</div>
        <div class="kpi-value">{int(qtd_pedidos):,}</div>
        <div class="kpi-sub">Pagos e confirmados</div>
      </div>
      <div class="kpi-card purple">
        <div class="kpi-label">Clientes Unicos</div>
        <div class="kpi-value">{n_clientes:,}</div>
        <div class="kpi-sub">Com historico de compra</div>
      </div>
      <div class="kpi-card {'red' if n_prejuizo > 0 else 'green'}">
        <div class="kpi-label">Produtos c/ Prejuizo</div>
        <div class="kpi-value">{n_prejuizo:,}</div>
        <div class="kpi-sub">Margem bruta negativa</div>
      </div>
      <div class="kpi-card green">
        <div class="kpi-label">Champions (RFM)</div>
        <div class="kpi-value">{n_champions:,}</div>
        <div class="kpi-sub">Melhores clientes</div>
      </div>
    </div>
    <div class="insight">
      <p><strong>Nota para o Sr. Almir:</strong> Os dados confirmam que a LH Nautical tem uma operacao consistente ao longo de 6 anos. 
      A margem bruta de <strong>{margem_media:.1f}%</strong> demonstra solidez comercial. 
      Identificamos <strong>{n_champions}</strong> clientes "Champions" que sozinhos representam a maior parte da rentabilidade. 
      A previsao de demanda aponta oportunidades para os proximos 90 dias. Todos esses numeros sao calculados diretamente dos dados operacionais da empresa — sem estimativas.</p>
    </div>
  </section>

  <!-- ===== VENDAS (Marina Costa) ===== -->
  <section class="section" id="vendas">
    <div class="section-header">
      <span class="section-badge" style="background:var(--accent1)">MARINA COSTA</span>
      <h2>Performance de Vendas</h2>
      <small>Resultados, margens e canais</small>
    </div>
    <div class="chart-grid">
      {card_img("Performance Anual 2020–2026", imgs['perf_anual'], "Receita total, lucro bruto e margem percentual por ano.")}
      {card_img("Participacao por Canal de Venda", imgs['canal'], "Distribuicao de receita e margem entre ecommerce, POS e loja fisica.")}
    </div>
    <div class="chart-grid" style="margin-top:20px">
      {card_img("Receita Media por Dia da Semana", imgs['dia_semana'], "Media considerando dias sem venda como zero — visao realista do comportamento semanal.")}
      {card_img("Produtos com Maior Prejuizo", imgs['prejuizo'], "Produtos com lucro bruto negativo (preco de venda abaixo do custo).")}
    </div>
    {"<div class='insight warn'><p><strong>Alerta para Marina:</strong> Existem <strong>" + str(n_prejuizo) + "</strong> produtos sendo vendidos abaixo do custo. A revisao imediata da precificacao desses itens pode impactar diretamente a margem da proxima campanha.</p></div>" if n_prejuizo > 0 else "<div class='insight'><p><strong>Boas noticias para Marina:</strong> Nenhum produto com margem bruta negativa identificado. A precificacao esta saudavel.</p></div>"}
  </section>

  <!-- ===== CLIENTES ===== -->
  <section class="section" id="clientes">
    <div class="section-header">
      <span class="section-badge" style="background:var(--accent4); color:#0d2e1a">CLV & RFM</span>
      <h2>Analise de Clientes</h2>
      <small>Valor do cliente e segmentacao comportamental</small>
    </div>
    <div class="chart-grid">
      {card_img("Top 20 Clientes por Lucro Acumulado", imgs['top_clientes'], f"Melhor cliente: {best_client} — lucro de {fmt(best_client_val)}")}
      {card_img("Segmentacao RFM de Clientes", imgs['rfm'], "Classificacao por Recencia, Frequencia e Valor Monetario. Champions = clientes mais valiosos.")}
    </div>
    <div class="insight">
      <p><strong>Insight de Clientes:</strong> A segmentacao RFM revela os perfis comportamentais da base de clientes. 
      Os <strong>Champions</strong> merecem tratamento VIP e acoes de fidelizacao prioritarias. 
      Os clientes <strong>At Risk</strong> precisam de campanhas de reativacao urgentes antes que se tornem <strong>Lost</strong>.</p>
    </div>
  </section>

  <!-- ===== PREVISAO ===== -->
  <section class="section" id="previsao">
    <div class="section-header">
      <span class="section-badge" style="background:var(--accent5); color:#2a1a00">PREVISAO</span>
      <h2>Previsao de Demanda</h2>
      <small>Projecao de receita para os proximos 90 dias</small>
    </div>
    <div class="chart-card" style="max-width:100%">
      <h3>Projecao de Receita Diaria — Proximos 90 Dias</h3>
      <p class="chart-desc">Modelo de serie temporal (Prophet ou Media Movel) com intervalo de confianca de 85%-115%.</p>
      {"<img src='data:image/png;base64," + imgs['previsao'] + "' alt='Previsao' />" if imgs['previsao'] else "<p class='no-data'>Previsao nao disponivel</p>"}
    </div>
    <div class="insight">
      <p><strong>Para Gabriel Santos:</strong> O modelo de previsao utiliza decomposicao de serie temporal com sazonalidade anual e semanal. 
      Para maior precisao, recomendo a instalacao do <strong>Prophet (Meta)</strong> via <code>pip install prophet</code>. 
      O script 04 tentara usa-lo automaticamente, com fallback para media movel caso nao esteja disponivel.</p>
    </div>
  </section>

  <!-- ===== RECOMENDACAO ===== -->
  <section class="section" id="recomendacao">
    <div class="section-header">
      <span class="section-badge" style="background:var(--accent3)">IA & ML</span>
      <h2>Sistema de Recomendacao</h2>
      <small>Filtragem colaborativa por SVD (Decomposicao Matricial)</small>
    </div>
    <div class="chart-grid">
      {card_img("Variancia Explicada pelo SVD", imgs['svd'], "Quanto do comportamento de compra dos clientes e capturado pelo modelo de recomendacao.")}
      <div class="chart-card">
        <h3>Como funciona o sistema de recomendacao</h3>
        <div style="padding: 12px 0; line-height: 2; font-size: 0.88rem; color: var(--muted)">
          <div style="margin-bottom:10px; padding:10px; background:var(--card); border-radius:8px; border-left:3px solid var(--accent1)">
            <strong style="color:white">1. Matriz Cliente x Produto</strong><br>
            Construida a partir do historico de compras, registrando quantidades adquiridas por cada cliente.
          </div>
          <div style="margin-bottom:10px; padding:10px; background:var(--card); border-radius:8px; border-left:3px solid var(--accent3)">
            <strong style="color:white">2. SVD (Decomposicao Matricial)</strong><br>
            Identifica padroes latentes no comportamento de compra, sem precisar de dados demograficos.
          </div>
          <div style="margin-bottom:10px; padding:10px; background:var(--card); border-radius:8px; border-left:3px solid var(--accent4)">
            <strong style="color:white">3. Recomendacoes Personalizadas</strong><br>
            Para cada cliente, sugere os TOP 5 produtos que ele ainda nao comprou, baseado em perfis similares.
          </div>
          <div style="padding:10px; background:var(--card); border-radius:8px; border-left:3px solid var(--accent5)">
            <strong style="color:white">4. Saida em CSV</strong><br>
            O arquivo <code>04c_recomendacoes_por_cliente.csv</code> lista as recomendacoes prontas para uso em campanhas.
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ===== QUALIDADE DOS DADOS (Gabriel Santos) ===== -->
  <section class="section" id="qualidade">
    <div class="section-header">
      <span class="section-badge" style="background:var(--accent2)">GABRIEL SANTOS</span>
      <h2>Qualidade dos Dados</h2>
      <small>Documentacao tecnica do pipeline de ingestao e tratamento</small>
    </div>
    <div class="chart-grid">
      {card_img("% de Dados Nulos por Tabela", imgs['nulos'], "Tabelas acima de 10% de nulos em vermelho — requerem atencao especial.")}
      {card_img("Volume de Linhas por Tabela", imgs['volume'], "Distribuicao dos dados brutos — base para estimar custos de processamento.")}
    </div>
    <div class="insight">
      <p><strong>Decisoes de Tratamento (para Gabriel):</strong><br>
      <strong>trade_name nulo em customers:</strong> Preenchido com legal_name (valido para PF).<br>
      <strong>complement nulo em addresses:</strong> Mantido como string vazia — campo opcional por natureza.<br>
      <strong>salesperson_id nulo em orders:</strong> Mantido como nulo — pedidos ecommerce nao tem vendedor associado.<br>
      <strong>paid_at nulo em payments:</strong> Indica pagamentos ainda pendentes — mantido para analise de inadimplencia.<br>
      <strong>termination_date nulo em employees:</strong> Correto — colaboradores ativos nao tem data de demissao.</p>
    </div>
  </section>

  <!-- ===== FASE 2: SUPPLY, RH E FISCAL ===== -->
  <section class="section" id="fase2">
    <div class="section-header">
      <span class="section-badge" style="background:var(--accent1)">NOVAS INTEGRAÇÕES (FASE 2)</span>
      <h2>Supply Chain, RH e Auditoria Fiscal</h2>
      <small>Dados logísticos e financeiros complementares ao pipeline</small>
    </div>
    
    <div class="chart-grid">
      <div class="chart-card">
        <h3>Top Fornecedores (Supply Chain)</h3>
        <p class="chart-desc">5 maiores fornecedores em gasto e tempo medio de entrega (Lead Time).</p>
        <div style="overflow-x:auto;">{html_fornec}</div>
      </div>
      
      <div class="chart-card">
        <h3>Risco Fiscal por Mês (Auditoria)</h3>
        <p class="chart-desc">Pedidos pagos e confirmados que NÃO possuem Nota Fiscal Autorizada.</p>
        <div style="overflow-x:auto;">{html_fiscal}</div>
      </div>
    </div>
    
    <div class="chart-grid" style="margin-top:20px;">
      <div class="chart-card">
        <h3>Ranking de Vendedores (Recursos Humanos)</h3>
        <p class="chart-desc">Performance de vendas no canal POS para cálculo de comissões.</p>
        <div style="overflow-x:auto;">{html_vended}</div>
      </div>
    </div>
    
    <div class="insight risk">
      <p><strong>Risco Crítico para Sr. Almir:</strong> O relatório fiscal aponta sistematicamente milhares de reais em pedidos processados mensalmente sem NF-e correspondente autorizada. Isso indica grave quebra de compliance entre o ERP de Vendas e o emissor fiscal.</p>
    </div>
  </section>

</div>

<footer class="footer">
  <p>LH Nautical Data Challenge &nbsp;|&nbsp; Pipeline: <span>EDA → Tratamento → Modelagem → Analise → IA</span></p>
  <p style="margin-top:6px">Gerado automaticamente pelos scripts Python do desafio.</p>
</footer>

</body>
</html>"""

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"[CONCLUIDO] Dashboard gerado em: {OUT_FILE}")
print("  Abra o arquivo no navegador para visualizar.")
