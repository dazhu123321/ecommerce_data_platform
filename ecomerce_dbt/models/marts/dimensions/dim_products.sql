
SELECT

    -- 1. Product Identifier
    PRODUCT_ID,

    -- 2. Product Information
    NAME AS PRODUCT_NAME,
    CATEGORY AS PRODUCT_CATEGORY,
    BRAND AS PRODUCT_BRAND,
    DEPARTMENT AS PRODUCT_DEPARTMENT,

    -- 3. Product Pricing
    COST AS PRODUCT_COST,
    RETAIL_PRICE AS PRODUCT_RETAIL_PRICE,

    -- 4. Product Identification
    SKU,

    -- 5. Distribution Information
    DISTRIBUTION_CENTER_ID

FROM {{ ref('stg_products') }}
