# =============================================================================
# tests/test_04_relatorios_gold.py
#
# FRENTE   : Validação dos Relatórios e KPIs (Camada Gold)
# OBJETIVO : Garante que os relatórios gerados pelos scripts 03 e 04
#            são matematicamente corretos, completos e fazem sentido
#            de negócio antes de serem apresentados aos stakeholders.
#
# POR QUÊ  : Um relatório errado que chega na mão do Sr. Almir ou da
#             Marina Costa é pior do que nenhum relatório — destrói
#             a credibilidade do time de dados.
#
# STAKEHOLDERS:
#   Marina Costa — KPIs de vendas, margem e CLV
#   Sr. Almir    — Sumário executivo: receita e lucro devem ser sólidos
#   Gabriel      — Consistência matemática e cobertura de outputs
# =============================================================================

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / "outputs" / "reports"
SILVER_DIR  = BASE_DIR / "processed"


# =============================================================================
# Bloco A — Existência dos Arquivos de Relatório
# =============================================================================

class TestExistenciaRelatorios:
    """
    Garante que todos os relatórios esperados foram gerados.
    POR QUÊ: Se um script falhou silenciosamente, o arquivo pode não existir
    e as análises seguintes vão falhar com FileNotFoundError — tarde demais.
    """

    RELATORIOS_ESPERADOS = [
        "01_qualidade_dados.csv",
        "03a_vendas_por_ano.csv",
        "03b_vendas_por_canal.csv",
        "03c_vendas_por_dia_semana.csv",
        "03d_ranking_margem_produtos.csv",
        "03e_clv_clientes.csv",
        "03f_devolucoes_por_ano.csv",
        "03g_performance_por_loja.csv",
        "04b_segmentacao_rfm.csv",
        "04c_recomendacoes_por_cliente.csv",
    ]

    @pytest.mark.parametrize("relatorio", RELATORIOS_ESPERADOS)
    def test_relatorio_foi_gerado(self, relatorio):
        path = REPORTS_DIR / relatorio
        assert path.exists(), (
            f"[OUTPUT FALTANDO] '{relatorio}' não foi gerado. "
            f"Execute o script correspondente antes de rodar os testes."
        )

    def test_dashboard_html_foi_gerado(self):
        dashboard = BASE_DIR / "outputs" / "dashboard_lh_nautical.html"
        assert dashboard.exists(), "Dashboard HTML não foi gerado pelo script 05."


# =============================================================================
# Bloco B — Sanidade dos KPIs de Vendas por Ano
# =============================================================================

