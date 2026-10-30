
SELECT
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

FROM {{ ref('stg_users') }}
