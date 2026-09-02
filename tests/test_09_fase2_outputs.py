# =============================================================================
# tests/test_09_fase2_outputs.py
#
# OBJETIVO : Valida os 7 relatórios Gold gerados pelo script 07 (Fase 2).
#            Esses eram os únicos outputs sem cobertura de testes.
#
# RELATÓRIOS COBERTOS:
#   07a_performance_fornecedores.csv  — Supply Chain
#   07b_vendas_por_estado.csv         — Logística / Geolocalização
#   07c_performance_vendedores.csv    — RH / POS
#   07d_risco_fiscal_por_mes.csv      — Auditoria Fiscal
#   07e_atributos_produtos_top.csv    — Catálogo / Atributos
#   07f_matriz_produto_fornecedor.csv — Procurement
#   07g_posicao_estoque_atual.csv     — Estoque Atual
#
# STAKEHOLDERS:
#   Sr. Almir  — 07d (risco fiscal), 07f (compras), 07g (estoque)
#   Marina     — 07b (logística), 07c (vendedores), 07e (atributos)
#   Gabriel    — 07a (fornecedores), coerência entre Silver e Gold
# =============================================================================

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / "outputs" / "reports"
SILVER_DIR  = BASE_DIR / "processed"


# =============================================================================
# Existência dos relatórios Fase 2
# =============================================================================

class TestExistenciaRelatoriosFase2:
    """
    Garante que todos os 7 relatórios do script 07 foram gerados.
    POR QUÊ: Ausência de um arquivo significa que uma seção do script 07
    falhou silenciosamente — o dashboard ou a análise apresentada estaria
    incompleta sem nenhum aviso visível.
    """

    RELATORIOS = [
        "07a_performance_fornecedores.csv",
        "07b_vendas_por_estado.csv",
        "07c_performance_vendedores.csv",
        "07d_risco_fiscal_por_mes.csv",
        "07e_atributos_produtos_top.csv",
        "07f_matriz_produto_fornecedor.csv",
        "07g_posicao_estoque_atual.csv",
    ]

    @pytest.mark.parametrize("relatorio", RELATORIOS)
    def test_relatorio_fase2_existe(self, relatorio):
        path = REPORTS_DIR / relatorio
        assert path.exists(), (
            f"[OUTPUT FALTANDO] '{relatorio}' não foi gerado.\n"
            f"Execute python 07_analise_fase2.py antes de rodar os testes."
        )

    @pytest.mark.parametrize("relatorio", RELATORIOS)
    def test_relatorio_fase2_nao_vazio(self, relatorio):
        """Arquivo gerado não pode estar vazio (0 linhas de dados)."""
        path = REPORTS_DIR / relatorio
        if not path.exists():
            pytest.skip(f"{relatorio} não existe — execute o script 07 primeiro.")
        df = pd.read_csv(path)
        assert len(df) > 0, f"{relatorio} existe mas está vazio (0 linhas de dados)."


# =============================================================================
# 07A — Performance de Fornecedores (Supply Chain)
# =============================================================================

class TestPerformanceFornecedores:
    """
    STAKEHOLDER: Sr. Almir / Gabriel Santos
    POR QUÊ: Lead time e atraso de fornecedores são a base para negociações
    de SLA e planejamento de estoque. Dados incorretos aqui levam a rupturas.
    """

    @pytest.fixture(scope="class")
    def perf_forn(self):
        path = REPORTS_DIR / "07a_performance_fornecedores.csv"
        if not path.exists():
            pytest.skip("07a não existe — execute o script 07 primeiro.")
        return pd.read_csv(path)

    def test_lead_time_nao_negativo(self, perf_forn):
        """
        lead_time_medio não pode ser negativo.
        POR QUÊ: Lead time negativo significa que o produto foi recebido
        antes de ser pedido — impossível fisicamente, indica bug no join.
        """
        negativos = perf_forn[perf_forn["lead_time_medio"] < 0]
        assert len(negativos) == 0, (
            f"{len(negativos)} fornecedores com lead_time_medio NEGATIVO.\n"
            f"{negativos[['supplier_id', 'legal_name', 'lead_time_medio']].to_string(index=False)}"
        )

    def test_total_gasto_positivo(self, perf_forn):
        """Total gasto por fornecedor deve ser > 0."""
        invalidos = perf_forn[perf_forn["total_gasto"] <= 0]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} fornecedores com total_gasto <= 0.\n"
            f"Indica que purchase_order_items.unit_cost está zerado para esses."
        )

    def test_sem_supplier_id_nulo(self, perf_forn):
        """Toda linha deve ter supplier_id mapeado."""
        nulos = perf_forn["supplier_id"].isnull().sum()
        assert nulos == 0, f"{nulos} linhas sem supplier_id em performance_fornecedores."

    def test_supplier_id_unico_por_linha(self, perf_forn):
        """
        Cada fornecedor deve aparecer uma única vez.
        POR QUÊ: Duplicata de fornecedor dobra o total_gasto e lead_time médio
        reportados — distorcendo completamente o ranking de fornecedores.
        """
        dups = perf_forn["supplier_id"].duplicated().sum()
        assert dups == 0, (
            f"{dups} supplier_ids duplicados em 07a.\n"
            f"O groupby do script 07 não deduplicou corretamente."
        )

    def test_qtd_compras_positiva(self, perf_forn):
        """qtd_compras deve ser >= 1 para todo fornecedor listado."""
        invalidos = perf_forn[perf_forn["qtd_compras"] < 1]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} fornecedores com qtd_compras < 1."
        )


