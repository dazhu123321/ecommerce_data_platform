
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select DATE_KEY
from ECOM_RAW.ANALYTICS_DEV.dim_date
where DATE_KEY is null



  
  
      
    ) dbt_internal_test