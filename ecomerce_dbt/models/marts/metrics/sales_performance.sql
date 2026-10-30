
WITH monthly_sales AS (

    -- 1. Aggregate sales metrics by month
    SELECT

        DATE_TRUNC(
            'MONTH',
            ORDER_CREATED_AT
        ) AS SALES_MONTH,

        COUNT(DISTINCT ORDER_ID) AS TOTAL_ORDERS,

        SUM(ITEM_COUNT) AS TOTAL_ITEMS,

        SUM(ORDER_SALES_AMOUNT) AS TOTAL_SALES,

        SUM(ORDER_ESTIMATED_COST) AS TOTAL_ESTIMATED_COST,

        SUM(ORDER_ESTIMATED_GROSS_PROFIT)
            AS TOTAL_ESTIMATED_GROSS_PROFIT,

        AVG(ORDER_SALES_AMOUNT) AS AVERAGE_ORDER_AMOUNT

    FROM {{ ref('fct_orders') }}

    WHERE ORDER_CREATED_AT IS NOT NULL

    GROUP BY
        DATE_TRUNC('MONTH', ORDER_CREATED_AT)

),

sales_with_previous_month AS (

    -- 2. Calculate previous month's sales

    SELECT

        *,

        LAG(TOTAL_SALES) OVER (
            ORDER BY SALES_MONTH
        ) AS PREVIOUS_MONTH_SALES,

        LAG(TOTAL_ORDERS) OVER (
            ORDER BY SALES_MONTH
        ) AS PREVIOUS_MONTH_ORDERS,

        LAG(TOTAL_ITEMS) OVER (
            ORDER BY SALES_MONTH
        ) AS PREVIOUS_MONTH_ITEMS,

        LAG(TOTAL_ESTIMATED_COST) OVER (
            ORDER BY SALES_MONTH
        ) AS PREVIOUS_MONTH_ESTIMATED_COST

    FROM monthly_sales

),

final AS (

    -- 3. Calculate month-over-month growth

    SELECT

        SALES_MONTH,

        YEAR(SALES_MONTH) AS SALES_YEAR,

        MONTH(SALES_MONTH) AS SALES_MONTH_NUMBER,

        TOTAL_ORDERS,

        TOTAL_ITEMS,

        TOTAL_SALES,

        TOTAL_ESTIMATED_COST,

        TOTAL_ESTIMATED_GROSS_PROFIT,

        AVERAGE_ORDER_AMOUNT,

        PREVIOUS_MONTH_SALES,

        PREVIOUS_MONTH_ORDERS,

        PREVIOUS_MONTH_ITEMS,

        PREVIOUS_MONTH_ESTIMATED_COST,

        CASE
            WHEN PREVIOUS_MONTH_SALES IS NULL
                OR PREVIOUS_MONTH_SALES = 0
            THEN NULL

            ELSE
                (TOTAL_SALES - PREVIOUS_MONTH_SALES)
                / PREVIOUS_MONTH_SALES * 100

        END AS SALES_MOM_GROWTH_PCT

    FROM sales_with_previous_month

)

SELECT *
FROM final
