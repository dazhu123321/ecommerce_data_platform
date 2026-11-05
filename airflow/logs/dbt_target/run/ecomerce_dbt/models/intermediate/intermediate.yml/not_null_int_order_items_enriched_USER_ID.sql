
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select USER_ID
from ECOM_RAW.ANALYTICS_DEV.int_order_items_enriched
where USER_ID is null



  
  
      
    ) dbt_internal_test