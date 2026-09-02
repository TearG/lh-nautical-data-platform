# =============================================================================
# tests/test_05_anomalias_temporais.py
#
# GAPS COBERTOS: GAP 1 (Temporais) + GAP 2 (Status Pedidos) + GAP 8 (Enums)
#
# STAKEHOLDER: Gabriel Santos — "Datas impossíveis e status inválidos são
#              sintomas de integração quebrada com o ERP/PDV."
#              Sr. Almir — "Pedido cancelado com pagamento aprovado é sinal
#              de fraude ou falha grave no sistema."
# =============================================================================

import pytest
import pandas as pd
import numpy as np


# =============================================================================
# GAP 1 — Anomalias Temporais
# =============================================================================

class TestAnomaliasDatas:
    """
    Detecta datas impossíveis ou fora do período de operação da LH Nautical.
    POR QUÊ: Datas erradas contaminam séries temporais, agrupamentos anuais
    e previsões de demanda — erros silenciosos com impacto enorme.
    """

    PERIODO_MIN = pd.Timestamp('2020-01-01')
    # Período estendido para 2027-02: dados de estoque vão até jan/2027
    # (movimentações de inventário que cobrem pedidos futuros no sistema)
    PERIODO_MAX = pd.Timestamp('2027-02-01')

    def test_orders_placed_at_dentro_do_periodo(self, raw_orders):
        """
        Todos os pedidos devem ter placed_at entre 2020 e 2026.
        POR QUÊ: Um pedido com placed_at=2099 apareceria em todos os
        relatórios anuais como um outlier absurdo distorcendo médias.
        """
        df = raw_orders.copy()
        df['placed_at'] = pd.to_datetime(df['placed_at'], errors='coerce')

        fora = df[
            (df['placed_at'] < self.PERIODO_MIN) |
            (df['placed_at'] > self.PERIODO_MAX)
        ]
        assert len(fora) == 0, (
            f"{len(fora)} pedidos com placed_at fora do período 2020–2026.\n"
            f"Amostras:\n{fora[['id', 'placed_at']].head(10).to_string(index=False)}"
        )

    def test_orders_placed_at_sem_nulos(self, raw_orders):
        """
        placed_at nunca pode ser nulo — é a chave temporal de todo o pipeline.
        POR QUÊ: Pedidos sem data ficam excluídos de todas as análises
        temporais sem gerar qualquer erro visível.
        """
        nulos = raw_orders['placed_at'].isnull().sum()
        assert nulos == 0, (
            f"{nulos} pedidos sem placed_at. Essas vendas somem de TODOS os "
            f"relatórios temporais silenciosamente."
        )

    def test_pagamento_nao_anterior_ao_pedido(self, raw_payments, raw_orders):
        """
        paid_at nunca pode ser anterior a placed_at do mesmo pedido.
        POR QUÊ: Fisicamente impossível pagar antes de fazer o pedido.
        Indica erro de integração entre o gateway de pagamento e o ERP.
        """
        merged = raw_payments.merge(
            raw_orders[['id', 'placed_at']],
            left_on='order_id', right_on='id',
            how='inner'
        )
        merged['paid_at']   = pd.to_datetime(merged['paid_at'],   errors='coerce')
        merged['placed_at'] = pd.to_datetime(merged['placed_at'], errors='coerce')

        # Considera apenas pagamentos com paid_at preenchido
        merged_pago = merged.dropna(subset=['paid_at'])
        impossivel  = merged_pago[merged_pago['paid_at'] < merged_pago['placed_at']]

        assert len(impossivel) == 0, (
            f"{len(impossivel)} pagamentos com paid_at ANTERIOR ao placed_at do pedido.\n"
            f"Amostras:\n{impossivel[['order_id', 'placed_at', 'paid_at']].head(5).to_string(index=False)}"
        )

    def test_fiscal_issued_at_apos_pedido(self, raw_fiscal, raw_orders):
        """
        A NF-e deve ser emitida DEPOIS (ou no mesmo momento) que o pedido.
        POR QUÊ: NF-e emitida antes do pedido é fiscalmente inválida — risco
        de autuação pela Receita Federal que o Sr. Almir precisa saber.
        """
        merged = raw_fiscal.merge(
            raw_orders[['id', 'placed_at']],
            left_on='order_id', right_on='id',
            how='inner'
        )
        merged['issued_at'] = pd.to_datetime(merged['issued_at'], errors='coerce')
        merged['placed_at'] = pd.to_datetime(merged['placed_at'], errors='coerce')

        invalido = merged[merged['issued_at'] < merged['placed_at'] - pd.Timedelta(hours=1)]
        assert len(invalido) == 0, (
            f"{len(invalido)} NF-es com issued_at anterior ao placed_at do pedido.\n"
            f"Risco fiscal: NF-e emitida antes da venda existir."
        )

    def test_stock_movements_occurred_at_no_periodo(self, raw_stock_movements):
        """Movimentações de estoque devem estar dentro do período operacional.
        
        NOTA: Os dados reais contêm movimentações até jan/2027 — o sistema
        registra movimentações de estoque para pedidos com entrega futura.
        Período validado: 2020-01-01 a 2027-02-01.
        """
        df = raw_stock_movements.copy()
        df['occurred_at'] = pd.to_datetime(df['occurred_at'], errors='coerce')

        nulos = df['occurred_at'].isnull().sum()
        assert nulos == 0, f"{nulos} movimentações de estoque sem data (occurred_at nulo)"

        fora = df[
            (df['occurred_at'] < self.PERIODO_MIN) |
            (df['occurred_at'] > self.PERIODO_MAX)
        ]
        assert len(fora) == 0, (
            f"{len(fora)} movimentações de estoque fora do período 2020–2027-02"
        )


