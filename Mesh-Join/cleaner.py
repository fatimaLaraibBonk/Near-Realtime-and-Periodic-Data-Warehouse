# now this takes the input file 
# and then cleans the data 
import pandas as pd
from pathlib import Path
import hashlib 
import connection 

def stable(text, n):
    hash_value = hashlib.md5(str(text).encode('utf-8')).hexdigest()[:8]
    return int(hash_value, 16) % n

def create_customer_master_data(customer_data):
    #stable(text, n) as md5 
    customer_data["gender"]=customer_data["customer_id"].apply(
    lambda x: "Male" if stable(str(x), 2) == 0 else "Female")
    age_groups=["0–17", "18–25", "26–35", "36–45", "46–50", "51–55", "55+"]
    customer_data["age_group"]=customer_data["customer_id"].apply(
        lambda x: age_groups[stable(str(x) + "age", 7)]
    )
    occupations=["Student", "Engineer", "Teacher", "Executive", "Clerk","Healthcare","Retail","Homemaker","Artist","Other"]
    customer_data["occupation"]=customer_data["customer_id"].apply(
        lambda x: occupations[stable(str(x)+"occ", 10)]
    )
    cities=["A","B","C"]
    customer_data["city_category"]=customer_data[["customer_id", "country"]].apply(
        lambda x: cities[stable(str(x["customer_id"]) + str(x["country"]), 3)],
        axis=1
    )
    #if more than one country appears for the same customer then we use the country on the first cleaned transaction 
    #basically this can be achieved by simply dropping the duplicates, the earlier ones are kept and later ones are removed
    years=["0","1","2","3","4+"]
    customer_data["stay_in_current_city_years"]=customer_data["customer_id"].apply(
        lambda x:years[stable(str(x)+"stay", 5)]
    )
    customer_data["marital_status"]=customer_data["customer_id"].apply(
    lambda x: "Single" if stable(str(x) + "mar", 2) == 0 else "Married")
    return customer_data

def create_product_master_data(product_data):

    #keep the longest product description, and if it is emoty we use unknown
    #we need that max for that product id 
    product_data["product_name"]=(
        product_data["product_name"]
        .fillna("")
        .replace("", pd.NA)
        .groupby(product_data["product_id"])
        .transform(lambda names: names.loc[names.str.len().idxmax()] if names.notna().any() else "UNKNOWN")
        .fillna("UNKNOWN")
    )
    #product category
    product_categories=["Home Decor", "Kitchen", "Stationery", "Toys", "Seasonal Gifts", "Bags", "Jewelry", "Garden", "Party", "Other"]
    product_data["product_category"]=product_data["product_id"].apply(
        lambda x: product_categories[stable(str(x)+"cat", 10)]
    )
    #cuppliers 
    #supplier id and supplier name 
    supplier_ids=["SUP01", "SUP02", "SUP03", "SUP04", "SUP05"]
    supplier_names=["Northwind Supplies", "Atlantic Gifts Ltd", "Midlands Wholesale", "Celtic Craft Co", "EuroPack Partners"]
    product_data["supplier_id"]=product_data["product_id"].apply(
        lambda x: supplier_ids[stable(str(x), 5)]
    )
    product_data["supplier_name"]=product_data["product_id"].apply(
        lambda x: supplier_names[stable(str(x), 5)]
    )
    return product_data

