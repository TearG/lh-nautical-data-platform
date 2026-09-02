# =============================================================================
# tests/test_07_previsao_e_concentracao.py
#
# GAPS COBERTOS: GAP 5 (Previsão) + GAP 6 (Concentração de Risco)
#
# STAKEHOLDER: Marina Costa — "Se a previsão for negativa algo está errado."
#              Sr. Almir — "Não quero depender de um único cliente para sobreviver."
#              Gabriel Santos — "Previsão sem validação não é previsão, é chute."
# =============================================================================

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / "outputs" / "reports"
SILVER_DIR  = BASE_DIR / "processed"


# =============================================================================
# GAP 5 — Validação do Output da Previsão de Demanda
# =============================================================================

class TestPrevisaoDemanda:
    """
    Valida que o arquivo de previsão gerado pelo script 04 é correto.
    POR QUÊ: Uma previsão com valores negativos ou datas no passado seria
    apresentada ao Sr. Almir como dado real — destruindo credibilidade do time.
    """

    @pytest.fixture(scope="class")
    def forecast_df(self):
        """Carrega o CSV de previsão de demanda gerado pelo script 04."""
        path = REPORTS_DIR / "04a_previsao_demanda_90d.csv"
        if not path.exists():
            pytest.skip("Arquivo de previsão não existe — execute o script 04 primeiro.")
        return pd.read_csv(path, parse_dates=['data'])

    def test_previsao_arquivo_existe(self):
        """Valida que o arquivo de previsão foi gerado."""
        path = REPORTS_DIR / "04a_previsao_demanda_90d.csv"
        assert path.exists(), (
            "04a_previsao_demanda_90d.csv não foi gerado.\n"
            "Execute python scripts/04_previsao_recomendacao.py"
        )

    def test_previsao_tem_90_dias(self, forecast_df):
        """
        O arquivo deve ter exatamente 90 linhas (uma por dia projetado).
        POR QUÊ: Previsão com menos dias indica que o modelo foi truncado
        ou que havia dados faltando no período de treinamento.
        """
        assert len(forecast_df) == 90, (
            f"Previsão tem {len(forecast_df)} linhas, esperado 90 dias."
        )

    def test_previsao_valores_positivos(self, forecast_df):
        """
        previsao_receita não pode ser negativa.
        POR QUÊ: Receita projetada negativa é matematicamente absurda —
        indica que o modelo superajustou tendência de queda ou tem bug.
        """
        negativos = forecast_df[forecast_df['previsao_receita'] < 0]
        assert len(negativos) == 0, (
            f"{len(negativos)} dias com previsão de receita NEGATIVA.\n"
            f"Min: R$ {forecast_df['previsao_receita'].min():,.2f}\n"
            f"Verifique a tendência do modelo — possível overfitting de queda."
        )

    def test_previsao_datas_sao_futuras(self, forecast_df):
        """
        As datas da previsão devem ser posteriores ao último dado histórico.
        POR QUÊ: Previsão para datas que já temos dados reais não é previsão
        — é recálculo de histórico, o que invalida a métrica de acurácia.
        """
        fato_path = SILVER_DIR / "fato_vendas.csv"
        if not fato_path.exists():
            pytest.skip("fato_vendas.csv não existe para comparação.")

        fato = pd.read_csv(fato_path, parse_dates=['order_date'])
        ultima_data_historica = fato['order_date'].max()

        min_data_previsao = forecast_df['data'].min()

        assert min_data_previsao > ultima_data_historica, (
            f"A previsão começa em {min_data_previsao.date()}, mas o histórico vai até "
            f"{ultima_data_historica.date()}.\n"
            f"As primeiras {(ultima_data_historica - min_data_previsao).days} linhas "
            f"cobrem período que já temos dados reais."
        )

    def test_previsao_intervalo_de_confianca_coerente(self, forecast_df):
        """
        intervalo_inf <= previsao_receita <= intervalo_sup para toda linha.
        POR QUÊ: Intervalo de confiança invertido (inf > sup) é um bug de
        cálculo que tornaria o gráfico no dashboard visualmente errado.
        """
        invalido_inf = forecast_df[forecast_df['intervalo_inf'] > forecast_df['previsao_receita'] + 0.01]
        invalido_sup = forecast_df[forecast_df['intervalo_sup'] < forecast_df['previsao_receita'] - 0.01]

        assert len(invalido_inf) == 0, (
            f"{len(invalido_inf)} linhas onde intervalo_inf > previsao_receita (intervalo invertido)"
        )
        assert len(invalido_sup) == 0, (
            f"{len(invalido_sup)} linhas onde intervalo_sup < previsao_receita (intervalo invertido)"
        )

    def test_previsao_sem_datas_duplicadas(self, forecast_df):
        """Não pode haver dois registros para a mesma data de previsão."""
        dups = forecast_df['data'].duplicated().sum()
        assert dups == 0, f"{dups} datas duplicadas no arquivo de previsão"


# =============================================================================
# GAP 6 — Análise de Concentração de Risco
# =============================================================================

