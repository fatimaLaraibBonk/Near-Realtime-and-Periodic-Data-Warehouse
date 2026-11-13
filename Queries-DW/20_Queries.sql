use dw_retail_fatima;

#checking what dates got loaded, data goes from dec 2010 to 9 dec 2011
select 'date check' as query_no, min(full_date) as first_loaded_date, max(full_date) as last_loaded_date from dim_time;


-- q1. top 5 products by revenue on weekdays and weekends, with monthly breakdown
-- loaded year 2011
-- first version scanned fact_sales twice and kept timing out
-- so now monthly totals are worked out once and the yearly total comes from those
with monthly as (
    select t.weekday_weekend, f.product_id, t.month,
           sum(f.revenue) as monthly_revenue
    from fact_sales f
    join dim_time t on t.time_key = f.time_key
    where t.year = 2011
    group by t.weekday_weekend, f.product_id, t.month
),
totals as (
    select weekday_weekend, product_id,
           sum(monthly_revenue) as total_revenue
    from monthly
    group by weekday_weekend, product_id
),
ranked as (
    select weekday_weekend, product_id, total_revenue,
           row_number() over (partition by weekday_weekend
                              order by total_revenue desc, product_id) as rnk
    from totals
)
select 'query 1' as query_no, r.weekday_weekend, r.rnk, r.product_id, p.product_name,
       m.month, m.monthly_revenue, r.total_revenue
from ranked r
join monthly m on m.weekday_weekend = r.weekday_weekend
              and m.product_id = r.product_id
join dim_product p on p.product_id = r.product_id
where r.rnk <= 5
order by r.weekday_weekend, r.rnk, m.month;


-- q2. total purchase amount by gender and age group, split by city category
-- all loaded data
select 'query 2' as query_no, c.gender, c.age_group, c.city_category,
       sum(f.revenue) as total_purchase_amount
from fact_sales f
join dim_customer c on c.customer_id = f.customer_id
group by c.gender, c.age_group, c.city_category
order by c.gender, c.age_group, c.city_category;


-- q3. total sales of each product category by customer occupation
-- all loaded data
select 'query 3' as query_no, p.product_category, c.occupation,
       sum(f.revenue) as total_sales
from fact_sales f
join dim_product p on p.product_id = f.product_id
join dim_customer c on c.customer_id = f.customer_id
group by p.product_category, c.occupation
order by p.product_category, total_sales desc;


-- q4. total purchases by gender and age group with quarterly trend
-- loaded year 2011, quarters 1 to 4
select 'query 4' as query_no, c.gender, c.age_group, t.year, t.quarter,
       sum(f.revenue) as total_purchase_amount
from fact_sales f
join dim_customer c on c.customer_id = f.customer_id
join dim_time t on t.time_key = f.time_key
where t.year = 2011
group by c.gender, c.age_group, t.year, t.quarter
order by c.gender, c.age_group, t.quarter;


-- q5. top 5 occupations by sales in each product category
-- all loaded data. row_number gives exactly 5 per category, use rank() instead if ties should stay
with occ_sales as (
    select p.product_category, c.occupation, sum(f.revenue) as total_sales
    from fact_sales f
    join dim_product p on p.product_id = f.product_id
    join dim_customer c on c.customer_id = f.customer_id
    group by p.product_category, c.occupation
),
ranked as (
    select product_category, occupation, total_sales,
           row_number() over (partition by product_category
                              order by total_sales desc, occupation) as rnk
    from occ_sales
)
select 'query 5' as query_no, product_category, rnk, occupation, total_sales
from ranked
where rnk <= 5
order by product_category, rnk;

#------------------------------------------------------------------------------------------------------------------------

-- q6. city category and marital status, monthly, for the last six months in the dw
-- latest date is taken from the data so nothing is hardcoded
-- data ends 2011-12-09 so this gives 2011-07 to 2011-12, december is only partly there
select 'query 6' as query_no, t.year, t.month, c.city_category, c.marital_status,
       sum(f.revenue) as total_purchase_amount
from fact_sales f
join dim_customer c on c.customer_id = f.customer_id
join dim_time t on t.time_key = f.time_key
where t.full_date >= date_sub(
        date_format((select max(t2.full_date)
                     from fact_sales f2
                     join dim_time t2 on t2.time_key = f2.time_key), '%Y-%m-01'),
        interval 5 month)
group by t.year, t.month, c.city_category, c.marital_status
order by t.year, t.month, c.city_category, c.marital_status;


-- q7. average purchase amount by years stayed in current city and gender
-- all loaded data
-- avg_per_line is the average of one fact row (one product in a cart)
-- avg_per_cart is revenue / number of distinct carts
select 'query 7' as query_no, c.stay_in_current_city_years, c.gender,
       round(avg(f.revenue), 2) as avg_per_line,
       round(sum(f.revenue) / count(distinct f.transaction_id), 2) as avg_per_cart
