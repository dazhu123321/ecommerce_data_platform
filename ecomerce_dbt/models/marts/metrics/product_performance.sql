
WITH product_sales AS (

    -- 1. Aggregate sales metrics by product
    SELECT

        PRODUCT_ID,

        COUNT(DISTINCT ORDER_ITEM_ID)
            AS TOTAL_ORDER_ITEMS,

        SUM(ITEM_QUANTITY)
            AS TOTAL_UNITS_SOLD,

        COUNT(DISTINCT ORDER_ID)
            AS TOTAL_ORDERS,

        COUNT(DISTINCT USER_ID)
            AS TOTAL_CUSTOMERS,

        SUM(ITEM_SALE_AMOUNT)
            AS TOTAL_RECORDED_SALES,

        SUM(ESTIMATED_ITEM_COST)
            AS TOTAL_ESTIMATED_COST,

        SUM(ESTIMATED_GROSS_PROFIT)
            AS TOTAL_ESTIMATED_GROSS_PROFIT,

        AVG(ITEM_SALE_AMOUNT)
            AS AVERAGE_SELLING_PRICE

    FROM {{ ref('fct_order_items') }}

    GROUP BY PRODUCT_ID

),

final AS (

    -- 2. Combine product information with sales metrics
    SELECT

        -- Product Information
        p.PRODUCT_ID,
        p.PRODUCT_NAME,
        p.PRODUCT_CATEGORY,
        p.PRODUCT_BRAND,
        p.PRODUCT_DEPARTMENT,

        p.PRODUCT_COST,
        p.PRODUCT_RETAIL_PRICE,

        p.SKU,
        p.DISTRIBUTION_CENTER_ID,

        -- Sales Metrics
        COALESCE(s.TOTAL_ORDER_ITEMS, 0)
            AS TOTAL_ORDER_ITEMS,

        COALESCE(s.TOTAL_UNITS_SOLD, 0)
            AS TOTAL_UNITS_SOLD,

        COALESCE(s.TOTAL_ORDERS, 0)
            AS TOTAL_ORDERS,

        COALESCE(s.TOTAL_CUSTOMERS, 0)
            AS TOTAL_CUSTOMERS,

        COALESCE(s.TOTAL_RECORDED_SALES, 0)
            AS TOTAL_RECORDED_SALES,

        COALESCE(s.TOTAL_ESTIMATED_COST, 0)
            AS TOTAL_ESTIMATED_COST,

        COALESCE(s.TOTAL_ESTIMATED_GROSS_PROFIT, 0)
            AS TOTAL_ESTIMATED_GROSS_PROFIT,

        s.AVERAGE_SELLING_PRICE,

        -- Estimated Gross Profit Margin
        CASE
            WHEN COALESCE(s.TOTAL_RECORDED_SALES, 0) = 0
                THEN NULL

            ELSE
                s.TOTAL_ESTIMATED_GROSS_PROFIT
                / s.TOTAL_RECORDED_SALES * 100
        END AS ESTIMATED_GROSS_PROFIT_MARGIN_PCT

    FROM {{ ref('dim_products') }} p

    LEFT JOIN product_sales s
        ON p.PRODUCT_ID = s.PRODUCT_ID

)

SELECT *
FROM final
