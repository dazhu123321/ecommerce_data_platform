
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with child as (
    select ORDER_ID as from_field
    from ECOM_RAW.ANALYTICS_DEV.stg_order_items
    where ORDER_ID is not null
),

parent as (
    select ORDER_ID as to_field
    from ECOM_RAW.ANALYTICS_DEV.stg_orders
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



  
  
      
    ) dbt_internal_test