# does the main clean up job
def cleanup(data, log):
    
    # started working on data on 3 November 
    #this function already is getting the data 
    log.write("Now cleaning the data...")
    num_transactions_before=data.shape[0]

    # quantity must be greater than 0 
    data=data[data["Quantity"]>0]
    log.write("-> Quanity filtered out")
    # unit price must be greater than 0 
    data=data[data["UnitPrice"]>0]
    log.write("-> Unit price filtered out")
    # customer id must be present 
    data=data[data["CustomerID"].notna() & (data["CustomerID"] != "")]
    log.write("-> Customer id filtered out")
    # dropping cancellations, their trasaction id starts with a C 
    data["InvoiceNo"]=data["InvoiceNo"].astype(str)
    data=data[~data["InvoiceNo"].str.startswith("C", na=False)]
    log.write("-> Cancellations filtered out")
    num_transactions_after=data.shape[0]
    log.write(f"[bold blue]Number of transactions before cleaning: {num_transactions_before} [/bold blue]")
    log.write(f"[bold blue]Number of transactions after cleaning: {num_transactions_after} [/bold blue]")
    #dropping duplicates
    #data.drop_duplicates(subset=["transaction_id"])
    #mapping attributes 
    data=data.rename(columns={"InvoiceNo":"transaction_id", "StockCode":"product_id", "Description":"product_name", "Quantity":"quantity", "InvoiceDate":"event_time", "UnitPrice":"unit_price", "CustomerID":"customer_id", "Country":"country"})
    log.write("Attributes mapped")
    log.write("Now generating respective sales and master data..")
    return data


