
  create or replace   view ECOM_RAW.ANALYTICS_DEV.stg_orders
  
  
  
  
  as (
    SELECT
    ORDER_ID,
    USER_ID,
    STATUS,
    GENDER,
    CREATED_AT,
    RETURNED_AT,
    SHIPPED_AT,
    DELIVERED_AT,
    NUM_OF_ITEM

FROM ECOM_RAW.THELOOK.ORDERS
  );