class TestConcentracaoRisco:
    """
    Analisa se a receita está concentrada demais em poucos clientes/produtos.
    POR QUÊ: Alta concentração é risco de negócio — perder um único cliente
    pode comprometer a viabilidade da empresa. O Sr. Almir PRECISA saber disso.

    Limites usados (referência de mercado para varejo):
      - Cliente único: < 20% da receita total
      - Produto único: < 15% da receita total
      - Canal único: < 80% da receita total (diversificação mínima)
    """

    LIMITE_CLIENTE  = 0.20  # 20%
    LIMITE_PRODUTO  = 0.15  # 15%
    LIMITE_CANAL    = 0.80  # 80%

    @pytest.fixture(scope="class")
    def fato_pago(self):
        path = SILVER_DIR / "fato_vendas.csv"
        if not path.exists():
            pytest.skip("fato_vendas.csv não existe.")
        df = pd.read_csv(path, parse_dates=['placed_at'])
        return df[df['status'].isin(['paid', 'confirmed', 'delivered'])]

    def test_nenhum_cliente_domina_mais_de_20pct_receita(self, fato_pago):
        """
        Nenhum cliente único deve responder por mais de 20% da receita total.
        Resultado é um AVISO documentado, não falha de pipeline — é decisão
        estratégica do Sr. Almir e da Marina responder a isso.
        """
        receita_total = fato_pago['line_total'].sum()
        por_cliente   = fato_pago.groupby('customer_id')['line_total'].sum()
        share_max     = (por_cliente.max() / receita_total)
        top_cliente   = por_cliente.idxmax()

        if share_max > self.LIMITE_CLIENTE:
            print(
                f"\n[ALERTA CONCENTRAÇÃO] Cliente ID {top_cliente} representa "
                f"{share_max*100:.1f}% da receita total "
                f"(limite recomendado: {self.LIMITE_CLIENTE*100:.0f}%).\n"
                f"Risco: Perder esse cliente impacta severamente o faturamento."
            )
        # Teste soft — registra o risco mas não bloqueia o pipeline
        assert share_max <= 0.40, (
            f"CONCENTRAÇÃO CRÍTICA: Um único cliente tem {share_max*100:.1f}% da receita. "
            f"Isso representa dependência extrema — risco existencial para o negócio."
        )

    def test_nenhum_produto_domina_mais_de_15pct_receita(self, fato_pago):
        """
        Nenhum produto único deve responder por mais de 15% da receita.
        POR QUÊ: Produto com ruptura de estoque paralisaria 15%+ da operação.
        """
        receita_total = fato_pago['line_total'].sum()
        por_produto   = fato_pago.groupby('product_id')['line_total'].sum()
        share_max     = (por_produto.max() / receita_total)
        top_produto   = por_produto.idxmax()

        if share_max > self.LIMITE_PRODUTO:
            print(
                f"\n[ALERTA CONCENTRAÇÃO PRODUTO] Produto ID {top_produto} "
                f"representa {share_max*100:.1f}% da receita "
                f"(limite: {self.LIMITE_PRODUTO*100:.0f}%).\n"
                f"Ação: Priorizar reposição de estoque e diversificar catálogo."
            )
        assert share_max <= 0.35, (
            f"CONCENTRAÇÃO PRODUTO CRÍTICA: Produto {top_produto} tem "
            f"{share_max*100:.1f}% da receita — ruptura seria catastrófica."
        )

    def test_distribuicao_por_canal_nao_monopolio(self, fato_pago):
        """
        Nenhum canal único deve responder por 100% das vendas.
        POR QUÊ: Canal único = ausência de diversificação. Se o e-commerce
        cair, a empresa fica sem vender — o Sr. Almir precisa saber disso.
        """
        receita_total = fato_pago['line_total'].sum()
        por_canal     = fato_pago.groupby('channel')['line_total'].sum()
        share_max     = (por_canal.max() / receita_total)
        top_canal     = por_canal.idxmax()

        if share_max > self.LIMITE_CANAL:
            print(
                f"\n[ALERTA CANAL] Canal '{top_canal}' representa "
                f"{share_max*100:.1f}% da receita "
                f"(limite recomendado: {self.LIMITE_CANAL*100:.0f}%).\n"
                f"Ação: Desenvolver canais alternativos para reduzir dependência."
            )
        assert share_max < 1.0, (
            f"100% da receita em um único canal ('{top_canal}'). "
            f"Ausência total de diversificação de canais."
        )

    def test_top10_clientes_share_documentado(self, fato_pago, report_clv):
        """
        Calcula e documenta o share dos top 10 clientes para o Sr. Almir.
        Não falha — apenas produz informação estratégica no output do pytest.
        POR QUÊ: Concentração nos top 10 é métrica padrão de risco em varejo B2B.
        """
        receita_total  = fato_pago['line_total'].sum()
        top10_receita  = report_clv.head(10)['receita_total'].sum()
        share_top10    = top10_receita / receita_total * 100

        print(
            f"\n[INFORMAÇÃO ESTRATÉGICA] Top 10 clientes representam "
            f"{share_top10:.1f}% da receita total.\n"
            f"Benchmark saudável para varejo B2B: < 40%.\n"
            f"Benchmark atual: {'OK' if share_top10 < 40 else 'ATENÇÃO'}"
        )
        assert True  # Informativo apenas
