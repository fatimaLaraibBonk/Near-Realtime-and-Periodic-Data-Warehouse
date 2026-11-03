# now this takes the input file 
# and then cleans the data 
import pandas as pd
from pathlib import Path

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
    pass



# separates data into periodic and online stream 
def partition(data):
    # the online one stays in a csv
    # the periodic one goes into a database
    # master data is also on disk so its in a database 
    pass


# now that we have the necessary paritions of data 
# we will now use threads to feed that data into mesh join then go to our data warehouse 


#checking the problrem for invoice 
#path=Path(r"C:\Users\dani\Documents\Studies\Data Warehouse\Project\Data\Online Retail.xlsx")
#data=pd.read_excel(path)
#print(data.head(5))
#print(data["InvoiceNo"])