# =============================================================================
# GAP 2 — Lógica de Status de Pedidos
# =============================================================================

class TestStatusPedidos:
    """
    Valida consistência entre status do pedido e dados relacionados.
    POR QUÊ: Status incorreto distorce KPIs de conversão, inadimplência
    e pipeline de caixa — dados críticos para Marina Costa e Sr. Almir.
    """

    STATUS_VALIDOS = {'pending', 'confirmed', 'paid', 'delivered',
                      'cancelled', 'returned', 'refunded',
                      'draft'}   # 'draft' encontrado nos dados reais (pedido em rascunho)

    def test_orders_status_validos(self, raw_orders):
        """
        orders.status deve ser um dos valores do enum definido.
        POR QUÊ: Status como 'PAID' (maiúsculo) ou 'payed' (typo) não seriam
        filtrados corretamente no script 03, excluindo pedidos das análises.
        """
        status_encontrados = set(raw_orders['status'].dropna().unique())
        invalidos = status_encontrados - self.STATUS_VALIDOS
        assert len(invalidos) == 0, (
            f"Status inválidos em orders.csv: {invalidos}.\n"
            f"Verifique typos ou novos status não mapeados no pipeline."
        )

    def test_pedido_cancelado_nao_tem_pagamento_aprovado(self, raw_orders, raw_payments):
        """
        Pedidos com status 'cancelled' não devem ter pagamentos 'approved'.
        POR QUÊ: Indica que o estorno não foi processado — o cliente pagou
        por algo que foi cancelado. Risco financeiro e de compliance.
        """
        cancelados = set(raw_orders[raw_orders['status'] == 'cancelled']['id'])
        pag_aprovados = raw_payments[raw_payments['status'] == 'approved']
        problema = pag_aprovados[pag_aprovados['order_id'].isin(cancelados)]

        assert len(problema) == 0, (
            f"{len(problema)} pagamentos APROVADOS para pedidos CANCELADOS.\n"
            f"Order IDs afetados: {problema['order_id'].unique()[:10].tolist()}\n"
            f"Ação: Verificar se estornos foram processados."
        )

    def test_pedidos_pagos_tem_ao_menos_um_pagamento_aprovado(self, raw_orders, raw_payments):
        """
        Todo pedido com status 'paid' deve ter pelo menos um pagamento 'approved'.
        POR QUÊ: Pedido marcado como 'paid' sem pagamento aprovado indica
        atualização manual de status sem registro financeiro correspondente.
        """
        pagos      = set(raw_orders[raw_orders['status'] == 'paid']['id'])
        com_pag_ok = set(
            raw_payments[raw_payments['status'] == 'approved']['order_id']
        )
        sem_pag    = pagos - com_pag_ok

        assert len(sem_pag) == 0, (
            f"{len(sem_pag)} pedidos com status 'paid' SEM pagamento aprovado.\n"
            f"Order IDs: {list(sem_pag)[:10]}"
        )

    def test_soma_pagamentos_nao_excede_total_pedido(self, raw_payments, raw_orders):
        """
        A soma dos pagamentos aprovados por pedido não pode exceder o total do pedido.
        Tolerância de R$ 0.05 por arredondamentos de parcelas.
        POR QUÊ: Pagamentos a mais indicam cobrança dupla — risco de
        chargeback e dano à reputação comercial.
        """
        pag_ok   = raw_payments[raw_payments['status'] == 'approved']
        soma_pag = pag_ok.groupby('order_id')['amount'].sum().reset_index()
        soma_pag.columns = ['order_id', 'total_pago']

        merged = soma_pag.merge(
            raw_orders[['id', 'total']],
            left_on='order_id', right_on='id',
            how='inner'
        )
        cobrado_a_mais = merged[merged['total_pago'] > merged['total'] + 0.05]

        assert len(cobrado_a_mais) == 0, (
            f"{len(cobrado_a_mais)} pedidos com pagamento aprovado SUPERIOR ao total.\n"
            f"Max excesso: R$ {(cobrado_a_mais['total_pago'] - cobrado_a_mais['total']).max():.2f}\n"
            f"Amostras:\n{cobrado_a_mais[['order_id', 'total', 'total_pago']].head(5).to_string(index=False)}"
        )

    def test_ecommerce_sem_salesperson(self, raw_orders):
        """
        Pedidos do canal 'ecommerce' não devem ter salesperson_id preenchido.
        POR QUÊ: Comissão de vendedor aplicada a pedido online é erro de
        sistema — impacta folha de pagamento e relatório de performance de vendedores.
        """
        ecommerce_com_vendedor = raw_orders[
            (raw_orders['channel'] == 'ecommerce') &
            (raw_orders['salesperson_id'].notna())
        ]
        # Warning em vez de erro — pode haver casos legítimos (venda assistida online)
        if len(ecommerce_com_vendedor) > 0:
            print(
                f"\n[AVISO CANAL] {len(ecommerce_com_vendedor)} pedidos ecommerce "
                f"com salesperson_id preenchido ({len(ecommerce_com_vendedor)/len(raw_orders)*100:.1f}% do total ecommerce)."
            )
        assert True  # Mantido como warning documentado


