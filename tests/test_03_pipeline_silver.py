# =============================================================================
# tests/test_03_pipeline_silver.py
#
# FRENTE   : Validação da Camada Silver (Dados Processados)
# OBJETIVO : Garante que os scripts 02 (tratamento) e 03 (análise) não
#            introduziram erros nos dados durante o processamento.
#
# POR QUÊ ISSO É CRÍTICO: Erros de ETL são os mais perigosos porque
# produzem resultados que parecem corretos mas estão errados. Este módulo
# testa os outputs dos NOSSOS scripts contra os dados brutos.
#
# Categorias de erros testados:
#  [I]  Perda de dados (linhas sumindo no join)
#  [II] Linhas duplicadas introduzidas pelo merge
#  [III] Colunas calculadas incorretamente (gross_profit, margin_pct)
#  [IV] Valores nulos introduzidos por joins errados (NaN fantasma)
#  [V]  Integridade das dimensões (dim_*)
#  [VI] Calendário correto (dim_calendar)
#
# STAKEHOLDER: Gabriel Santos (Tech Lead) — "Quero saber se foi o dado
#              original que estava errado ou se fomos nós que quebramos."
# =============================================================================

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR   = Path(__file__).parent.parent
SILVER_DIR = BASE_DIR / "processed"
BRONZE_DIR = BASE_DIR / "1-lh_nautical_csv"


# =============================================================================
# [I] Preservação de Volume — Nenhuma linha pode sumir sem motivo
# =============================================================================

class TestPreservacaoVolume:
    """
    Compara a contagem de linhas do bronze vs silver para detectar
    perda silenciosa de dados durante o tratamento.

    POR QUÊ: JOINs do tipo INNER podem eliminar linhas válidas se a
    chave de join tiver discrepâncias de tipo (int vs float, por ex.).
    Isso é um dos bugs mais comuns em pipelines Pandas.
    """

    def test_fato_returns_mantem_granularidade(self, fato_returns, raw_return_items):
        """
        Garante que todos os itens devolvidos do bronze estao na fato_returns.
        Nao deve haver perda de dados (inner join falho) nem duplicacao indesejada.
        """
        assert len(fato_returns) == len(raw_return_items)

    def test_fato_compras_nao_tem_chaves_nulas(self, fato_compras):
        """
        Garante que a Fato Compras tem os IDs de Pedido e Fornecedor mapeados.
        """
        assert fato_compras['purchase_order_id'].notna().all()
        assert fato_compras['supplier_id'].notna().all()

    def test_fato_fiscal_nao_tem_chaves_nulas(self, fato_fiscal):
        """
        Garante que a Fato Fiscal tem NF-e ID e Order ID mapeados.
        """
        assert fato_fiscal['invoice_id'].notna().all()
        assert fato_fiscal['order_id'].notna().all()

    def test_fato_vendas_preserva_todos_order_items(self, raw_order_items, fato_vendas):
        """
        fato_vendas é derivado de order_items. O total de linhas deve
        ser idêntico ao original — todo item deve ter sido processado.
        """
        bronze_count = len(raw_order_items)
        silver_count = len(fato_vendas)
        assert silver_count == bronze_count, (
            f"[PERDA DE DADOS] order_items bronze: {bronze_count:,} linhas. "
            f"fato_vendas silver: {silver_count:,} linhas. "
            f"Diferença: {bronze_count - silver_count:,} linhas PERDIDAS no join."
        )

    def test_dim_customers_preserva_todos_clientes(self, raw_customers, dim_customers):
        """dim_customers deve ter exatamente o mesmo número de clientes únicos."""
        assert len(dim_customers) == len(raw_customers), (
            f"dim_customers: {len(dim_customers)} vs raw: {len(raw_customers)} "
            f"({len(raw_customers) - len(dim_customers)} clientes perdidos!)"
        )

    def test_fato_payments_preserva_todos_pagamentos(self, raw_payments, fato_payments):
        """fato_payments não pode ter menos linhas que payments.csv original."""
        assert len(fato_payments) == len(raw_payments), (
            f"fato_payments: {len(fato_payments)} vs raw: {len(raw_payments)}"
        )

    def test_fato_stock_preserva_todas_movimentacoes(self, raw_stock_movements, fato_stock):
        """fato_stock é baseado em stock_movements — volume deve ser idêntico."""
        assert len(fato_stock) == len(raw_stock_movements), (
            f"fato_stock: {len(fato_stock)} vs raw: {len(raw_stock_movements)}"
        )

    def test_dim_locations_preserva_todos_locais(self, raw_locations, dim_locations):
        """Todos os locais devem estar na dimensão."""
        assert len(dim_locations) == len(raw_locations), (
            f"dim_locations: {len(dim_locations)} vs raw: {len(raw_locations)}"
        )


