
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select ORDER_ID
from ECOM_RAW.ANALYTICS_DEV.int_order_items_enriched
where ORDER_ID is null



  
  
      
    ) dbt_internal_test