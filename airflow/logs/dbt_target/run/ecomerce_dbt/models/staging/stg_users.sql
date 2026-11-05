
  create or replace   view ECOM_RAW.ANALYTICS_DEV.stg_users
  
  
  
  
  as (
    SELECT
    ID AS USER_ID,
    FIRST_NAME,
    LAST_NAME,
    EMAIL,
    AGE,
    GENDER,
    STATE,
    STREET_ADDRESS,
    POSTAL_CODE,
    CITY,
    COUNTRY,
    LATITUDE,
    LONGITUDE,
    TRAFFIC_SOURCE,
    CREATED_AT,
    USER_GEOM

FROM ECOM_RAW.THELOOK.USERS
  );

