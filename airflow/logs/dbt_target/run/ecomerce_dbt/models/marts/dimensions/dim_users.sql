
  
    

create or replace transient table ECOM_RAW.ANALYTICS_DEV.dim_users
    
    
    
    
    

    as (SELECT
    USER_ID,

    FIRST_NAME,
    LAST_NAME,
    EMAIL,

    AGE,
    GENDER,

    STATE,
    CITY,
    COUNTRY,
    STREET_ADDRESS,
    POSTAL_CODE,

    LATITUDE,
    LONGITUDE,

    TRAFFIC_SOURCE,
    CREATED_AT

FROM ECOM_RAW.ANALYTICS_DEV.stg_users
    )
;


  