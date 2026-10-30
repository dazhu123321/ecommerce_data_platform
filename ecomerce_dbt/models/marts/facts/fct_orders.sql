
WITH order_items_aggregated AS (

    -- Aggregate order items to order level
    SELECT
        ORDER_ID,

        COUNT(ORDER_ITEM_ID) AS ITEM_COUNT,

        SUM(ITEM_SALE_AMOUNT) AS ORDER_SALES_AMOUNT,

        SUM(ESTIMATED_ITEM_COST) AS ORDER_ESTIMATED_COST,

        SUM(ESTIMATED_GROSS_PROFIT)
            AS ORDER_ESTIMATED_GROSS_PROFIT

    FROM {{ ref('fct_order_items') }}

    GROUP BY ORDER_ID

),

final AS (

    SELECT

        -- 1. Order Identifier
        o.ORDER_ID,

        -- 2. Dimension Keys
        u.USER_ID,
        d.DATE_KEY AS ORDER_DATE_KEY,

        -- 3. Order Information
        o.STATUS AS ORDER_STATUS,
        o.GENDER AS ORDER_GENDER,
        o.CREATED_AT AS ORDER_CREATED_AT,
        o.RETURNED_AT,
        o.SHIPPED_AT,
        o.DELIVERED_AT,

        -- 4. Order Metrics
        o.NUM_OF_ITEM,
        COALESCE(i.ITEM_COUNT, 0) AS ITEM_COUNT,

        -- 5. Sales Metrics
        COALESCE(i.ORDER_SALES_AMOUNT, 0)
            AS ORDER_SALES_AMOUNT,

        COALESCE(i.ORDER_ESTIMATED_COST, 0)
            AS ORDER_ESTIMATED_COST,

        COALESCE(i.ORDER_ESTIMATED_GROSS_PROFIT, 0)
            AS ORDER_ESTIMATED_GROSS_PROFIT

    FROM {{ ref('stg_orders') }} o

    LEFT JOIN order_items_aggregated i
        ON o.ORDER_ID = i.ORDER_ID

    LEFT JOIN {{ ref('dim_users') }} u
        ON o.USER_ID = u.USER_ID

    LEFT JOIN {{ ref('dim_date') }} d
        ON TO_DATE(o.CREATED_AT) = d.FULL_DATE

)

SELECT *
FROM final
