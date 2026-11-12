use dw_retail_fatima;

select min(full_date) as first_loaded_date, max(full_date) as last_loaded_date from dim_time;

-- q1 
with prod_rev as (
    select t.weekday_weekend, f.product_id, sum(f.revenue) as total_revenue
    from fact_sales f
    join dim_time t on t.time_key = f.time_key
    where t.year = 2011
    group by t.weekday_weekend, f.product_id
),
ranked as (
    select weekday_weekend, product_id, total_revenue,
           row_number() over (partition by weekday_weekend order by total_revenue desc) as rnk
    from prod_rev
),
top5 as (
    select * from ranked where rnk <= 5
)
select r.weekday_weekend, r.rnk, p.product_id, p.product_name, t.month,
       sum(f.revenue) as monthly_revenue
from top5 r
join fact_sales f on f.product_id = r.product_id
join dim_time t on t.time_key = f.time_key
                and t.weekday_weekend = r.weekday_weekend
                and t.year = 2011
join dim_product p on p.product_id = r.product_id
group by r.weekday_weekend, r.rnk, p.product_id, p.product_name, t.month
order by r.weekday_weekend, r.rnk, t.month;


-- q2
select c.gender, c.age_group, c.city_category,
       sum(f.revenue) as total_purchase_amount
from fact_sales f
join dim_customer c on c.customer_id = f.customer_id
group by c.gender, c.age_group, c.city_category
order by c.gender, c.age_group, c.city_category;


-- q3. total sales of each product category by customer occupation
-- all loaded data
select p.product_category, c.occupation,
       sum(f.revenue) as total_sales
from fact_sales f
join dim_product p on p.product_id = f.product_id
join dim_customer c on c.customer_id = f.customer_id
group by p.product_category, c.occupation
order by p.product_category, total_sales desc;


-- q4. total purchases by gender and age group with quarterly trend
-- loaded year 2011 (quarters 1 to 4)
select c.gender, c.age_group, t.year, t.quarter,
       sum(f.revenue) as total_purchase_amount
from fact_sales f
join dim_customer c on c.customer_id = f.customer_id
join dim_time t on t.time_key = f.time_key
where t.year = 2011
group by c.gender, c.age_group, t.year, t.quarter
order by c.gender, c.age_group, t.quarter;


-- q5. top 5 occupations by sales within each product category
-- all loaded data. row_number gives exactly 5 per category; swap to rank() to keep ties.
with occ_sales as (
    select p.product_category, c.occupation, sum(f.revenue) as total_sales
    from fact_sales f
    join dim_product p on p.product_id = f.product_id
    join dim_customer c on c.customer_id = f.customer_id
    group by p.product_category, c.occupation
),
ranked as (
    select product_category, occupation, total_sales,
           row_number() over (partition by product_category order by total_sales desc) as rnk
    from occ_sales
)
select product_category, rnk, occupation, total_sales
from ranked
where rnk <= 5
order by product_category, rnk;

#------------------------------------------------------------------------------------------------------------------------

-- q6. city category performance by marital status, monthly, latest six months in the dw
-- latest loaded date is found from the data, no hardcoded dates.
-- with data ending 2011-12-09 this covers 2011-07 to 2011-12 (december is partial).
select t.year, t.month, c.city_category, c.marital_status,
       sum(f.revenue) as total_purchase_amount
from fact_sales f
join dim_customer c on c.customer_id = f.customer_id
join dim_time t on t.time_key = f.time_key
where t.full_date >= date_sub(
        date_format((select max(t2.full_date)
                     from fact_sales f2
                     join dim_time t2 on t2.time_key = f2.time_key), '%y-%m-01'),
        interval 5 month)
group by t.year, t.month, c.city_category, c.marital_status
order by t.year, t.month, c.city_category, c.marital_status;


-- q7. average purchase amount by years stayed in current city and gender
-- all loaded data. avg_per_line = average per fact row (one product in one cart).
-- avg_per_cart = revenue divided by distinct shopping carts. both shown, pick one for the report.
select c.stay_in_current_city_years, c.gender,
       round(avg(f.revenue), 2) as avg_per_line,
       round(sum(f.revenue) / count(distinct f.transaction_id), 2) as avg_per_cart