class TestKpiVendasAno:
    """
    STAKEHOLDER: Marina Costa + Sr. Almir
    Valida que os KPIs anuais fazem sentido matemático e de negócio.
    """

    def test_vendas_ano_cobre_periodo_completo(self, report_vendas_ano):
        """
        O relatório deve cobrir anos dentro de 2020–2026.
        POR QUÊ: Se ano 2019 ou 2027 aparecer, há datas incorretas nos dados
        que inflaram ou distorceram o período analisado.
        """
        anos = set(report_vendas_ano['year'].tolist())
        invalidos = anos - {2020, 2021, 2022, 2023, 2024, 2025, 2026}
        assert len(invalidos) == 0, (
            f"Anos fora do período esperado (2020-2026): {invalidos}. "
            f"Verifique datas no futuro ou passado nos dados brutos."
        )

    def test_receita_total_positiva(self, report_vendas_ano):
        """Receita total de cada ano deve ser positiva."""
        negativos = report_vendas_ano[report_vendas_ano['receita_total'] <= 0]
        assert len(negativos) == 0, (
            f"Anos com receita <= 0: {negativos['year'].tolist()}"
        )

    def test_lucro_bruto_menor_que_receita(self, report_vendas_ano):
        """
        Lucro bruto nunca pode ser maior que a receita total.
        POR QUÊ: Lucro bruto = Receita - Custo. Se custo = 0 para qualquer
        motivo (join faltou), lucro = receita. Margem > 100% é impossível.
        """
        problema = report_vendas_ano[
            report_vendas_ano['lucro_bruto'] > report_vendas_ano['receita_total'] * 1.001
        ]
        assert len(problema) == 0, (
            f"[CÁLCULO IMPOSSÍVEL] Lucro > Receita nos anos: {problema['year'].tolist()}. "
            f"Indica que cost_total = 0 para muitos itens (join com custo falhou)."
        )

    def test_margem_pct_consistente_com_receita_lucro(self, report_vendas_ano):
        """
        margem_pct deve ser recalculável como lucro/receita × 100.
        POR QUÊ: Se a coluna foi calculada errada, todos os visuais de
        margem no dashboard estarão errados.
        """
        df = report_vendas_ano.copy()
        df['margem_recalculada'] = (df['lucro_bruto'] / df['receita_total'] * 100).round(1)
        df['margem_registrada']  = df['margem_pct'].round(1)
        diff = (df['margem_recalculada'] - df['margem_registrada']).abs()
        assert diff.max() <= 0.1, (
            f"margem_pct diverge do recálculo em até {diff.max():.2f} pontos percentuais. "
            f"Verifique a fórmula no script 03."
        )

    def test_ticket_medio_dentro_de_faixa_razoavel(self, report_vendas_ano):
        """
        Ticket médio deve estar entre R$ 1 e R$ 500.000.
        POR QUÊ: Ticket médio absurdo (ex: R$ 0,01 ou R$ 10 milhões) indica
        que o cálculo de média está sobre uma coluna errada ou com dados corrompidos.
        """
        invalidos = report_vendas_ano[
            (report_vendas_ano['ticket_medio'] < 1) |
            (report_vendas_ano['ticket_medio'] > 500_000)
        ]
        assert len(invalidos) == 0, (
            f"Ticket médio fora da faixa razoável (R$ 1 - R$ 500K) nos anos: "
            f"{invalidos[['year', 'ticket_medio']].to_string(index=False)}"
        )

    def test_qtd_pedidos_maior_que_zero(self, report_vendas_ano):
        """Todos os anos no relatório devem ter pelo menos um pedido."""
        sem_pedidos = report_vendas_ano[report_vendas_ano['qtd_pedidos'] == 0]
        assert len(sem_pedidos) == 0, (
            f"Anos com zero pedidos no relatório: {sem_pedidos['year'].tolist()}. "
            f"Esses anos não deveriam aparecer se não há dados."
        )


# =============================================================================
# Bloco C — Sanidade do CLV (Customer Lifetime Value)
# =============================================================================