# =============================================================================
# [II] Duplicatas Introduzidas pelo Merge
# =============================================================================

class TestDuplicatasIntroduzidas:
    """
    Merges em Pandas podem criar linhas extras se a chave de join
    não for única em um dos lados (relacionamento 1:N acidental).
    POR QUÊ: Um JOIN mal configurado pode multiplicar linhas e fazer
    a receita parecer 2x ou 3x maior do que é na realidade.
    """

    def test_fato_vendas_sem_order_item_id_duplicado(self, fato_vendas):
        """
        Cada order_item_id deve aparecer exatamente uma vez em fato_vendas.
        Se aparecer mais de uma vez, o join com a dimensão de produto
        foi mal configurado (provavelmente uma variante com múltiplos custos).
        """
        dups = fato_vendas.duplicated(subset=['order_item_id']).sum()
        assert dups == 0, (
            f"[DUPLICATA NO JOIN] {dups} order_item_ids duplicados em fato_vendas! "
            f"Isso multiplica a receita artificialmente."
        )

    def test_dim_customers_has_primary_key(self, dim_customers):
        """Clientes devem ter IDs unicos e nao nulos."""
        assert dim_customers['customer_id'].notna().all()
        assert dim_customers['customer_id'].is_unique

    def test_dim_employees_has_primary_key(self, dim_employees):
        """Funcionarios devem ter IDs unicos e nao nulos."""
        assert dim_employees['employee_id'].notna().all()
        assert dim_employees['employee_id'].is_unique

    def test_dim_suppliers_has_primary_key(self, dim_suppliers):
        """Fornecedores devem ter IDs unicos e nao nulos."""
        assert dim_suppliers['supplier_id'].notna().all()
        assert dim_suppliers['supplier_id'].is_unique

    def test_dim_addresses_has_primary_key(self, dim_addresses):
        """Enderecos devem ter IDs unicos e nao nulos."""
        assert dim_addresses['address_id'].notna().all()
        assert dim_addresses['address_id'].is_unique

    def test_dim_customers_sem_customer_id_duplicado(self, dim_customers):
        """Cada cliente deve aparecer exatamente uma vez na dimensão."""
        dups = dim_customers.duplicated(subset=['customer_id']).sum()
        assert dups == 0, (
            f"{dups} customer_ids duplicados em dim_customers — "
            f"joins com fato_vendas vão multiplicar linhas!"
        )

    def test_dim_products_sem_variant_id_duplicado(self, dim_products):
        """
        Cada variante deve aparecer uma vez em dim_products.
        POR QUÊ: dim_products é a junção de variants + products. Se uma
        variante tiver dois registros de produto (produto duplicado no bronze),
        o join em fato_vendas vai duplicar os itens daquela variante.
        """
        dups = dim_products.duplicated(subset=['variant_id']).sum()
        assert dups == 0, (
            f"{dups} variant_ids duplicados em dim_products. "
            f"Verifique se product_variants.csv tem duplicatas."
        )


# =============================================================================
# [III] Correção dos Cálculos das Colunas Derivadas
# =============================================================================