from fact_sales f
join dim_customer c on c.customer_id = f.customer_id
group by c.stay_in_current_city_years, c.gender
order by c.stay_in_current_city_years, c.gender;


-- q8. city categories ranked by revenue inside each product category
-- city_category (a, b, c) is from dim_customer, not dim_store.city
select 'query 8' as query_no, product_category, city_category, total_revenue,
       rank() over (partition by product_category order by total_revenue desc) as city_rank
from (
    select p.product_category, c.city_category, sum(f.revenue) as total_revenue
    from fact_sales f
    join dim_product p on p.product_id = f.product_id
    join dim_customer c on c.customer_id = f.customer_id
    group by p.product_category, c.city_category
) x
order by product_category, city_rank;


-- q9. month over month sales growth % by product category
-- loaded year 2011. filtered before lag so jan 2011 has no previous month (null)
-- dec 2011 only goes to the 9th so expect a big drop there
with monthly as (
    select p.product_category, t.month, sum(f.revenue) as revenue
    from fact_sales f
    join dim_product p on p.product_id = f.product_id
    join dim_time t on t.time_key = f.time_key
    where t.year = 2011
    group by p.product_category, t.month
)
select 'query 9' as query_no, product_category, month, revenue,
       lag(revenue) over w as previous_month_revenue,
       round((revenue - lag(revenue) over w) / nullif(lag(revenue) over w, 0) * 100, 2) as growth_pct
from monthly
window w as (partition by product_category order by month)
order by product_category, month;


-- q10. weekend vs weekday sales by age group
-- loaded year 2011
select 'query 10' as query_no, c.age_group,
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
-- loaded year 2011. different from q1, here the top 5 is picked inside each month + weekday/weekend group
with prod_month as (
    select t.month, t.weekday_weekend, f.product_id, sum(f.revenue) as revenue
    from fact_sales f
    join dim_time t on t.time_key = f.time_key
    where t.year = 2011
    group by t.month, t.weekday_weekend, f.product_id
),
ranked as (
    select month, weekday_weekend, product_id, revenue,
           row_number() over (partition by month, weekday_weekend
                              order by revenue desc, product_id) as rnk
    from prod_month
)
select 'query 11' as query_no, r.month, r.weekday_weekend, r.rnk, r.product_id, p.product_name, r.revenue
from ranked r
join dim_product p on p.product_id = r.product_id
where r.rnk <= 5
order by r.month, r.weekday_weekend, r.rnk;


-- q12. quarterly store revenue growth
-- loaded year 2011, q4 is partial. q1 has no previous quarter here so its null
with quarterly as (
    select s.store_id, s.store_name, t.quarter, sum(f.revenue) as revenue
    from fact_sales f
    join dim_store s on s.store_id = f.store_id
    join dim_time t on t.time_key = f.time_key
    where t.year = 2011
    group by s.store_id, s.store_name, t.quarter
)
select 'query 12' as query_no, store_name, quarter, revenue,
       lag(revenue) over w as previous_quarter_revenue,
       round((revenue - lag(revenue) over w) / nullif(lag(revenue) over w, 0) * 100, 2) as growth_pct
from quarterly
window w as (partition by store_id order by quarter)
order by store_name, quarter;


-- q13. supplier sales contribution by store and product name
-- all loaded data. contribution_pct is the share of that store's total revenue
-- product_id is in the group by too, otherwise two products with the same name get merged
select 'query 13' as query_no, s.store_name, su.supplier_name, p.product_name, p.product_id,
       sum(f.revenue) as revenue,
       round(sum(f.revenue) / sum(sum(f.revenue)) over (partition by s.store_id) * 100, 4) as contribution_pct
from fact_sales f
join dim_store s on s.store_id = f.store_id
join dim_supplier su on su.supplier_id = f.supplier_id
join dim_product p on p.product_id = f.product_id
group by s.store_id, s.store_name, su.supplier_id, su.supplier_name, p.product_id, p.product_name
order by s.store_name, su.supplier_name, p.product_name, p.product_id;


-- q14. seasonal sales for each product
-- all loaded data, dec 2010 to dec 2011. so winter has dec 2010, jan-feb 2011 and dec 2011
-- spring and fall are only 2011
select 'query 14' as query_no, p.product_id, p.product_name,
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


-- q15. monthly revenue volatility for each store and supplier pair (% change month to month)
-- loaded year 2011. jan 2011 has no previous month so its null
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
select 'query 15' as query_no, store_name, supplier_name, month, revenue,
       lag(revenue) over w as previous_month_revenue,
       round((revenue - lag(revenue) over w) / nullif(lag(revenue) over w, 0) * 100, 2) as volatility_pct