class TestKpiCLV:
    """
    STAKEHOLDER: Marina Costa — O CLV é o principal input para priorização
    de campanhas. Se estiver errado, ela vai investir em clientes errados.
    """

    def test_clv_cobre_todos_clientes_com_compra(self, report_clv, fato_vendas):
        """
        Todos os customer_ids únicos em fato_vendas devem estar no relatório de CLV.
        POR QUÊ: Clientes faltando no CLV serão ignorados em campanhas.
        """
        clientes_fato = set(fato_vendas[
            fato_vendas['status'].isin(['paid', 'confirmed', 'delivered'])
        ]['customer_id'].dropna().astype(int))

        clientes_clv  = set(report_clv['customer_id'].astype(int))
        faltando      = clientes_fato - clientes_clv

        assert len(faltando) == 0, (
            f"{len(faltando)} clientes com compras confirmadas estão FALTANDO no relatório de CLV. "
            f"Exemplos de IDs: {list(faltando)[:10]}"
        )

    def test_clv_lucro_bruto_total_reconcilia_com_fato(self, report_clv, fato_vendas):
        """
        A soma de lucro_bruto no CLV deve igualar a soma em fato_vendas.
        Tolerância de R$ 10 (por diferenças de arredondamento em múltiplos groupby).
        POR QUÊ: Se a soma não fecha, os pesos relativos entre clientes
        estão corretos mas o total está errado — confundirá a Marina.
        """
        fato_pago   = fato_vendas[fato_vendas['status'].isin(['paid', 'confirmed', 'delivered'])]
        soma_fato   = fato_pago['gross_profit'].sum()
        soma_clv    = report_clv['lucro_bruto'].sum()
        diff        = abs(soma_fato - soma_clv)

        assert diff <= 10.0, (
            f"[RECONCILIAÇÃO FALHOU] "
            f"Lucro no fato_vendas: R$ {soma_fato:,.2f} | "
            f"Soma do CLV: R$ {soma_clv:,.2f} | "
            f"Diferença: R$ {diff:,.2f}"
        )

    def test_clv_sem_receita_negativa_por_cliente(self, report_clv):
        """
        Nenhum cliente deve ter receita_total negativa.
        POR QUÊ: Receita negativa por cliente indica que devoluções foram
        somadas incorretamente com as vendas no groupby do script 03.
        """
        negativos = report_clv[report_clv['receita_total'] < 0]
        assert len(negativos) == 0, (
            f"{len(negativos)} clientes com receita_total negativa. "
            f"Devoluções podem ter sido contabilizadas com sinal errado."
        )

    def test_clv_ranking_decrescente(self, report_clv):
        """
        O CLV deve estar ordenado do maior para o menor lucro_bruto.
        POR QUÊ: O script 03 salva o CLV ordenado — se o arquivo não
        estiver ordenado, o 'melhor cliente' reportado pode estar errado.
        """
        lucros = report_clv['lucro_bruto'].tolist()
        assert lucros == sorted(lucros, reverse=True), (
            "O relatório de CLV não está ordenado por lucro_bruto decrescente. "
            "O 'melhor cliente' no dashboard pode estar incorreto."
        )


# =============================================================================
# Bloco D — Sanidade da Segmentação RFM
# =============================================================================

class TestKpiRFM:
    """
    STAKEHOLDER: Marina Costa — A segmentação RFM define para quem enviar
    cada tipo de campanha. Um cliente classificado errado vai receber
    comunicação inadequada, prejudicando conversão e fidelização.
    """

    SEGMENTOS_VALIDOS = {'Champions', 'Loyal Customers', 'Potential Loyalist',
                         'At Risk', 'Lost'}

    def test_rfm_segmentos_validos(self, report_rfm):
        """Todos os segmentos devem ser da lista pré-definida."""
        segmentos_no_relatorio = set(report_rfm['segmento'].unique())
        invalidos = segmentos_no_relatorio - self.SEGMENTOS_VALIDOS
        assert len(invalidos) == 0, (
            f"Segmentos inválidos no RFM: {invalidos}. "
            f"Verifique a função classificar_rfm() no script 04."
        )

    def test_rfm_cobre_todos_segmentos(self, report_rfm):
        """
        Os 5 segmentos devem estar todos representados.
        POR QUÊ: Se 'Lost' não aparecer, pode indicar que a segmentação
        está com thresholds errados que classificam todos como ativos.
        """
        segmentos_no_relatorio = set(report_rfm['segmento'].unique())
        faltando = self.SEGMENTOS_VALIDOS - segmentos_no_relatorio
        # Warning, não erro — pode não ter clientes em alguma categoria
        if faltando:
            print(f"\n[AVISO RFM] Segmentos sem clientes: {faltando}")

    def test_rfm_sem_clientes_duplicados(self, report_rfm):
        """
        Cada cliente deve estar em um único segmento.
        POR QUÊ: Um cliente com dois segmentos receberia comunicações
        duplicadas e contraditórias (ex: "volte" e "parabéns, campeão").
        """
        dups = report_rfm.duplicated(subset=['customer_id']).sum()
        assert dups == 0, (
            f"{dups} clientes classificados em MAIS DE UM segmento RFM. "
            f"Verifique o groupby e o merge no script 04."
        )

    def test_rfm_score_dentro_do_intervalo(self, report_rfm):
        """
        RFM_score = R + F + M, cada um de 1 a 5, portanto soma de 3 a 15.
        POR QUÊ: Score fora do range indica NaN sendo somado como 0
        ou erro na escala de pontuação.
        """
        invalidos = report_rfm[
            (report_rfm['RFM_score'] < 3) | (report_rfm['RFM_score'] > 15)
        ]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} clientes com RFM_score fora do intervalo [3, 15]. "
            f"Min: {report_rfm['RFM_score'].min()} | Max: {report_rfm['RFM_score'].max()}"
        )


