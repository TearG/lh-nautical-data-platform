WITH dias_semana AS (
    SELECT 0 AS dia_num, 'Domingo' AS dia_nome UNION ALL
    SELECT 1, 'Segunda-feira' UNION ALL
    SELECT 2, 'Terça-feira' UNION ALL
    SELECT 3, 'Quarta-feira' UNION ALL
    SELECT 4, 'Quinta-feira' UNION ALL
    SELECT 5, 'Sexta-feira' UNION ALL
    SELECT 6, 'Sábado'
),
vendas_por_dia AS (
    SELECT 
        EXTRACT(DOW FROM CAST(created_at AS TIMESTAMP)) AS dia_num,
        SUM(total) AS valor_venda
    FROM orders
    GROUP BY EXTRACT(DOW FROM CAST(created_at AS TIMESTAMP))
)
SELECT 
    d.dia_nome,
    COALESCE(v.valor_venda, 0) AS valor_venda
FROM dias_semana d
LEFT JOIN vendas_por_dia v ON d.dia_num = v.dia_num
ORDER BY d.dia_num;
