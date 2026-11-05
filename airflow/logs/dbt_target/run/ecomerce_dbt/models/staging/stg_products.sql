
  create or replace   view ECOM_RAW.ANALYTICS_DEV.stg_products
  
  
  
  
  as (
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

FROM ECOM_RAW.THELOOK.PRODUCTS
  );

