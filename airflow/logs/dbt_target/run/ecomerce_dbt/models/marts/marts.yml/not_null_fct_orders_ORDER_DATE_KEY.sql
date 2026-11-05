
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select ORDER_DATE_KEY
from ECOM_RAW.ANALYTICS_DEV.fct_orders
where ORDER_DATE_KEY is null



  
  
      
    ) dbt_internal_test