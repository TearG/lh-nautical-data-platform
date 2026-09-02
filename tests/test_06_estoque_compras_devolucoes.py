# =============================================================================
# tests/test_06_estoque_compras_devolucoes.py
#
# GAPS COBERTOS: GAP 3 (Estoque) + GAP 4 (Devoluções) + GAP 7 (Compras)
#
# STAKEHOLDER: Marina Costa — "Produto ativo sem estoque é venda perdida."
#              Sr. Almir — "Devolução maior que a compra é fraude ou erro grave."
#              Gabriel Santos — "Movimentação sem referência quebra rastreabilidade."
# =============================================================================

import pytest
import pandas as pd
import numpy as np


# =============================================================================
# GAP 3 — Estoque
# =============================================================================

class TestIntegridadeEstoque:
    """
    Valida consistência do estoque físico e das movimentações.
    POR QUÊ: Estoque negativo ou produto ativo sem estoque são os principais
    causadores de rupturas não monitoradas — maior dor operacional para Marina.
    """

    def test_stock_levels_sem_quantidade_negativa(self, raw_stock_levels):
        """
        quantity_on_hand nunca pode ser negativo.
        POR QUÊ: Estoque físico negativo é matematicamente impossível.
        Indica erro de integração entre o sistema de vendas e o WMS.
        """
        negativos = raw_stock_levels[
            raw_stock_levels['quantity_on_hand'].notna() &
            (raw_stock_levels['quantity_on_hand'] < 0)
        ]
        assert len(negativos) == 0, (
            f"{len(negativos)} registros com quantity_on_hand NEGATIVO.\n"
            f"Variantes afetadas: {negativos['product_variant_id'].tolist()[:10]}"
        )

    def test_variantes_ativas_tem_registro_de_estoque(self, raw_variants, raw_stock_levels):
        """
        Toda variante ativa deve ter pelo menos um registro em stock_levels.
        POR QUÊ: Produto ativo sem estoque = ruptura invisível. O sistema
        permite vender mas não tem como entregar — piora NPS e gera devoluções.
        """
        ativas = set(raw_variants[raw_variants['is_active'] == True]['id'])
        com_estoque = set(raw_stock_levels['product_variant_id'].dropna())
        sem_estoque = ativas - com_estoque

        # Warning, não erro — produto pode ter sido desativado do catálogo recentemente
        if len(sem_estoque) > 0:
            pct = len(sem_estoque) / len(ativas) * 100
            print(
                f"\n[ALERTA RUPTURA] {len(sem_estoque)} variantes ativas ({pct:.1f}%) "
                f"SEM registro em stock_levels.\n"
                f"Variante IDs: {list(sem_estoque)[:15]}"
            )
        # Limiar crítico: mais de 10% de variantes ativas sem estoque é problema grave
        assert len(sem_estoque) / max(len(ativas), 1) < 0.10, (
            f"Mais de 10% das variantes ativas ({len(sem_estoque)}) sem registro de estoque. "
            f"Investigar urgentemente."
        )

    def test_stock_movements_sem_quantidade_zero(self, raw_stock_movements):
        """
        Movimentações de estoque com quantity = 0 são inúteis e confusas.
        POR QUÊ: Podem inflar contagens de movimentação e distorcer análises
        de giro de estoque sem representar nenhuma mudança real.
        """
        zeros = raw_stock_movements[raw_stock_movements['quantity'] == 0]
        assert len(zeros) == 0, (
            f"{len(zeros)} movimentações de estoque com quantity = 0 (sem efeito operacional)"
        )

    def test_stock_movements_reference_id_nao_nulo(self, raw_stock_movements):
        """
        reference_id deve estar preenchido para tipos que exigem rastreabilidade.
        POR QUÊ: Movimentação sem referência não pode ser auditada — impossível
        saber qual venda, compra ou ajuste causou a mudança no estoque.
        """
        tipos_com_ref = ['sale', 'purchase', 'return']
        df = raw_stock_movements[raw_stock_movements['movement_type'].isin(tipos_com_ref)]
        sem_ref = df[df['reference_id'].isnull()]

        assert len(sem_ref) == 0, (
            f"{len(sem_ref)} movimentações do tipo {tipos_com_ref} sem reference_id.\n"
            f"Auditoria impossível para esses registros."
        )


# =============================================================================
# GAP 4 — Devoluções
# =============================================================================

