
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    ORDER_ITEM_ID as unique_field,
    count(*) as n_records

from ECOM_RAW.ANALYTICS_DEV.int_order_items_enriched
where ORDER_ITEM_ID is not null
group by ORDER_ITEM_ID
having count(*) > 1



  
  
      
    ) dbt_internal_test