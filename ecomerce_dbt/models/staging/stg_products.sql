
SELECT
    ID AS PRODUCT_ID,
    NAME,
    CATEGORY,
    BRAND,
    DEPARTMENT,
    COST,
    RETAIL_PRICE,
    SKU,
    DISTRIBUTION_CENTER_ID

FROM {{ source('thelook', 'products') }}
