# =============================================================================
# tests/test_02_anomalias_negocio.py
#
# FRENTE   : Análise de Vendas / Qualidade de Dados
# OBJETIVO : Detecta anomalias de valor que impactam margens e KPIs.
#
# STAKEHOLDER: Marina Costa (Gerente de Negócios) — "Preciso garantir que os
#              números que estou vendo na análise são confiáveis."
#              Sr. Almir (Fundador) — "A NF-e é o dado que eu confio."
# =============================================================================

import pytest
import pandas as pd
import numpy as np


# =============================================================================
# Bloco A — Anomalias de Preços e Valores Monetários
# =============================================================================

class TestValoresMonetarios:
    """
    Testa se os valores monetários estão dentro de limites razoáveis.
    POR QUÊ: Preços zerados ou negativos distorcem ticket médio e margem
    sem nenhum erro visível no pipeline — são "silent killers" de KPIs.
    """

    def test_order_items_sem_preco_negativo(self, raw_order_items):
        """Nenhum item de pedido deve ter unit_price negativo."""
        negativos = raw_order_items[raw_order_items['unit_price'] < 0]
        assert len(negativos) == 0, (
            f"{len(negativos)} itens com unit_price NEGATIVO. "
            f"Exemplos:\n{negativos[['id','order_id','unit_price']].head(5)}"
        )

    def test_order_items_sem_total_negativo(self, raw_order_items):
        """line_total não pode ser negativo (seria uma devolução mascarada)."""
        negativos = raw_order_items[raw_order_items['line_total'] < 0]
        assert len(negativos) == 0, f"{len(negativos)} itens com line_total negativo"

    def test_order_items_quantidade_positiva(self, raw_order_items):
        """Quantidade de item em pedido deve ser sempre > 0."""
        invalidos = raw_order_items[raw_order_items['quantity'] <= 0]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} itens com quantity <= 0 em order_items. "
            f"Exemplos:\n{invalidos[['id','order_id','quantity']].head(5)}"
        )

    def test_payments_sem_valor_negativo(self, raw_payments):
        """Pagamentos não devem ter valor negativo."""
        negativos = raw_payments[raw_payments['amount'] < 0]
        assert len(negativos) == 0, f"{len(negativos)} pagamentos com amount negativo"

    def test_orders_total_positivo(self, raw_orders):
        """O total de um pedido deve ser sempre >= 0."""
        invalidos = raw_orders[raw_orders['total'] < 0]
        assert len(invalidos) == 0, f"{len(invalidos)} pedidos com total negativo"

    def test_variants_cost_price_positivo(self, raw_variants):
        """
        Custo de produto deve ser > 0.
        POR QUÊ: Custo zero distorce a margem bruta para 100%, inflando
        lucros artificialmente — o maior risco para a análise da Marina.
        """
        invalidos = raw_variants[raw_variants['cost_price'] <= 0]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} variantes com cost_price <= 0. "
            f"SKUs afetados:\n{raw_variants.loc[invalidos.index, 'sku'].tolist()[:10]}"
        )

    def test_variants_sale_price_positivo(self, raw_variants):
        """Preço de venda deve ser > 0."""
        invalidos = raw_variants[raw_variants['sale_price'] <= 0]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} variantes com sale_price <= 0"
        )

    def test_fiscal_total_positivo(self, raw_fiscal):
        """Valor total de NF-e deve ser positivo."""
        invalidos = raw_fiscal[raw_fiscal['total_amount'] <= 0]
        assert len(invalidos) == 0, (
            f"{len(invalidos)} NF-es com total_amount <= 0"
        )


# =============================================================================
# Bloco B — Consistência de Cálculo (line_total = quantity × unit_price)
# =============================================================================

