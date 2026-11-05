
  create or replace   view ECOM_RAW.ANALYTICS_DEV.stg_order_items
  
  
  
  
  as (
    SELECT
    ID AS ORDER_ITEM_ID,
    ORDER_ID,
    USER_ID,
    PRODUCT_ID,
    INVENTORY_ITEM_ID,
    STATUS,
    CREATED_AT,
    SHIPPED_AT,
    DELIVERED_AT,
    RETURNED_AT,
    SALE_PRICE

FROM ECOM_RAW.THELOOK.ORDER_ITEMS
  );