from monthly
window w as (partition by store_id, supplier_id order by month)
order by store_name, supplier_name, month;

#------------------------------------------------------------------------------------------------------------

-- q16. top 5 product pairs bought together, counting distinct carts
-- one cart = one transaction_id
-- index on fact_sales, only run this the first time
-- create index idx_fact_txn_prod on fact_sales (transaction_id, product_id);

#workbench cuts any single statement off at 30 sec and we cant change that
#limit 5 doesnt help, mysql still has to count every pair before it knows which 5 are on top
#so the pair counting is split into 4 smaller inserts, each one finishes on its own
#and the final select just reads a small table

#more memory for the group by so the temp table stays off disk
set session tmp_table_size = 268435456;
set session max_heap_table_size = 268435456;

#products have to be in at least this many carts to be kept
#a pair cant show up in more carts than either of its products, so this is safe
#as long as the 5th pair in the result is >= this number. if its lower, drop the number and rerun
set @min_carts = 150;

drop table if exists tmp_pair_counts, tmp_pair_items, tmp_txn_map, tmp_prod_map, tmp_cart_items;

#each product only once per cart, so count(*) on a pair later = number of distinct carts
#(a temporary table won't work here, mysql can't use it twice in the same query)
create table tmp_cart_items (
    transaction_id varchar(50) not null,
    product_id varchar(255) not null,
    primary key (transaction_id, product_id)
);

insert into tmp_cart_items (transaction_id, product_id)
select distinct transaction_id, product_id
from fact_sales;

#swapping the long varchar ids for ints, grouping on ints is a lot faster
#ordered by product_id so prod_no follows the same order as product_id
create table tmp_prod_map (
    prod_no int auto_increment primary key,
    product_id varchar(255) not null unique
);

insert into tmp_prod_map (product_id)
select product_id
from tmp_cart_items
group by product_id
having count(*) >= @min_carts
order by product_id;

create table tmp_txn_map (
    txn_no int auto_increment primary key,
    transaction_id varchar(50) not null unique
);

insert into tmp_txn_map (transaction_id)
select distinct c.transaction_id
from tmp_cart_items c
join tmp_prod_map pm on pm.product_id = c.product_id;

create table tmp_pair_items (
    txn_no int not null,
    prod_no int not null,
    primary key (txn_no, prod_no),
    key ix_prod_txn (prod_no, txn_no)
);

insert into tmp_pair_items (txn_no, prod_no)
select t.txn_no, pm.prod_no
from tmp_cart_items c
join tmp_prod_map pm on pm.product_id = c.product_id
join tmp_txn_map t on t.transaction_id = c.transaction_id;

#pair counts saved here, one row per pair
create table tmp_pair_counts (
    prod_a int not null,
    prod_b int not null,
    carts_together int not null,
    primary key (prod_a, prod_b)
);

#4 chunks split on the first product of the pair, so no pair gets counted twice
#if one of these still hits 30 sec, change 4 to 8 everywhere and add chunks 4 to 7
insert into tmp_pair_counts
select a.prod_no, b.prod_no, count(*)
from tmp_pair_items a
join tmp_pair_items b on b.txn_no = a.txn_no and b.prod_no > a.prod_no
where a.prod_no % 4 = 0
group by a.prod_no, b.prod_no;

insert into tmp_pair_counts
select a.prod_no, b.prod_no, count(*)
from tmp_pair_items a
join tmp_pair_items b on b.txn_no = a.txn_no and b.prod_no > a.prod_no
where a.prod_no % 4 = 1
group by a.prod_no, b.prod_no;

insert into tmp_pair_counts
select a.prod_no, b.prod_no, count(*)
from tmp_pair_items a
join tmp_pair_items b on b.txn_no = a.txn_no and b.prod_no > a.prod_no
where a.prod_no % 4 = 2
group by a.prod_no, b.prod_no;

insert into tmp_pair_counts
select a.prod_no, b.prod_no, count(*)
from tmp_pair_items a
join tmp_pair_items b on b.txn_no = a.txn_no and b.prod_no > a.prod_no
where a.prod_no % 4 = 3
group by a.prod_no, b.prod_no;

#top 5 from the saved counts, then join back to the real ids and names
select 'query 16' as query_no,
       ma.product_id as product_a, pa.product_name as product_a_name,
       mb.product_id as product_b, pb.product_name as product_b_name,
       pairs.carts_together