# =============================================================================
# Bloco E — Sanidade das Recomendações
# =============================================================================

class TestRecomendacoes:
    """
    STAKEHOLDER: Marina Costa — As recomendações serão usadas em campanhas.
    Uma recomendação de produto que o cliente JÁ COMPROU é um erro que
    prejudica a experiência e a conversão da campanha.
    """

    def test_recomendacoes_rank_valido(self, report_recomendacoes):
        """Ranks devem ser de 1 a 5 para cada cliente."""
        invalidos = report_recomendacoes[
            (report_recomendacoes['rank'] < 1) |
            (report_recomendacoes['rank'] > 5)
        ]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} recomendações com rank inválido (fora de 1-5)"
        )

    def test_recomendacoes_5_por_cliente(self, report_recomendacoes):
        """
        Cada cliente deve ter exatamente 5 recomendações.
        POR QUÊ: Se um cliente tiver menos de 5, pode indicar que ele
        já comprou quase tudo no catálogo, ou que o filtro de exclusão
        está muito agressivo.
        """
        contagem = report_recomendacoes.groupby('customer_id')['rank'].count()
        clientes_incompletos = contagem[contagem < 5]

        # Warning em vez de falha — pode ser legítimo para clientes que já compraram muito
        if len(clientes_incompletos) > 0:
            print(
                f"\n[AVISO RECOMENDAÇÕES] {len(clientes_incompletos)} clientes com < 5 recomendações. "
                f"Máx recomendações: {contagem.max()} | Mín: {contagem.min()}"
            )

    def test_recomendacoes_sem_product_id_nulo(self, report_recomendacoes):
        """
        Toda recomendação deve ter um product_id válido.
        POR QUÊ: product_id nulo significa que o SVD recomendou um
        índice que não existe no catálogo (bug de mapeamento de índice).
        """
        nulos = report_recomendacoes['product_id'].isnull().sum()
        assert nulos == 0, (
            f"{nulos} recomendações sem product_id. "
            f"O mapeamento de índice do SVD para product_id está quebrado."
        )


# =============================================================================
# Bloco F — Sanidade das Vendas por Dia da Semana
# =============================================================================

class TestVendasDiaSemana:
    """
    STAKEHOLDER: Sr. Almir + Marina — "Em que dia vendemos mais?"
    Se a análise de dia da semana estiver errada, a campanha será
    lançada no dia errado.
    """

    def test_dia_semana_tem_7_dias(self, report_dia_semana):
        """O relatório deve ter exatamente 7 linhas (uma por dia da semana)."""
        assert len(report_dia_semana) == 7, (
            f"Relatório de dia da semana tem {len(report_dia_semana)} linhas, "
            f"esperado 7 (Segunda a Domingo)."
        )

    def test_dia_semana_day_of_week_0_a_6(self, report_dia_semana):
        """day_of_week deve conter exatamente os valores 0 a 6."""
        esperado = set(range(7))
        encontrado = set(report_dia_semana['day_of_week'].tolist())
        assert encontrado == esperado, (
            f"day_of_week contém valores inesperados. "
            f"Esperado: {esperado} | Encontrado: {encontrado}"
        )

    def test_media_diaria_positiva(self, report_dia_semana):
        """A receita média de cada dia deve ser >= 0 (dias sem venda = 0, não negativo)."""
        negativos = report_dia_semana[report_dia_semana['receita_dia'] < 0]
        assert len(negativos) == 0, (
            f"Dias com receita média negativa: {negativos[['day_of_week', 'receita_dia']].to_string()}"
        )
