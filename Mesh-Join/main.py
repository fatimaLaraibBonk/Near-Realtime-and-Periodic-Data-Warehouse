
# here i accumulate all the code neatly together 
import cleaner
import pandas as pd 
from pathlib import Path


# from that input we will get the link to file and clean it and then we will show the cleaned stats
def clean_up_file(file_link, log):

    
    # since the data takes forever to download ill make a safety check to see if downloaded already exists 
    
    # if already downloaded but not cleaned 
    path=Path(r"C:\Users\dani\Documents\Studies\Data Warehouse\Project\Data\Online Retail.xlsx")
    if path.is_file():
        log.write("Data already exists..")
        data=pd.read_excel(path)
        cleaner.cleanup(data, log)
        return
    # else download and sent for clean up (mazdoori)
    log.write("Fetching data from online..")
    data=pd.read_excel(file_link)
    log.write("Data read. Now cleaning.")
    cleaner.cleanup(data, log)
    return

# then we start up the warehouse 

def start_etl():
    pass