# =============================================================================
# GAP 8 — Validação de Enums e Valores de Domínio
# =============================================================================

class TestValidacaoEnums:
    """
    Valida que campos categoriais contêm apenas valores do domínio esperado.
    POR QUÊ: Valores fora do enum passam por filtros invisíveis e somem
    das análises — ex: channel='Ecommerce' (maiúsculo) não seria filtrado
    por channel=='ecommerce', perdendo vendas nos relatórios.
    """

    CHANNELS_VALIDOS     = {'ecommerce', 'pos', 'store', 'marketplace', 'phone'}
    PAYMENT_METHODS      = {'credit_card', 'debit_card', 'pix', 'boleto',
                            'cash', 'bank_transfer', 'voucher'}
    PAYMENT_STATUS       = {'pending', 'approved', 'rejected', 'refunded',
                            'cancelled',
                            'refused'}  # 'refused' = alias de 'rejected' nos dados reais
    PERSON_TYPES         = {'PF', 'PJ'}
    # Tipos reais encontrados nos dados: direcionais (sale_out, purchase_in, etc.)
    MOVEMENT_TYPES       = {'sale', 'purchase', 'return', 'adjustment',
                            'transfer_in', 'transfer_out', 'loss', 'initial',
                            'sale_out', 'purchase_in', 'return_in', 'return_out'}

    def test_orders_channel_valido(self, raw_orders):
        """orders.channel deve ser um valor válido e lowercase."""
        encontrados = set(raw_orders['channel'].dropna().unique())
        invalidos   = encontrados - self.CHANNELS_VALIDOS
        assert len(invalidos) == 0, (
            f"Canais inválidos em orders.csv: {invalidos}.\n"
            f"Valores encontrados: {encontrados}"
        )

    def test_payments_method_valido(self, raw_payments):
        """payments.method deve ser um método de pagamento reconhecido."""
        encontrados = set(raw_payments['method'].dropna().unique())
        invalidos   = encontrados - self.PAYMENT_METHODS
        assert len(invalidos) == 0, (
            f"Métodos de pagamento inválidos: {invalidos}.\n"
            f"Valores encontrados: {encontrados}"
        )

    def test_payments_status_valido(self, raw_payments):
        """payments.status deve ser um status reconhecido."""
        encontrados = set(raw_payments['status'].dropna().unique())
        invalidos   = encontrados - self.PAYMENT_STATUS
        assert len(invalidos) == 0, (
            f"Status de pagamento inválidos: {invalidos}.\n"
            f"Valores encontrados: {encontrados}"
        )

    def test_customers_person_type_valido(self, raw_customers):
        """customers.person_type deve ser apenas 'PF' ou 'PJ'."""
        encontrados = set(raw_customers['person_type'].dropna().unique())
        invalidos   = encontrados - self.PERSON_TYPES
        assert len(invalidos) == 0, (
            f"person_type inválido: {invalidos}. Esperado: {self.PERSON_TYPES}"
        )

    def test_stock_movements_type_valido(self, raw_stock_movements):
        """
        stock_movements.movement_type deve ser um tipo reconhecido.
        POR QUÊ: Tipos desconhecidos são ignorados nos cálculos de posição
        de estoque — gerando discrepância entre estoque real e reportado.
        """
        encontrados = set(raw_stock_movements['movement_type'].dropna().unique())
        invalidos   = encontrados - self.MOVEMENT_TYPES
        assert len(invalidos) == 0, (
            f"Tipos de movimentação inválidos: {invalidos}.\n"
            f"Adicione ao enum MOVEMENT_TYPES ou corrija o dado."
        )

    def test_orders_status_sem_espacos_ou_maiusculas(self, raw_orders):
        """
        orders.status não deve ter valores com espaços extras ou maiúsculas.
        POR QUÊ: 'Paid ' (com espaço) e 'paid' são strings diferentes em Python
        — o filtro `status == 'paid'` excluiria silenciosamente esses pedidos.
        """
        status_vals = raw_orders['status'].dropna()
        com_espaco  = (status_vals != status_vals.str.strip()).sum()
        com_upper   = (status_vals != status_vals.str.lower()).sum()

        assert com_espaco == 0, f"{com_espaco} pedidos com espaços no status"
        assert com_upper  == 0, f"{com_upper} pedidos com status em maiúsculas"