from fact_sales f
join dim_customer c on c.customer_id = f.customer_id
group by c.stay_in_current_city_years, c.gender
order by c.stay_in_current_city_years, c.gender;


-- q8. city categories ranked by revenue inside each product category
-- city_category (a, b, c) comes from dim_customer, not dim_store.city
select product_category, city_category, total_revenue,
       rank() over (partition by product_category order by total_revenue desc) as city_rank
from (
    select p.product_category, c.city_category, sum(f.revenue) as total_revenue
    from fact_sales f
    join dim_product p on p.product_id = f.product_id
    join dim_customer c on c.customer_id = f.customer_id
    group by p.product_category, c.city_category
) x
order by product_category, city_rank;


-- q9. month-over-month sales growth percentage by product category
-- loaded year 2011. filtered before lag, so january 2011 has no previous month (null).
with monthly as (
    select p.product_category, t.month, sum(f.revenue) as revenue
    from fact_sales f
    join dim_product p on p.product_id = f.product_id
    join dim_time t on t.time_key = f.time_key
    where t.year = 2011
    group by p.product_category, t.month
)
select product_category, month, revenue,
       lag(revenue) over w as previous_month_revenue,
       round((revenue - lag(revenue) over w) / nullif(lag(revenue) over w, 0) * 100, 2) as growth_pct
from monthly
window w as (partition by product_category order by month)
order by product_category, month;


-- q10. weekend vs weekday sales by age group
-- loaded year 2011
select c.age_group,
       sum(case when t.weekday_weekend = 'Weekday' then f.revenue else 0 end) as weekday_sales,
       sum(case when t.weekday_weekend = 'Weekend' then f.revenue else 0 end) as weekend_sales,
       sum(f.revenue) as total_sales
from fact_sales f
join dim_customer c on c.customer_id = f.customer_id
join dim_time t on t.time_key = f.time_key
where t.year = 2011
group by c.age_group
order by c.age_group;

#----------------------------------------------------------------------------------------------------------

-- q11. top 5 products by revenue on weekdays and weekends, grouped by month
-- loaded year 2011. top 5 is picked inside each month and weekday/weekend group.
with prod_month as (
    select t.month, t.weekday_weekend, f.product_id, sum(f.revenue) as revenue
    from fact_sales f
    join dim_time t on t.time_key = f.time_key
    where t.year = 2011
    group by t.month, t.weekday_weekend, f.product_id
),
ranked as (
    select month, weekday_weekend, product_id, revenue,
           row_number() over (partition by month, weekday_weekend order by revenue desc) as rnk
    from prod_month
)
select r.month, r.weekday_weekend, r.rnk, r.product_id, p.product_name, r.revenue
from ranked r
join dim_product p on p.product_id = r.product_id
where r.rnk <= 5
order by r.month, r.weekday_weekend, r.rnk;


-- q12. quarterly store revenue growth
-- loaded year 2011 (q4 2011 is partial). q1 2011 has no previous quarter in the filtered data (null).
with quarterly as (
    select s.store_id, s.store_name, t.quarter, sum(f.revenue) as revenue
    from fact_sales f
    join dim_store s on s.store_id = f.store_id
    join dim_time t on t.time_key = f.time_key
    where t.year = 2011
    group by s.store_id, s.store_name, t.quarter
)
select store_name, quarter, revenue,
       lag(revenue) over w as previous_quarter_revenue,
       round((revenue - lag(revenue) over w) / nullif(lag(revenue) over w, 0) * 100, 2) as growth_pct
from quarterly
window w as (partition by store_id order by quarter)
order by store_name, quarter;


