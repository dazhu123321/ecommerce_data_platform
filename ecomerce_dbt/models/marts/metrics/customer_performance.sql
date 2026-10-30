
WITH customer_orders AS (

    -- 1. Aggregate order metrics by customer
    SELECT

        USER_ID,

        COUNT(DISTINCT ORDER_ID)
            AS TOTAL_ORDERS,

        SUM(ORDER_SALES_AMOUNT)
            AS TOTAL_RECORDED_SALES,

        AVG(ORDER_SALES_AMOUNT)
            AS AVERAGE_ORDER_AMOUNT,

        MIN(TO_DATE(ORDER_CREATED_AT))
            AS FIRST_ORDER_DATE,

        MAX(TO_DATE(ORDER_CREATED_AT))
            AS LAST_ORDER_DATE

    FROM {{ ref('fct_orders') }}

    WHERE USER_ID IS NOT NULL

    GROUP BY USER_ID

),

final AS (

    -- 2. Combine customer profile and order metrics
    SELECT

        -- Customer Information
        u.USER_ID,

        u.FIRST_NAME,
        u.LAST_NAME,
        u.EMAIL,

        u.AGE,
        u.GENDER,

        u.STATE,
        u.CITY,
        u.COUNTRY,

        u.TRAFFIC_SOURCE,
        u.CREATED_AT AS USER_CREATED_AT,

        -- Customer Order Metrics
        COALESCE(o.TOTAL_ORDERS, 0)
            AS TOTAL_ORDERS,

        COALESCE(o.TOTAL_RECORDED_SALES, 0)
            AS TOTAL_RECORDED_SALES,

        o.AVERAGE_ORDER_AMOUNT,

        o.FIRST_ORDER_DATE,
        o.LAST_ORDER_DATE,

        -- Repeat Customer Flag
        CASE
            WHEN COALESCE(o.TOTAL_ORDERS, 0) >= 2
                THEN TRUE
            ELSE FALSE
        END AS IS_REPEAT_CUSTOMER,

        -- Customer Purchase Behavior
        CASE
            WHEN COALESCE(o.TOTAL_ORDERS, 0) = 0
                THEN 'NEVER_PURCHASED'

            WHEN o.TOTAL_ORDERS = 1
                THEN 'ONE_TIME_CUSTOMER'

            ELSE 'REPEAT_CUSTOMER'
        END AS CUSTOMER_SEGMENT

    FROM {{ ref('dim_users') }} u

    LEFT JOIN customer_orders o
        ON u.USER_ID = o.USER_ID

)

SELECT *
FROM final