# separates data into periodic and online stream 
def partition(data, log, host, port, username, password):


    data["sales_mode"] = data["transaction_id"].apply(
    lambda x:"Online" if int(hashlib.md5(x.encode('utf-8')).hexdigest()[:8], 16) % 10 in range(7) else "Periodic")    
    full_data=data
    periodic_sales=data[data["sales_mode"]=="Periodic"][["transaction_id", "customer_id", "product_id","quantity","unit_price","event_time","sales_mode"]]
    online_sales=data[data["sales_mode"]=="Online"][["transaction_id", "customer_id", "product_id","quantity","unit_price","event_time","sales_mode"]]
    log.write(f"[black]Online sales: {online_sales.shape[0]}[/black]")
    log.write(f"[black]Periodic sales: {periodic_sales.shape[0]}[/black]")    

    # the online one stays in a csv
    #online_sales_stream.csv which has a control rate for the flow in its threads
    #rwmoving a stupid decimal point issue 
    online_sales["customer_id"] = (
    online_sales["customer_id"].astype(str).str.replace(r"\.0$", "", regex=True))
    #switching to relative paths s     s                                       
    file_path_for_online=r"..\Data\online_sales_stream.csv"
    online_sales.to_csv(file_path_for_online, index=False)

    # the periodic one goes into a database
    # master data is also on disk so its in a database 
    # periodic_sales_data (staging table)
    # we need to also introduct the extra columns in periodic sales
    # we need a total of 48 groups
    rows_per_group=periodic_sales.shape[0]//48 
    start=0
    end=rows_per_group
    periodic_sales["release_hour"]=-1
    for i in range(0,48):
        try:
            if i==47:
                periodic_sales.loc[periodic_sales.index[start:], "release_hour"]=i
                break 
            periodic_sales.loc[periodic_sales.index[start:], "release_hour"]=i
            start=end
            end=start+rows_per_group
            #log.write(f"[green]Group {i} prcoessed properly [/green]")
        except Exception as e:
            log.write(f"[red]Group {i} encountered an exception {e} [/red]")

    periodic_sales["released"]=0
    periodic_sales["customer_id"] = (
    periodic_sales["customer_id"].astype(str).str.replace(r"\.0$", "", regex=True))
    #basically my plan is that we make the database here 
    #add the necessary tables here 
    database="dw_retail_fatima"
    db_connection=connection.connect(host, username, password, database, log)
    if db_connection==0:
        log.write(f"[red]Could not connect to database")
        return -1
    if db_connection.is_connected():
        #create table 
        query="drop table if exists periodic_sales_data"
        cursor=db_connection.cursor()
        cursor.execute(query)
        query="create table if not exists periodic_sales_data (" \
        "transaction_id varchar(255)," \
        "customer_id varchar(255), " \
        "product_id text, " \
        "quantity int, " \
        "unit_price float, " \
        "event_time timestamp, " \
        "sales_mode text, " \
        "release_hour int, " \
        "released int default 0);"
        #then we will make our staging table 
        cursor.execute(query)
        log.write(f"[blue]Staging table for periodic sales created![/blue]")
        #issue 1: duplicate entries for transaction id 
        #now we insert the data 
        data=list(periodic_sales.itertuples(index=False, name=None))
        query=""" insert into periodic_sales_data (transaction_id, customer_id, product_id, quantity, unit_price, event_time, sales_mode, release_hour, released)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.executemany(query, data)
        db_connection.commit()
        connection.end_connection(db_connection, log, cursor)

    # staging table has a released flag so same group is NOT extracted twice 
    # and then we also have to flag each trasaction of this data as "Periodic"
    db_connection=connection.connect(host, username, password, database, log)
    if db_connection.is_connected():
        full_data["customer_id"]=(full_data["customer_id"].astype(str).str.replace(r"\.0$", "", regex=True))
        customer_data=full_data[["customer_id", "country"]]
        customer_data=pd.DataFrame(customer_data)
        customer_data=full_data[["customer_id", "country", "event_time"]].sort_values("event_time", kind="stable") 
        customer_data=customer_data.drop_duplicates(subset=["customer_id"])[["customer_id", "country"]]                  
        customer_master_data=create_customer_master_data(customer_data)
        log.write(f"[orange]Now working on master tables[/orange]")
        query="drop table if exists customer_master_data"
        cursor=db_connection.cursor()
        cursor.execute(query)
        query="drop table if exists product_master_data"
        cursor.execute(query)
        query="create table if not exists customer_master_data (" \
        "customer_id varchar(255) primary key," \
        "gender varchar(255)," \
        "age_group varchar(255)," \
        "occupation varchar(255)," \
        "city_category varchar(255)," \
        "stay_in_current_city_years varchar (255)," \
        "marital_status varchar(255));"
        cursor.execute(query)
        query="""insert into customer_master_data (customer_id, gender, age_group, occupation, city_category, stay_in_current_city_years, marital_status)
        values (%s,%s,%s,%s,%s,%s,%s);"""
        #log.write(f"[black]{customer_data.columns}[/black]")
        customer_master_data=customer_master_data.drop(columns="country")
        data=list(customer_master_data.itertuples(index=False, name=None))
        cursor.executemany(query,data)
        db_connection.commit()
        file_path_for_online=r"..\Data\customer_master_data.csv"
        customer_master_data.to_csv(file_path_for_online, index=False)

        #now we need to deal with product data 
        product_data=full_data[["product_id", "product_name"]]
        #product_data=product_data.drop_duplicates(subset=["product_id"])
        product_data=pd.DataFrame(create_product_master_data(product_data))
        #now for the product_master_data 
        query="create table if not exists product_master_data (" \
        "product_id varchar(255) primary key," \
        "product_name varchar(255)," \
        "product_category varchar(255)," \
        "supplier_id varchar(255)," \
        "supplier_name varchar(255));"
        cursor.execute(query)
        product_data=product_data.drop_duplicates(subset=["product_id"])
        query="""
            insert into product_master_data(
            product_id, product_name, product_category, supplier_id, supplier_name)
            values (%s, %s, %s, %s, %s);
        """
        data=list(product_data.itertuples(index=False, name=None)) 
        #log.write(f"[black]{product_data.columns}[/black]")
        cursor.executemany(query, data)
        db_connection.commit()
        connection.end_connection(db_connection, log, cursor)
        file_path_for_online=r"..\Data\product_master_data.csv"
        product_data.to_csv(file_path_for_online, index=False)
    # master data -> two tables both on disk and read onto memory
    log.write(f"[green]Master tables created successfully.[/green]")


# now that we have the necessary paritions of data 
# we will now use threads to feed that data into mesh join then go to our data warehouse 


#checking the problrem for invoice 
#path=Path(r"C:\Users\dani\Documents\Studies\Data Warehouse\Project\Data\Online Retail.xlsx")
#data=pd.read_excel(path)
#print(data.head(5))
#print(data["InvoiceNo"])