# =============================================================================
# 07B — Vendas por Estado (Logística / Geolocalização)
# =============================================================================

class TestVendasPorEstado:
    """
    STAKEHOLDER: Marina Costa
    POR QUÊ: Receita por estado define planejamento logístico e expansão.
    Se a soma dos estados não fechar com a receita total, os dados de
    endereço estão cobrindo apenas parte dos clientes.
    """

    @pytest.fixture(scope="class")
    def vendas_estado(self):
        path = REPORTS_DIR / "07b_vendas_por_estado.csv"
        if not path.exists():
            pytest.skip("07b não existe — execute o script 07 primeiro.")
        return pd.read_csv(path)

    def test_receita_total_positiva_por_estado(self, vendas_estado):
        """Receita por estado deve ser > 0."""
        invalidos = vendas_estado[vendas_estado["receita_total"] <= 0]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} estados com receita <= 0."
        )

    def test_qtd_pedidos_positiva_por_estado(self, vendas_estado):
        """Quantidade de pedidos por estado deve ser >= 1."""
        invalidos = vendas_estado[vendas_estado["qtd_pedidos"] < 1]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} estados com qtd_pedidos < 1."
        )

    def test_cobertura_endereco_minima(self, vendas_estado, fato_vendas):
        """
        A soma de qtd_pedidos por estado deve cobrir ao menos 70% dos
        pedidos pagos/confirmados/entregues em fato_vendas.
        POR QUÊ: Cobertura < 70% indica que o join com dim_addresses
        falhou para a maioria dos clientes — geolocalização inútil.
        """
        total_pedidos_fato = fato_vendas[
            fato_vendas["status"].isin(["paid", "confirmed", "delivered"])
        ]["order_id"].nunique()

        total_pedidos_estado = vendas_estado[
            vendas_estado["state"] != "Desconhecido"
        ]["qtd_pedidos"].sum()

        cobertura = total_pedidos_estado / max(total_pedidos_fato, 1) * 100

        print(f"\n[COBERTURA ENDEREÇO] {cobertura:.1f}% dos pedidos com estado identificado.")
        assert cobertura >= 70, (
            f"Apenas {cobertura:.1f}% dos pedidos têm estado identificado.\n"
            f"O join com dim_addresses está cobrindo menos de 70% dos clientes."
        )

    def test_sem_estado_nulo(self, vendas_estado):
        """
        Coluna 'state' não pode ser nula — o script usa 'Desconhecido' como fallback.
        POR QUÊ: Nulo quebraria agrupamentos downstream que esperam string.
        """
        nulos = vendas_estado["state"].isnull().sum()
        assert nulos == 0, (
            f"{nulos} linhas com state nulo. O fillna('Desconhecido') falhou."
        )


# =============================================================================
# 07C — Performance de Vendedores (RH / POS)
# =============================================================================