-- q13. supplier sales contribution by store and product name
-- all loaded data. contribution_pct = share of the store's total revenue.
-- product_id is in the group by so different products with the same name are not merged.
select s.store_name, su.supplier_name, p.product_name, p.product_id,
       sum(f.revenue) as revenue,
       round(sum(f.revenue) / sum(sum(f.revenue)) over (partition by s.store_id) * 100, 4) as contribution_pct
from fact_sales f
join dim_store s on s.store_id = f.store_id
join dim_supplier su on su.supplier_id = f.supplier_id
join dim_product p on p.product_id = f.product_id
group by s.store_id, s.store_name, su.supplier_id, su.supplier_name, p.product_id, p.product_name
order by s.store_name, su.supplier_name, p.product_name, p.product_id;


-- q14. seasonal analysis of product sales
-- all loaded data (dec 2010 to dec 2011). winter therefore includes dec 2010, jan-feb 2011 and dec 2011.
-- spring and fall only cover 2011.
select p.product_id, p.product_name,
       sum(case when t.season = 'Spring' then f.revenue else 0 end) as spring_sales,
       sum(case when t.season = 'Summer' then f.revenue else 0 end) as summer_sales,
       sum(case when t.season = 'Fall'   then f.revenue else 0 end) as fall_sales,
       sum(case when t.season = 'Winter' then f.revenue else 0 end) as winter_sales,
       sum(f.revenue) as total_sales
from fact_sales f
join dim_product p on p.product_id = f.product_id
join dim_time t on t.time_key = f.time_key
group by p.product_id, p.product_name
order by total_sales desc;


-- q15. store and supplier monthly revenue volatility (% change month to month)
-- loaded year 2011. january 2011 has no previous month (null).
with monthly as (
    select s.store_id, s.store_name, su.supplier_id, su.supplier_name, t.month,
           sum(f.revenue) as revenue
    from fact_sales f
    join dim_store s on s.store_id = f.store_id
    join dim_supplier su on su.supplier_id = f.supplier_id
    join dim_time t on t.time_key = f.time_key
    where t.year = 2011
    group by s.store_id, s.store_name, su.supplier_id, su.supplier_name, t.month
)
select store_name, supplier_name, month, revenue,
       lag(revenue) over w as previous_month_revenue,
       round((revenue - lag(revenue) over w) / nullif(lag(revenue) over w, 0) * 100, 2) as volatility_pct
from monthly
window w as (partition by store_id, supplier_id order by month)
order by store_name, supplier_name, month;

#------------------------------------------------------------------------------------------------------------
-- q16 
select count(*) as carts, max(n) as biggest_cart, sum(n * (n - 1) / 2) as estimated_pairs
from (select transaction_id, count(*) as n
      from tmp_cart_items
      group by transaction_id) x; 
      
drop table if exists frequent_products;
create table frequent_products (product_id varchar(255) primary key);
insert into frequent_products
select product_id from tmp_cart_items
group by product_id
having count(*) >= 30;

drop table if exists tmp_cart_items_f;
create table tmp_cart_items_f (
    transaction_id varchar(50) not null,
    product_id varchar(255) not null,
    primary key (transaction_id, product_id)
);
insert into tmp_cart_items_f
select c.transaction_id, c.product_id
from tmp_cart_items c
join frequent_products fp on fp.product_id = c.product_id;

-- step 1: index on the fact table (skip if already created)
create index idx_fact_txn_prod on fact_sales (transaction_id, product_id);

-- step 2: real helper table with a key, so the self-join is an indexed lookup
-- (a temporary table won't work, mysql can't reference one twice in the same query)
drop table if exists tmp_cart_items;

create table tmp_cart_items (
    transaction_id varchar(50) not null,
    product_id varchar(255) not null,
    primary key (transaction_id, product_id)
);

insert into tmp_cart_items (transaction_id, product_id)
select distinct transaction_id, product_id
from fact_sales;

-- step 3: pair counting on ids only, limit before joining names
select pairs.product_a, pa.product_name as product_a_name,
       pairs.product_b, pb.product_name as product_b_name,
       pairs.carts_together