class TestIntegridadeDevolucoes:
    """
    Valida a lógica de negócio das devoluções.
    POR QUÊ: Devoluções mal registradas distorcem taxa de retorno,
    custo de logística reversa e reposição de estoque.
    """

    def test_return_items_fk_order_items(self, raw_return_items, raw_order_items):
        """
        return_items.order_item_id deve referenciar um order_item existente.
        POR QUÊ: Devolução de item que nunca foi vendido é logicamente inválida
        e pode indicar devolução fraudulenta.
        """
        oi_ids    = set(raw_order_items['id'])
        ri_fks    = set(raw_return_items['order_item_id'].dropna())
        orfaos    = ri_fks - oi_ids
        assert len(orfaos) == 0, (
            f"{len(orfaos)} return_items com order_item_id INEXISTENTE em order_items.\n"
            f"Possível devolução fraudulenta ou erro de importação.\n"
            f"IDs inválidos: {list(orfaos)[:10]}"
        )

    def test_quantidade_devolvida_nao_excede_comprada(self, raw_return_items, raw_order_items):
        """
        A quantidade devolvida de um item não pode exceder a quantidade comprada.
        POR QUÊ: Devolver mais do que foi comprado é impossível fisicamente —
        indica duplicação de registro de devolução ou erro sistêmico.
        """
        # Agrupa devoluções por order_item
        dev_por_item = (
            raw_return_items
            .dropna(subset=['order_item_id'])
            .groupby('order_item_id')['quantity']
            .sum()
            .reset_index()
        )
        dev_por_item.columns = ['order_item_id', 'qty_devolvida']

        # Junta com a quantidade original
        merged = dev_por_item.merge(
            raw_order_items[['id', 'quantity']].rename(columns={'id': 'order_item_id'}),
            on='order_item_id', how='inner'
        )

        excesso = merged[merged['qty_devolvida'] > merged['quantity']]
        assert len(excesso) == 0, (
            f"{len(excesso)} itens com quantidade devolvida MAIOR que a comprada.\n"
            f"Amostras:\n{excesso[['order_item_id', 'quantity', 'qty_devolvida']].head(5).to_string(index=False)}"
        )

    def test_return_items_fk_returns(self, raw_return_items, raw_returns):
        """
        return_items.return_id deve referenciar um return existente.
        POR QUÊ: Item de devolução órfão não tem cabeçalho — impossível
        rastrear motivo, cliente ou status da devolução.
        """
        return_ids = set(raw_returns['id'])
        item_fks   = set(raw_return_items['return_id'].dropna())
        orfaos     = item_fks - return_ids

        assert len(orfaos) == 0, (
            f"{len(orfaos)} return_items com return_id INEXISTENTE em returns.\n"
            f"IDs órfãos: {list(orfaos)[:10]}"
        )

    def test_devolucao_unit_refund_positivo(self, raw_return_items):
        """
        unit_refund_amount deve ser >= 0.
        POR QUÊ: Reembolso negativo significaria cobrar o cliente pela devolução
        — comportamento impossível e provavelmente um erro de sinal.
        """
        negativos = raw_return_items[
            raw_return_items['unit_refund_amount'].notna() &
            (raw_return_items['unit_refund_amount'] < 0)
        ]
        assert len(negativos) == 0, (
            f"{len(negativos)} itens de devolução com unit_refund_amount negativo"
        )


# =============================================================================
# GAP 7 — Compras e Fornecedores
# =============================================================================

class TestIntegridadeCompras:
    """
    Valida a consistência do processo de compras (Purchase Orders).
    POR QUÊ: O custo de compra é a base de cálculo da margem bruta.
    Se o custo estiver errado nos POs, a margem estará errada.
    """

    def test_purchase_orders_fk_suppliers(self, raw_purchase_orders, raw_suppliers):
        """
        purchase_orders.supplier_id deve referenciar um fornecedor existente.
        POR QUÊ: PO sem fornecedor não pode ter prazo de entrega monitorado
        e o custo associado não é rastreável para análise de fornecedores.
        """
        supplier_ids = set(raw_suppliers['id'])
        po_fks       = set(raw_purchase_orders['supplier_id'].dropna())
        orfaos       = po_fks - supplier_ids

        assert len(orfaos) == 0, (
            f"{len(orfaos)} purchase_orders com supplier_id INEXISTENTE em suppliers.\n"
            f"IDs: {list(orfaos)[:10]}"
        )

    def test_purchase_order_items_unit_cost_positivo(self, raw_purchase_order_items):
        """
        unit_cost em purchase_order_items deve ser > 0.
        POR QUÊ: Custo zero num item de compra faria aquele produto parecer
        ter margem bruta = 100% nas análises — KPI completamente errado.
        """
        invalidos = raw_purchase_order_items[raw_purchase_order_items['unit_cost'] <= 0]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} itens de PO com unit_cost <= 0.\n"
            f"Variantes afetadas: {raw_purchase_order_items.loc[invalidos.index, 'product_variant_id'].tolist()[:10]}"
        )

    def test_goods_receipt_nao_excede_ordered(self, raw_goods_receipt_items, raw_purchase_order_items):
        """
        A quantidade recebida (goods_receipt) não pode exceder a quantidade pedida.
        Tolerância de 5% para recebimentos parciais por lote.
        POR QUÊ: Receber mais do que pediu indica erro de sistema WMS ou
        fornecedor enviando mercadoria não solicitada — risco financeiro.
        """
        recebido = (
            raw_goods_receipt_items
            .groupby('purchase_order_item_id')['quantity_received']
            .sum()
            .reset_index()
        )
        recebido.columns = ['id', 'qty_recebida']

        merged = recebido.merge(
            raw_purchase_order_items[['id', 'quantity_ordered']],
            on='id', how='inner'
        )

        excesso = merged[merged['qty_recebida'] > merged['quantity_ordered'] * 1.05]
        assert len(excesso) == 0, (
            f"{len(excesso)} itens de PO com recebimento que excede o pedido em > 5%.\n"
            f"Amostras:\n{excesso[['id', 'quantity_ordered', 'qty_recebida']].head(5).to_string(index=False)}"
        )

    def test_purchase_orders_fk_variants(self, raw_purchase_order_items, raw_variants):
        """
        purchase_order_items.product_variant_id deve referenciar variante existente.
        POR QUÊ: Compra de variante inexistente cria custo no estoque que nunca
        será associado a um produto — distorcendo a margem de forma invisível.
        """
        variant_ids = set(raw_variants['id'])
        po_fks      = set(raw_purchase_order_items['product_variant_id'].dropna())
        orfaos      = po_fks - variant_ids

        assert len(orfaos) == 0, (
            f"{len(orfaos)} itens de PO com product_variant_id inexistente em product_variants"
        )