class TestPerformanceVendedores:
    """
    STAKEHOLDER: Marina Costa (comissionamento)
    POR QUÊ: Vendedor com receita incorreta recebe comissão errada.
    Um vendedor de e-commerce no relatório POS indica filtro de canal errado.
    """

    @pytest.fixture(scope="class")
    def perf_vend(self):
        path = REPORTS_DIR / "07c_performance_vendedores.csv"
        if not path.exists():
            pytest.skip("07c não existe — execute o script 07 primeiro.")
        return pd.read_csv(path)

    def test_receita_vendedor_positiva(self, perf_vend):
        """Receita gerada por vendedor deve ser > 0."""
        invalidos = perf_vend[perf_vend["receita_gerada"] <= 0]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} vendedores com receita_gerada <= 0."
        )

    def test_qtd_vendas_positiva(self, perf_vend):
        """Cada vendedor deve ter ao menos 1 venda registrada."""
        invalidos = perf_vend[perf_vend["qtd_vendas"] < 1]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} vendedores com qtd_vendas < 1."
        )

    def test_salesperson_id_unico(self, perf_vend):
        """
        Cada vendedor deve aparecer uma única vez.
        POR QUÊ: Duplicata no relatório de vendedores pagaria comissão dupla.
        """
        dups = perf_vend["salesperson_id"].duplicated().sum()
        assert dups == 0, (
            f"{dups} salesperson_ids duplicados em 07c.\n"
            f"O groupby do script 07 criou linhas extras."
        )

    def test_vendedores_reconciliam_com_fato_vendas(self, perf_vend, fato_vendas):
        """
        Soma de receita dos vendedores deve ser <= receita POS com salesperson em fato_vendas.
        POR QUÊ: Receita de vendedores > receita POS indica que pedidos de
        outros canais foram incluídos (filtro de channel=='pos' quebrado).

        NOTA: O script 07 inclui todos os status (sem filtro de status pagos)
        para refletir a performance bruta de vendas — incluindo pedidos em
        andamento. O teste usa a mesma lógica sem filtro de status.
        """
        receita_pos_fato = fato_vendas[
            (fato_vendas["channel"] == "pos") &
            fato_vendas["salesperson_id"].notna()
        ]["line_total"].sum()

        receita_vend = perf_vend["receita_gerada"].sum()

        assert receita_vend <= receita_pos_fato * 1.001, (
            f"Receita total de vendedores (R$ {receita_vend:,.2f}) excede\n"
            f"a receita POS com salesperson em fato_vendas (R$ {receita_pos_fato:,.2f}).\n"
            f"Filtro de canal channel=='pos' pode estar incorreto no script 07."
        )


# =============================================================================
# 07D — Risco Fiscal por Mês (Auditoria)
# =============================================================================

class TestRiscoFiscal:
    """
    STAKEHOLDER: Sr. Almir
    POR QUÊ: O risco fiscal é a descoberta mais crítica do projeto —
    10.117 pedidos sem NF-e. A validação do relatório mensal garante
    que esse número está sendo reportado corretamente por período.
    """

    @pytest.fixture(scope="class")
    def risco_fiscal(self):
        path = REPORTS_DIR / "07d_risco_fiscal_por_mes.csv"
        if not path.exists():
            pytest.skip("07d não existe — execute o script 07 primeiro.")
        return pd.read_csv(path)

    def test_anos_dentro_do_periodo(self, risco_fiscal):
        """Anos no relatório fiscal devem estar entre 2020 e 2026."""
        invalidos = risco_fiscal[
            (risco_fiscal["year"] < 2020) | (risco_fiscal["year"] > 2026)
        ]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} linhas com ano fora do período 2020-2026:\n"
            f"{invalidos[['year', 'month']].to_string(index=False)}"
        )

    def test_meses_validos(self, risco_fiscal):
        """Meses devem estar entre 1 e 12."""
        invalidos = risco_fiscal[
            (risco_fiscal["month"] < 1) | (risco_fiscal["month"] > 12)
        ]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} linhas com mês inválido (fora de 1-12)."
        )

    def test_qtd_pedidos_sem_nfe_positiva(self, risco_fiscal):
        """Cada mês no relatório deve ter ao menos 1 pedido sem NF-e."""
        invalidos = risco_fiscal[risco_fiscal["qtd_pedidos_sem_nfe"] < 1]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} meses com qtd_pedidos_sem_nfe < 1.\n"
            f"Se não há pedidos sem NF-e naquele mês, ele não deveria aparecer."
        )

    def test_total_pedidos_sem_nfe_consistente(self, risco_fiscal, fato_vendas):
        """
        O total de pedidos sem NF-e no relatório mensal deve bater com a
        descoberta da investigação de veracidade (~10.117 pedidos).
        Tolerância de 5% para diferenças de período/filtro.

        POR QUÊ: Se os números não fecham entre os dois scripts (06 e 07),
        o Sr. Almir recebeu informações inconsistentes sobre o risco fiscal.
        """
        total_sem_nfe_relatorio = risco_fiscal["qtd_pedidos_sem_nfe"].sum()

        # Recalcula independentemente para validação cruzada
        fato_fiscal = pd.read_csv(SILVER_DIR / "fato_fiscal.csv")
        vendas_pagas = fato_vendas[
            fato_vendas["status"].isin(["paid", "confirmed", "delivered"])
        ]
        pedidos_com_nfe = set(
            fato_fiscal[fato_fiscal["status"] == "authorized"]["order_id"].unique()
        )
        pedidos_sem_nfe_recalc = (
            ~vendas_pagas["order_id"].isin(pedidos_com_nfe)
        ).sum()  # linhas sem NF-e (não pedidos únicos)

        pedidos_unicos_sem_nfe = vendas_pagas[
            ~vendas_pagas["order_id"].isin(pedidos_com_nfe)
        ]["order_id"].nunique()

        print(f"\n[RISCO FISCAL] Pedidos únicos sem NF-e: {pedidos_unicos_sem_nfe:,}")
        print(f"[RISCO FISCAL] Total no relatório 07d:  {total_sem_nfe_relatorio:,}")

        diff_pct = abs(total_sem_nfe_relatorio - pedidos_unicos_sem_nfe) / max(pedidos_unicos_sem_nfe, 1) * 100
        assert diff_pct <= 5, (
            f"Total de pedidos sem NF-e no relatório 07d ({total_sem_nfe_relatorio:,})\n"
            f"diverge em {diff_pct:.1f}% do recálculo independente ({pedidos_unicos_sem_nfe:,}).\n"
            f"Scripts 06 e 07 estão reportando números inconsistentes ao Sr. Almir."
        )

    def test_receita_nao_faturada_positiva(self, risco_fiscal):
        """Receita não faturada (sem NF-e) deve ser > 0 em todo mês do relatório."""
        invalidos = risco_fiscal[risco_fiscal["receita_nao_faturada"] <= 0]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} meses com receita_nao_faturada <= 0.\n"
            f"Pedidos sem NF-e não podem ter receita zero."
        )


