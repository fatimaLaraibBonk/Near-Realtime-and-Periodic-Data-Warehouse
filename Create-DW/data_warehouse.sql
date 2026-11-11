#for this project we are using star schema 
#i will use the same database from before
use dw_retail_fatima;

#drop tables and views in the start 
drop view if exists STORE_QUARTERLY_SALES;
drop table if exists fact_sales;
drop table if exists dim_customer;
drop table if exists dim_product;
drop table if exists dim_supplier;
drop table if exists dim_store;
drop table if exists dim_time;

#dimensions 
#customer
create table if not exists dim_customer(
    customer_id varchar(255) primary key,
    gender varchar(10),
    age_group varchar(10),
    occupation varchar(50),
    city_category varchar(10),
    stay_in_current_city_years varchar(10),
    marital_status varchar(10)
);
#product
create table if not exists dim_product(
    product_id varchar(255) primary key,
    product_name text, 
    product_category varchar(255)
);
#supplier
create table if not exists dim_supplier(
    supplier_id varchar(255) primary key, 
    supplier_name varchar(255)
);
#store location/where
create table if not exists dim_store(
    store_id varchar(10) primary key, 
    store_name varchar(255),
    city varchar(255)
);
#time when hour, date, the day of the month, the month, the quarter, the year, day of the week, weekday or weekened flag, the season and the half year 
#first half is january-june 
#july-december second half 
#time_key is yyyymmddhh so 2011031214 is 12 march 2011 at 2pm
create table if not exists dim_time(
    time_key bigint primary key,
    full_date date,
    hour tinyint,
    day_of_month tinyint,
    month tinyint,
    quarter tinyint,
    year smallint,
    day_of_week varchar(10),
    weekday_weekend varchar(10), #Weekday or Weekend
    season varchar(10), #spring march-may, summer june-aug, fall sep-nov, winter dec-feb
    half_year tinyint #1 is jan-june, 2 is july-dec
);
#facts
#one row is one transaction, measures plus the keys of the 5 dimensions
create table if not exists fact_sales(
    fact_id bigint auto_increment primary key,
    transaction_id varchar(50) not null,
    customer_id varchar(255) not null,
    product_id varchar(255) not null,
    supplier_id varchar(255) not null,
    store_id varchar(10) not null,
    time_key bigint not null,
    quantity int not null,
    revenue decimal(12,2) not null, #quantity x unit price, calculated in consolidation
    sales_mode varchar(10),
    processing_mode varchar(10),
    foreign key (customer_id) references dim_customer(customer_id),
    foreign key (product_id) references dim_product(product_id),
    foreign key (supplier_id) references dim_supplier(supplier_id),
    foreign key (store_id) references dim_store(store_id),
    foreign key (time_key) references dim_time(time_key)
);
#loading the smaller dimension tables 
insert into dim_store (store_id, store_name, city) values
('1','Online','Web'),
('2','London Bridge','London'),
('3','Manchester Arndale','Manchester'),
('4','Birmingham Bullring','Birmingham'),
('5','Edinburgh Princes','Edinburgh');

#the 5 suppliers from the spec, same shortcut as the stores
insert into dim_supplier (supplier_id, supplier_name) values
('SUP01','Northwind Supplies'),
('SUP02','Atlantic Gifts Ltd'),
('SUP03','Midlands Wholesale'),
('SUP04','Celtic Craft Co'),
('SUP05','EuroPack Partners');