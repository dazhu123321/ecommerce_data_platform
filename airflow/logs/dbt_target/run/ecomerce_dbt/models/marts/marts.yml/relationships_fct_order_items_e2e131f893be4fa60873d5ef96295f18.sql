
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with child as (
    select PRODUCT_ID as from_field
    from ECOM_RAW.ANALYTICS_DEV.fct_order_items
    where PRODUCT_ID is not null
),

parent as (
    select PRODUCT_ID as to_field
    from ECOM_RAW.ANALYTICS_DEV.dim_products
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



  
  
      
    ) dbt_internal_test