
WITH RECURSIVE date_spine (date_day, max_date) AS (

    -- 1. Get the minimum and maximum order dates
    SELECT
        MIN(TO_DATE(CREATED_AT)),
        MAX(TO_DATE(CREATED_AT))

    FROM {{ ref('stg_orders') }}

    WHERE CREATED_AT IS NOT NULL

    UNION ALL

    -- 2. Generate consecutive calendar dates
    SELECT
        DATEADD(DAY, 1, date_day),
        max_date

    FROM date_spine

    WHERE date_day < max_date
)

-- 3. Build the date dimension
SELECT

    -- Date Identifier
    TO_NUMBER(TO_CHAR(date_day, 'YYYYMMDD')) AS DATE_KEY,

    -- Full Date
    date_day AS FULL_DATE,

    -- Year Information
    YEAR(date_day) AS YEAR,
    QUARTER(date_day) AS QUARTER,
    MONTH(date_day) AS MONTH,

    -- Month Information
    MONTHNAME(date_day) AS MONTH_NAME,

    -- Week Information
    WEEKISO(date_day) AS WEEK_OF_YEAR,
    DAYOFWEEKISO(date_day) AS DAY_OF_WEEK,

    -- Day Information
    DAY(date_day) AS DAY_OF_MONTH,
    DAYOFYEAR(date_day) AS DAY_OF_YEAR,
    DAYNAME(date_day) AS DAY_NAME,

    -- Weekend Indicator
    CASE
        WHEN DAYOFWEEKISO(date_day) IN (6, 7)
        THEN TRUE
        ELSE FALSE
    END AS IS_WEEKEND

FROM date_spine