class TestCalculosDerivados:
    """
    Valida as colunas que NOSSO script calculou.
    POR QUÊ: Erros de cálculo em gross_profit e margin_pct contaminariam
    TODOS os relatórios de margem — é o maior risco para a Marina Costa.
    """

    def test_gross_profit_calculado_corretamente(self, fato_vendas):
        """
        gross_profit = line_total - cost_total
        Validamos contra recálculo independente com tolerância de 0.01.
        """
        df = fato_vendas.dropna(subset=['line_total', 'cost_total', 'gross_profit'])
        recalculado  = (df['line_total'] - df['cost_total']).round(2)
        registrado   = df['gross_profit'].round(2)
        diff         = (recalculado - registrado).abs()
        max_diff     = diff.max()

        assert max_diff <= 0.01, (
            f"[ERRO DE CÁLCULO] gross_profit diverge do recálculo em até R$ {max_diff:.4f}. "
            f"Linhas afetadas: {(diff > 0.01).sum():,}"
        )

    def test_margin_pct_dentro_de_limites_fisicos(self, fato_vendas):
        """
        margin_pct deve estar entre -100% e 100% para itens com custo definido.
        POR QUÊ: Margem > 100% indica cost_price = 0 (bug de join) —
        nenhum produto tem lucro bruto maior que o preço de venda.
        """
        df = fato_vendas.dropna(subset=['margin_pct', 'line_total'])
        df_com_receita = df[df['line_total'] > 0]

        acima_100 = (df_com_receita['margin_pct'] > 100).sum()
        assert acima_100 == 0, (
            f"{acima_100} linhas com margin_pct > 100% — "
            f"indica cost_price = 0 (join faltando com dim_products)."
        )

    def test_cost_total_calculado_corretamente(self, fato_vendas):
        """
        cost_total = quantity × cost_price
        Tolerância de R$ 0.02 por linha (arredondamentos).
        """
        df = fato_vendas.dropna(subset=['quantity', 'cost_price', 'cost_total'])
        df = df[df['cost_price'] > 0]  # só onde temos custo definido
        recalculado = (df['quantity'] * df['cost_price']).round(2)
        registrado  = df['cost_total'].round(2)
        diff        = (recalculado - registrado).abs()

        assert diff.max() <= 0.02, (
            f"[ERRO DE CÁLCULO] cost_total diverge em até R$ {diff.max():.4f}. "
            f"Linhas: {(diff > 0.02).sum():,}"
        )

    def test_order_date_derivado_corretamente_de_placed_at(self, fato_vendas):
        """
        order_date deve ser placed_at truncado ao dia (sem hora/minuto).
        POR QUÊ: Se order_date estiver errado, a análise de "vendas por dia"
        do script 03 agrupa dados no dia errado.
        """
        df = fato_vendas.dropna(subset=['placed_at', 'order_date'])
        order_date_esperado = df['placed_at'].dt.normalize()
        order_date_real     = pd.to_datetime(df['order_date']).dt.normalize()
        diff = (order_date_esperado != order_date_real).sum()

        assert diff == 0, (
            f"{diff} linhas com order_date diferente de placed_at truncado ao dia. "
            f"Isso quebra a análise temporal."
        )

    def test_year_month_derivados_corretamente(self, fato_vendas):
        """
        As colunas 'year' e 'month' devem corresponder a placed_at.
        POR QUÊ: Se estiverem erradas, a análise "vendas por ano/mês" 
        agrupará dados no período errado.
        """
        df = fato_vendas.dropna(subset=['placed_at', 'year', 'month'])
        year_errado  = (df['year']  != df['placed_at'].dt.year).sum()
        month_errado = (df['month'] != df['placed_at'].dt.month).sum()

        assert year_errado == 0,  f"{year_errado} linhas com 'year' incorreto em fato_vendas"
        assert month_errado == 0, f"{month_errado} linhas com 'month' incorreto em fato_vendas"


# =============================================================================
# [IV] Nulos Fantasma Introduzidos por Joins Incorretos
# =============================================================================

