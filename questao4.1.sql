WITH customer_orders AS (
    SELECT 
        customer_id,
        SUM(total) AS faturamento_total,
        COUNT(id) AS frequencia,
        SUM(total) / COUNT(id) AS ticket_medio
    FROM orders
    GROUP BY customer_id
),
customer_diversity AS (
    SELECT 
        o.customer_id,
        COUNT(DISTINCT p.category_id) AS diversidade_categorias
    FROM orders o
    JOIN order_items oi ON o.id = oi.order_id
    JOIN product_variants pv ON oi.product_variant_id = pv.id
    JOIN products p ON pv.product_id = p.id
    GROUP BY o.customer_id
),
elite_customers AS (
    SELECT 
        co.customer_id,
        co.faturamento_total,
        co.frequencia,
        co.ticket_medio,
        cd.diversidade_categorias
    FROM customer_orders co
    JOIN customer_diversity cd ON co.customer_id = cd.customer_id
    WHERE cd.diversidade_categorias >= 13
)
SELECT 
    customer_id,
    faturamento_total,
    frequencia,
    ticket_medio,
    diversidade_categorias
FROM elite_customers
ORDER BY ticket_medio DESC, customer_id ASC
LIMIT 10;