from (
    select a.product_id as product_a, b.product_id as product_b,
           count(*) as carts_together
    from tmp_cart_items a
    join tmp_cart_items b on b.transaction_id = a.transaction_id
                          and b.product_id > a.product_id
    group by a.product_id, b.product_id
    order by carts_together desc
    limit 5
) pairs
join dim_product pa on pa.product_id = pairs.product_a
join dim_product pb on pb.product_id = pairs.product_b
order by pairs.carts_together desc;

-- step 4: clean up
drop table if exists tmp_cart_items;

-- q17. yearly revenue by store, supplier and product with rollup
-- loaded year 2011. product_label keeps id + name so same-name products are not merged.
-- null in the output is replaced with labels using grouping().
select case when grouping(store_name) = 1 then 'all stores' else store_name end as store,
       case when grouping(supplier_name) = 1 then 'all suppliers' else supplier_name end as supplier,
       case when grouping(product_label) = 1 then 'all products' else product_label end as product,
       sum(revenue) as yearly_revenue
from (
    select s.store_name, su.supplier_name,
           concat(p.product_id, ' - ', p.product_name) as product_label,
           f.revenue
    from fact_sales f
    join dim_store s on s.store_id = f.store_id
    join dim_supplier su on su.supplier_id = f.supplier_id
    join dim_product p on p.product_id = f.product_id
    join dim_time t on t.time_key = f.time_key
    where t.year = 2011
) x
group by store_name, supplier_name, product_label with rollup
order by grouping(store_name), store_name, grouping(supplier_name), supplier_name,
         grouping(product_label), product_label;


-- q18. revenue and volume by product for first half, second half and full year
-- loaded year 2011 (second half ends 9 december)
select p.product_id, p.product_name,
       sum(case when t.half_year = 1 then f.quantity else 0 end) as h1_quantity,
       sum(case when t.half_year = 1 then f.revenue  else 0 end) as h1_revenue,
       sum(case when t.half_year = 2 then f.quantity else 0 end) as h2_quantity,
       sum(case when t.half_year = 2 then f.revenue  else 0 end) as h2_revenue,
       sum(f.quantity) as full_year_quantity,
       sum(f.revenue) as full_year_revenue
from fact_sales f
join dim_product p on p.product_id = f.product_id
join dim_time t on t.time_key = f.time_key
where t.year = 2011
group by p.product_id, p.product_name
order by full_year_revenue desc;


-- q19. high revenue spikes
-- daily revenue per product (grouped by full_date, not the hourly time_key).
-- the average is taken over the days on which the product actually sold.
-- all loaded data. returns days where revenue > 2 x the product's own daily average.
with daily as (
    select f.product_id, t.full_date, sum(f.revenue) as daily_revenue
    from fact_sales f
    join dim_time t on t.time_key = f.time_key
    group by f.product_id, t.full_date
),
with_avg as (
    select product_id, full_date, daily_revenue,
           avg(daily_revenue) over (partition by product_id) as avg_daily_revenue
    from daily
)
select w.product_id, p.product_name, w.full_date, w.daily_revenue,
       round(w.avg_daily_revenue, 2) as avg_daily_revenue,
       round(w.daily_revenue / w.avg_daily_revenue, 2) as times_average
from with_avg w
join dim_product p on p.product_id = w.product_id
where w.daily_revenue > 2 * w.avg_daily_revenue
order by times_average desc, w.product_id, w.full_date;


-- q20. view store_quarterly_sales
-- year is included so q4 2010 and q4 2011 are not merged
drop view if exists store_quarterly_sales;

create view store_quarterly_sales as
select s.store_id, s.store_name, t.year, t.quarter,
       sum(f.revenue) as total_quarterly_sales
from fact_sales f
join dim_store s on s.store_id = f.store_id
join dim_time t on t.time_key = f.time_key
group by s.store_id, s.store_name, t.year, t.quarter;

-- ordering goes on the select that reads the view (mysql ignores order by inside create view)
select * from store_quarterly_sales
order by store_name, year, quarter;

#-=--------------------------------------------------------------------------------------------------------------------------------------------------