from (
    select prod_a, prod_b, carts_together
    from tmp_pair_counts
    order by carts_together desc, prod_a, prod_b
    limit 5
) pairs
join tmp_prod_map ma on ma.prod_no = pairs.prod_a
join tmp_prod_map mb on mb.prod_no = pairs.prod_b
join dim_product pa on pa.product_id = ma.product_id
join dim_product pb on pb.product_id = mb.product_id
order by pairs.carts_together desc, ma.product_id, mb.product_id;

#cleanup
drop table if exists tmp_pair_counts, tmp_pair_items, tmp_txn_map, tmp_prod_map, tmp_cart_items;


-- q17. yearly revenue by store, supplier and product with rollup
-- loaded year 2011. product_label has id + name so same name products dont get merged
-- grouping() is used to swap the rollup nulls with proper labels
select 'query 17' as query_no,
       case when grouping(store_name) = 1 then 'all stores' else store_name end as store,
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


-- q18. revenue and quantity by product for first half, second half and full year
-- loaded year 2011, second half stops at 9 december
select 'query 18' as query_no, p.product_id, p.product_name,
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
-- daily revenue per product, grouped on full_date since time_key is hourly
-- average is over the days the product actually sold on
-- all loaded data. spike = a day where revenue is more than 2x that product's daily average
-- the whole q19 block can be rerun as many times as needed, the view gets dropped and remade each time

#spikes saved as a view so q19 and the summary queries under it all use the same logic
drop view if exists q19_spikes;

create view q19_spikes as
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
select product_id, full_date, daily_revenue, avg_daily_revenue,
       daily_revenue / avg_daily_revenue as times_average
from with_avg
where daily_revenue > 2 * avg_daily_revenue;

#full list of spike days, this one goes in the appendix
select 'query 19' as query_no, s.product_id, p.product_name, s.full_date,
       round(s.daily_revenue, 2) as daily_revenue,
       round(s.avg_daily_revenue, 2) as avg_daily_revenue,
       round(s.times_average, 2) as times_average
from q19_spikes s
join dim_product p on p.product_id = s.product_id
order by s.times_average desc, s.product_id, s.full_date;

-- q19a. headline numbers for the report
select 'query 19a' as query_no,
       count(*) as spike_days,
       count(distinct product_id) as products_with_spikes,
       (select count(distinct product_id) from fact_sales) as products_sold
from q19_spikes;

-- q19b. how big the spikes are
select 'query 19b' as query_no,
       case when times_average < 3  then '2-3x'
            when times_average < 5  then '3-5x'
            when times_average < 10 then '5-10x'
            else '10x and up' end as spike_size,
       count(*) as spike_days,
       count(distinct product_id) as products
from q19_spikes
group by spike_size
order by min(times_average);

-- q19c. when the spikes happen, by month
-- december 2011 is partial, data stops on the 9th
select 'query 19c' as query_no,
       year(full_date) as year, month(full_date) as month,
       count(*) as spike_days
from q19_spikes
group by year(full_date), month(full_date)
order by year, month;

-- q19d. top 10 spikes and whether one order made the whole spike
-- biggest_cart_pct close to 100 means one customer order is basically the whole day
with top10 as (
    select product_id, full_date, daily_revenue, times_average
    from q19_spikes
    order by times_average desc, product_id
    limit 10
),
carts as (
    select f.product_id, t.full_date, f.transaction_id, sum(f.revenue) as cart_revenue
    from fact_sales f
    join dim_time t on t.time_key = f.time_key
    group by f.product_id, t.full_date, f.transaction_id
)
select 'query 19d' as query_no, s.product_id, p.product_name, s.full_date,
       round(s.daily_revenue, 2) as daily_revenue,
       round(s.times_average, 2) as times_average,
       count(*) as carts_that_day,
       round(max(c.cart_revenue) / s.daily_revenue * 100, 1) as biggest_cart_pct
from top10 s
join carts c on c.product_id = s.product_id and c.full_date = s.full_date
join dim_product p on p.product_id = s.product_id
group by s.product_id, p.product_name, s.full_date, s.daily_revenue, s.times_average
order by s.times_average desc, s.product_id;


-- q20. view STORE_QUARTERLY_SALES
-- year is in there too, otherwise q4 2010 and q4 2011 get added together
drop view if exists STORE_QUARTERLY_SALES;

create view STORE_QUARTERLY_SALES as
select s.store_id, s.store_name, t.year, t.quarter,
       sum(f.revenue) as total_quarterly_sales
from fact_sales f
join dim_store s on s.store_id = f.store_id
join dim_time t on t.time_key = f.time_key
group by s.store_id, s.store_name, t.year, t.quarter;

#mysql ignores order by inside create view so ordering goes here
select 'query 20' as query_no, v.* from STORE_QUARTERLY_SALES v
order by store_name, year, quarter;