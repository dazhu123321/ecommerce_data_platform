
    
    

select
    ORDER_ID as unique_field,
    count(*) as n_records

from ECOM_RAW.ANALYTICS_DEV.fct_orders
where ORDER_ID is not null
group by ORDER_ID
having count(*) > 1