class TestConsistenciaCalculo:
    """
    Verifica se os valores calculados estão matematicamente corretos.
    POR QUÊ: Inconsistências de cálculo indicam erros de ETL ou
    desconto não registrado corretamente.
    """

    def test_line_total_consistente_com_qty_e_preco(self, raw_order_items):
        """
        line_total deve ser próximo de quantity × unit_price.
        Tolerância de 1% para acomodar descontos por linha.
        POR QUÊ: Divergências maiores que 1% indicam dado corrompido
        ou desconto não registrado no campo correto.
        """
        df = raw_order_items.copy()
        df['expected_total'] = df['quantity'] * df['unit_price']
        df['diff_pct'] = abs(df['line_total'] - df['expected_total']) / df['expected_total'].clip(lower=0.01) * 100

        # Ignora itens com unit_price = 0 (promoção gratuita — tratar separado)
        df_valido = df[df['unit_price'] > 0]
        inconsistentes = df_valido[df_valido['diff_pct'] > 1.0]

        assert len(inconsistentes) == 0, (
            f"{len(inconsistentes)} itens com line_total divergindo > 1% de qty×price. "
            f"Máxima divergência: {df_valido['diff_pct'].max():.2f}%"
        )

    def test_orders_total_coerente_com_subtotal(self, raw_orders):
        """
        total <= subtotal (o total pode ser menor por desconto, nunca maior).
        Tolerância: total pode ser até 0.01 maior (arredondamento).
        """
        problemas = raw_orders[raw_orders['total'] > raw_orders['subtotal'] + 0.01]
        assert len(problemas) == 0, (
            f"{len(problemas)} pedidos com total > subtotal (matematicamente impossível)"
        )


# =============================================================================
# Bloco C — Alerta de Margem Negativa (Venda Abaixo do Custo)
# =============================================================================

class TestMargemProdutos:
    """
    STAKEHOLDER: Sr. Almir — Este é o alerta que ele mais precisa ver.
    Vender abaixo do custo é prejuízo certo, mesmo que a receita pareça alta.
    Este teste não falha o pipeline, mas gera um warning documentado.
    """

    def test_alerta_variantes_custo_maior_que_preco(self, raw_variants):
        """
        Identifica variantes onde cost_price > sale_price (margem negativa).
        É um WARNING, não ERROR — pode ser política intencional (liquidação).
        """
        prejuizo = raw_variants[raw_variants['cost_price'] > raw_variants['sale_price']]

        if len(prejuizo) > 0:
            skus = prejuizo['sku'].tolist()
            pytest.warns(
                UserWarning,
                match="ATENCAO"
            ) if False else None  # pragma: no cover

            # Registra o warning no output do pytest sem falhar o teste
            print(f"\n[AVISO NEGOCIO] {len(prejuizo)} variantes vendendo abaixo do custo:")
            print(prejuizo[['sku', 'cost_price', 'sale_price']].to_string(index=False))

        # Teste "soft" — avisa mas não bloqueia o pipeline
        # Para tornar bloqueador: troque o comentário abaixo
        # assert len(prejuizo) == 0, f"{len(prejuizo)} produtos com margem negativa!"
        assert True  # Mantido como warning; remova esta linha para tornar P0


# =============================================================================
# Bloco D — Consistência NF-e vs Pedido (para o Sr. Almir)
# =============================================================================

class TestNFeConsistencia:
    """
    STAKEHOLDER: Sr. Almir — A NF-e é o documento fiscal oficial.
    Divergência entre o total da NF-e e o total do pedido é um risco
    tributário sério que precisa ser reportado imediatamente.
    """

    def test_nfe_total_proximo_ao_pedido(self, raw_fiscal, raw_orders):
        """
        O total_amount da NF-e deve ser igual ao total do pedido
        com tolerância de R$ 0.02 (arredondamentos de centavos).
        """
        merged = raw_fiscal.merge(
            raw_orders[['id', 'total']],
            left_on='order_id',
            right_on='id',
            how='inner'
        )
        merged['diff'] = abs(merged['total_amount'] - merged['total'])
        divergentes = merged[merged['diff'] > 0.02]

        assert len(divergentes) == 0, (
            f"{len(divergentes)} NF-es com valor divergente do pedido (> R$ 0.02). "
            f"Máxima divergência: R$ {merged['diff'].max():.2f}. "
            f"Amostras:\n{divergentes[['order_id', 'total_amount', 'total', 'diff']].head(5).to_string()}"
        )

    def test_pedidos_pagos_tem_nfe(self, raw_orders, raw_fiscal):
        """
        Todo pedido com status 'paid' deve ter pelo menos uma NF-e emitida.
        POR QUÊ: Venda sem NF-e é irregularidade fiscal.
        """
        pagos    = set(raw_orders[raw_orders['status'] == 'paid']['id'])
        com_nfe  = set(raw_fiscal['order_id'])
        sem_nfe  = pagos - com_nfe

        assert len(sem_nfe) == 0, (
            f"{len(sem_nfe)} pedidos pagos SEM NF-e emitida. "
            f"IDs: {list(sem_nfe)[:10]}"
        )