class TestNulosIntroduzidos:
    """
    Um LEFT JOIN com chave errada cria NaNs nas colunas do lado direito
    para todas as linhas que não fizeram match — silenciosamente.
    POR QUÊ: Esses NaNs são excluídos do cálculo de média/soma
    no Pandas, distorcendo todos os KPIs derivados.
    """

    def test_fato_vendas_sem_order_id_nulo(self, fato_vendas):
        """Toda linha de fato_vendas deve ter um order_id válido."""
        nulos = fato_vendas['order_id'].isnull().sum()
        assert nulos == 0, f"{nulos} linhas em fato_vendas sem order_id (join quebrado)"

    def test_fato_vendas_sem_customer_id_nulo(self, fato_vendas):
        """
        customer_id não pode ser nulo após o join.
        POR QUÊ: Se o join com orders falhou para alguma linha,
        essa linha ficou sem customer_id — invisível nas análises de CLV.
        """
        nulos = fato_vendas['customer_id'].isnull().sum()
        assert nulos == 0, (
            f"{nulos} linhas em fato_vendas sem customer_id. "
            f"O join com orders.csv foi incompleto para essas linhas."
        )

    def test_fato_vendas_sem_line_total_nulo(self, fato_vendas):
        """line_total nunca pode ser nulo — é a receita da linha."""
        nulos = fato_vendas['line_total'].isnull().sum()
        assert nulos == 0, f"{nulos} linhas com line_total nulo em fato_vendas"

    def test_fato_vendas_produto_join_cobertura_aceitavel(self, fato_vendas):
        """
        Após o join com dim_products, o percentual de linhas SEM product_name
        deve ser menor que 5% (tolerância para variantes removidas/inativas).
        POR QUÊ: Se > 5% das linhas não encontraram produto, o join está errado.
        """
        df = fato_vendas
        sem_produto = df['product_name'].isnull().sum()
        pct_sem_produto = sem_produto / len(df) * 100

        assert pct_sem_produto < 5.0, (
            f"{sem_produto:,} linhas ({pct_sem_produto:.1f}%) sem product_name em fato_vendas. "
            f"O join com dim_products está cobrindo menos de 95% dos itens — "
            f"verifique se o join é feito por variant_id corretamente."
        )

    def test_dim_customers_trade_name_sem_nulo(self, dim_customers):
        """
        Após tratamento, trade_name não pode ter nulos — foi preenchido com legal_name.
        POR QUÊ: Nosso script 02 fez fillna(legal_name) — se ainda houver nulos,
        a lógica de preenchimento não funcionou.
        """
        nulos = dim_customers['trade_name'].isnull().sum()
        assert nulos == 0, (
            f"{nulos} clientes ainda com trade_name nulo em dim_customers. "
            f"O fillna(legal_name) do script 02 falhou para esses casos."
        )


# =============================================================================
# [V] Integridade das Dimensões Geradas
# =============================================================================

class TestIntegridadeDimensoes:
    """
    Valida que as tabelas dimensão geradas pelo nosso script
    estão completas e coerentes com o bronze.
    """

    def test_dim_calendar_cobre_periodo_completo(self, dim_calendar):
        """
        dim_calendar deve cobrir de 2020-01-01 a 2026-12-31 sem lacunas.
        POR QUÊ: Se houver dias faltando, análises de séries temporais
        que fazem LEFT JOIN com o calendário vão ter lacunas invisíveis.
        """
        datas = pd.to_datetime(dim_calendar['date'])
        min_data = datas.min()
        max_data = datas.max()

        assert min_data == pd.Timestamp('2020-01-01'), (
            f"dim_calendar começa em {min_data}, esperado 2020-01-01"
        )
        assert max_data == pd.Timestamp('2026-12-31'), (
            f"dim_calendar termina em {max_data}, esperado 2026-12-31"
        )

        # Verifica lacunas (dias faltando)
        todos_os_dias = pd.date_range(start='2020-01-01', end='2026-12-31', freq='D')
        dias_no_calendar = set(datas.dt.normalize())
        dias_esperados   = set(todos_os_dias)
        faltando = dias_esperados - dias_no_calendar

        assert len(faltando) == 0, (
            f"{len(faltando)} dias faltando em dim_calendar. "
            f"Exemplos: {sorted(list(faltando))[:5]}"
        )

    def test_dim_calendar_campos_derivados_corretos(self, dim_calendar):
        """
        Valida que year, month, day_of_week foram calculados corretamente.
        POR QUÊ: Esses campos são usados em TODOS os agrupamentos temporais.
        """
        df = dim_calendar.copy()
        df['date'] = pd.to_datetime(df['date'])

        year_errado  = (df['year']        != df['date'].dt.year).sum()
        month_errado = (df['month']       != df['date'].dt.month).sum()
        dow_errado   = (df['day_of_week'] != df['date'].dt.dayofweek).sum()

        assert year_errado  == 0, f"{year_errado} linhas com 'year' errado em dim_calendar"
        assert month_errado == 0, f"{month_errado} linhas com 'month' errado em dim_calendar"
        assert dow_errado   == 0, f"{dow_errado} linhas com 'day_of_week' errado em dim_calendar"

    def test_dim_products_tem_cost_price(self, dim_products):
        """
        Após o join com product_variants, dim_products deve ter cost_price.
        POR QUÊ: Sem cost_price, fato_vendas.cost_total fica nulo para
        todos os itens — zerando o cálculo de lucro bruto.
        """
        nulos = dim_products['cost_price'].isnull().sum()
        pct   = nulos / len(dim_products) * 100
        assert pct < 2.0, (
            f"{nulos} produtos ({pct:.1f}%) sem cost_price em dim_products. "
            f"O join com product_variants.csv falhou para esses registros."
        )


