
WITH order_items AS (

    SELECT *
    FROM {{ ref('int_order_items_enriched') }}

),

final AS (

    SELECT

        -- 1. Fact Table Identifiers
        oi.ORDER_ITEM_ID,
        oi.ORDER_ID,

        -- 2. Dimension Keys
        du.USER_ID,
        dp.PRODUCT_ID,
        dd.DATE_KEY AS ORDER_DATE_KEY,

        -- 3. Order Information
        oi.ORDER_STATUS,
        oi.ITEM_STATUS,
        oi.ORDER_CREATED_AT,

        -- 4. Product Information
        oi.PRODUCT_CATEGORY,
        oi.PRODUCT_BRAND,

        -- 5. Business Measures
        oi.SALE_PRICE AS ITEM_SALE_AMOUNT,
        oi.PRODUCT_COST AS ESTIMATED_ITEM_COST,

        1 AS ITEM_QUANTITY,

        -- 6. Estimated Gross Profit
        oi.SALE_PRICE - oi.PRODUCT_COST
            AS ESTIMATED_GROSS_PROFIT

    FROM order_items oi

    LEFT JOIN {{ ref('dim_users') }} du
        ON oi.USER_ID = du.USER_ID

    LEFT JOIN {{ ref('dim_products') }} dp
        ON oi.PRODUCT_ID = dp.PRODUCT_ID

    LEFT JOIN {{ ref('dim_date') }} dd
        ON TO_DATE(oi.ORDER_CREATED_AT) = dd.FULL_DATE

)

SELECT *
FROM final
