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

FROM {{ source('thelook', 'users') }}