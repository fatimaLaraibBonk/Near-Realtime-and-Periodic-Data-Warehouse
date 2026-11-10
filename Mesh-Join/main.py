
# here i accumulate all the code neatly together 
import cleaner
import threads
import pandas as pd 
from pathlib import Path



class data:
    def __init__(self, log, host, port, username, password):
        self.log=log
        self.host=host
        self.port=port
        self.username=username
        self.password=password

    def sql_data(self):
        return self.host, self.port, self.username, self.password

    def return_log(self):
        return self.log 


# from that input we will get the link to file and clean it and then we will show the cleaned stats
def clean_up_file(file_link, log, host, port, username, password):

    main_object=data(log,host,port,username,password) #now we can pass this object to other files so they can do their stuff 
    # since the data takes forever to download ill make a safety check to see if downloaded already exists 
    # if already downloaded but not cleaned 
    # using relative pathing 
    path=Path(r"..\Data\Online Retail.xlsx")
    if path.is_file():
        log.write("Data already exists..")
        df=pd.read_excel(path)
        df=cleaner.cleanup(df, log)
        cleaner.partition(df,log, host, port, username, password) # actual distribution 
    # else download and sent for clean up (mazdoori)
    else:
        log.write("Fetching data from online..")
        df=pd.read_excel(file_link)
        log.write("Data read. Now cleaning.")
        df=cleaner.cleanup(df, log)
        cleaner.partition(df,log, host, port, username, password)
    return main_object

#in the end of the cleanup file function we get master data in tables and csv, 
# online data in the form of a csv
# periodic data in a table 


# now we start the actual nightmare
# start threads
# buffer and mesh join with shedding 
# unshedding during non-peak time 
# 
def start_etl(main_object, rate, mode, speed):
    #main object is just used to pass arounf the necessary unchanging data
    #here we boot up the stupid threads for periodic sales and online sales 

    settings=threads.settings(rate, mode, speed)
    threads.start_threads(settings, main_object)
    return settings 

