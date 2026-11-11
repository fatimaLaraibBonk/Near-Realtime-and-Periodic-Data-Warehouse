#we can run this before and after the work on periodic data and master data 
create database if not exists dw_retail_fatima;
use dw_retail_fatima;

#checking for sales 
select * from periodic_sales_data;
select release_hour, count(*) from periodic_sales_data group by release_hour;

#checking for customers 
select * from customer_master_data;
select gender from customer_master_data group by gender;
select marital_status from customer_master_data group by marital_status;
select age_group from customer_master_data group by age_group;
select occupation from customer_master_data group by occupation;
select city_category from customer_master_data group by city_category;
select stay_in_current_city_years from customer_master_data group by stay_in_current_city_years;
 
#checking for products
select * from product_master_data;

#checking shedding table
select * from shedding_table;

select * from fact_sales;
select * from dim_store;
select * from dim_customer;
select * from dim_product;