# =============================================================================
# [VI] Reconciliação de Totais Bronze vs Silver
# =============================================================================

class TestReconciliacaoTotais:
    """
    Compara totais financeiros entre bronze e silver para confirmar
    que nenhum valor foi alterado ou perdido durante o tratamento.

    POR QUÊ: Este é o teste definitivo de integridade do ETL. Se a
    soma de line_total no bronze for diferente do silver, algo foi
    alterado indevidamente no processamento.
    """

    def test_soma_line_total_identica_bronze_silver(self, raw_order_items, fato_vendas):
        """
        A soma de line_total em order_items (bronze) deve ser igual
        à soma de line_total em fato_vendas (silver).
        Tolerância de R$ 1.00 por arredondamentos de float.
        """
        soma_bronze = raw_order_items['line_total'].sum()
        soma_silver = fato_vendas['line_total'].sum()
        diff        = abs(soma_bronze - soma_silver)

        assert diff <= 1.0, (
            f"[DIVERGÊNCIA FINANCEIRA CRÍTICA] "
            f"Soma bronze: R$ {soma_bronze:,.2f} | "
            f"Soma silver: R$ {soma_silver:,.2f} | "
            f"Diferença: R$ {diff:,.2f}. "
            f"Dados foram alterados ou perdidos no processamento!"
        )

    def test_soma_quantidade_identica_bronze_silver(self, raw_order_items, fato_vendas):
        """
        A quantidade total de itens vendidos deve ser idêntica no bronze e silver.
        POR QUÊ: Se quantidade mudou, significa que algum valor foi imputado
        incorretamente durante o processamento.
        """
        qty_bronze = raw_order_items['quantity'].sum()
        qty_silver = fato_vendas['quantity'].sum()

        assert qty_bronze == qty_silver, (
            f"Quantidade total bronze: {qty_bronze:,} | "
            f"Quantidade silver: {qty_silver:,} | "
            f"Diferença: {abs(qty_bronze - qty_silver):,} unidades."
        )

    def test_numero_pedidos_unicos_preservado(self, raw_orders, fato_vendas):
        """
        O número de pedidos únicos em fato_vendas não pode ser maior
        que em orders.csv (nenhum pedido pode ser "inventado" pelo join).
        """
        pedidos_bronze = raw_orders['id'].nunique()
        pedidos_silver = fato_vendas['order_id'].nunique()

        assert pedidos_silver <= pedidos_bronze, (
            f"fato_vendas tem {pedidos_silver} pedidos únicos, "
            f"mas orders.csv só tem {pedidos_bronze}. "
            f"O join criou pedidos inexistentes!"
        )

    def test_numero_clientes_unicos_preservado(self, raw_customers, fato_vendas):
        """
        O número de clientes únicos em fato_vendas não pode exceder
        o total de clientes cadastrados.
        """
        clientes_bronze = raw_customers['id'].nunique()
        clientes_silver = fato_vendas['customer_id'].nunique()

        assert clientes_silver <= clientes_bronze, (
            f"fato_vendas tem {clientes_silver} clientes únicos, "
            f"mas customers.csv tem {clientes_bronze}. "
            f"O join introduziu customer_ids inválidos!"
        )