# =============================================================================
# 07G — Posição Atual de Estoque (Operacional)
# =============================================================================

class TestPosicaoEstoque:
    """
    STAKEHOLDER: Sr. Almir / Marina Costa
    POR QUÊ: O relatório de estoque é a base para decisões de compra.
    Alerta de ruptura incorreto leva a compras desnecessárias ou rupturas reais.
    """

    @pytest.fixture(scope="class")
    def estoque(self):
        path = REPORTS_DIR / "07g_posicao_estoque_atual.csv"
        if not path.exists():
            pytest.skip("07g não existe — execute o script 07 primeiro.")
        return pd.read_csv(path)

    def test_quantidade_on_hand_nao_negativa(self, estoque):
        """
        quantity_on_hand não pode ser negativo.
        POR QUÊ: Estoque físico negativo é fisicamente impossível.
        Indica que dim_stock_levels tem erro de integração WMS.
        """
        negativos = estoque[estoque["quantity_on_hand"] < 0]
        assert len(negativos) == 0, (
            f"{len(negativos)} registros com quantity_on_hand NEGATIVO em 07g.\n"
            f"Variantes afetadas: {negativos['product_variant_id'].tolist()[:10]}"
        )

    def test_alerta_estoque_baixo_e_booleano(self, estoque):
        """
        alerta_estoque_baixo deve conter apenas True/False.
        POR QUÊ: Se o campo tiver NaN ou string, o dashboard vai exibir
        alertas incorretos ou travar ao tentar filtrar por True.
        """
        valores_unicos = set(estoque["alerta_estoque_baixo"].dropna().unique())
        invalidos = valores_unicos - {True, False, 1, 0}
        assert len(invalidos) == 0, (
            f"alerta_estoque_baixo contém valores inesperados: {invalidos}.\n"
            f"Esperado: apenas True/False (ou 1/0)."
        )

    def test_valor_custo_nao_negativo(self, estoque):
        """estoque_valor_custo = quantity_on_hand × cost_price >= 0."""
        invalidos = estoque[
            estoque["estoque_valor_custo"].notna() &
            (estoque["estoque_valor_custo"] < 0)
        ]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} registros com estoque_valor_custo negativo.\n"
            f"cost_price pode estar negativo para essas variantes."
        )

    def test_sem_product_variant_id_nulo(self, estoque):
        """Toda linha de estoque deve ter um product_variant_id."""
        nulos = estoque["product_variant_id"].isnull().sum()
        assert nulos == 0, (
            f"{nulos} linhas em 07g sem product_variant_id.\n"
            f"O join com dim_stock_levels falhou para essas linhas."
        )

    def test_alertas_consistentes_com_reorder_point(self, estoque):
        """
        alerta_estoque_baixo = True <=> quantity_on_hand <= reorder_point.
        POR QUÊ: Alerta aceso com estoque suficiente gera compras desnecessárias.
        Alerta apagado com estoque insuficiente causa ruptura invisível.
        """
        df = estoque.dropna(subset=["reorder_point"])
        df["alerta_recalc"] = df["quantity_on_hand"] <= df["reorder_point"]

        # Compara como booleano
        alerta_registrado = df["alerta_estoque_baixo"].astype(bool)
        divergentes = (alerta_registrado != df["alerta_recalc"]).sum()

        assert divergentes == 0, (
            f"{divergentes} registros com alerta_estoque_baixo inconsistente.\n"
            f"A lógica quantity_on_hand <= reorder_point não corresponde ao campo gravado."
        )
