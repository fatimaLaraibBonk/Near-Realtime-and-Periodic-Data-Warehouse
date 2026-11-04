# now this takes the input file 
# and then cleans the data 
import pandas as pd
from pathlib import Path
import hashlib 
import connection 

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
    
    #mapping attributes 
    data=data.rename(columns={"InvoiceNo":"transaction_id", "StockCode":"product_id", "Description":"product_name", "Quantity":"quantity", "InvoiceDate":"event_time", "UnitPrice":"unit_price", "CustomerID":"customer_id", "Country":"country"})
    log.write("Attributes mapped")
    log.write("Now generating respective sales and master data..")
    return data


# separates data into periodic and online stream 
def partition(data, log):


    data["sales_mode"] = data["transaction_id"].apply(
    lambda x:"Online" if int(hashlib.md5(x.encode('utf-8')).hexdigest()[:8], 16) % 10 in range(7) else "Periodic")    
    periodic_sales=data[data["sales_mode"]=="Periodic"][["transaction_id", "customer_id", "product_id","quantity","unit_price","event_time","sales_mode"]]
    online_sales=data[data["sales_mode"]=="Online"][["transaction_id", "customer_id", "product_id","quantity","unit_price","event_time","sales_mode"]]
    log.write(f"[black]Online sales: {online_sales.shape[0]}[/black]")
    log.write(f"[black]Periodic sales: {periodic_sales.shape[0]}[/black]")    

    # the online one stays in a csv
    #online_sales_stream.csv which has a control rate for the flow in its threads
    file_path_for_online=r"C:\Users\dani\Documents\Studies\Data Warehouse\Project\Data\online_sales_stream.csv"
    online_sales.to_csv(file_path_for_online, index=False)

    # the periodic one goes into a database
    # master data is also on disk so its in a database 
    # periodic_sales_data (staging table)
    
    # staging table has a released flag so same group is NOT extracted twice 
    # and then we also have to flag each trasaction of this data as "Periodic"


    # master data -> two tables both on disk and read onto memory
    pass


# now that we have the necessary paritions of data 
# we will now use threads to feed that data into mesh join then go to our data warehouse 


#checking the problrem for invoice 
#path=Path(r"C:\Users\dani\Documents\Studies\Data Warehouse\Project\Data\Online Retail.xlsx")
#data=pd.read_excel(path)
#print(data.head(5))
#print(data["InvoiceNo"])