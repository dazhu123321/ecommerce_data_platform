
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with child as (
    select ORDER_DATE_KEY as from_field
    from ECOM_RAW.ANALYTICS_DEV.fct_order_items
    where ORDER_DATE_KEY is not null
),

parent as (
    select DATE_KEY as to_field
    from ECOM_RAW.ANALYTICS_DEV.dim_date
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



  
  
      
    ) dbt_internal_test