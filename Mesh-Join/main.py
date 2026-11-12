# here i accumulate all the code neatly together
import cleaner
import threads
import pandas as pd
from pathlib import Path
import requests
import os
import zipfile 

class data:
    def __init__(self, log, host, port, username, password, name):
        self.log=log
        self.host=host
        self.port=port
        self.name=name
        self.username=username
        self.password=password

    def sql_data(self):
        return self.host, self.port, self.name, self.username, self.password

    def return_log(self):
        return self.log


# from that input we will get the link to file and clean it and then we will show the cleaned stats
def clean_up_file(file_link, log, host, port, username, password, name):

    main_object=data(log=log, host=host, port=port, username=username, password=password, name=name) #now we can pass this object to other files so they can do their stuff
    # since the data takes forever to download ill make a safety check to see if downloaded already exists
    # if already downloaded but not cleaned
    # using relative pathing
    path=Path(r"..\Data\Online Retail.xlsx")

    if path.is_file():
        log.write("Data already exists..")
        df=pd.read_excel(path)
        df=cleaner.cleanup(df, log)
        cleaner.partition(df,log, host, port, name, username, password) # actual distribution

    # else download and sent for clean up (mazdoori)
    else:
        os.makedirs(path.parent, exist_ok=True)
        log.write(f"Saving to: {path.resolve()}")
        headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
        tmp=path.with_suffix(".part")
        for attempt in range(1, 4):
            try:
                log.write(f"Download attempt {attempt}/3..")
                downloaded=0
                last_progress=0
                with requests.get(file_link, stream=True, headers=headers, timeout=(10, 30)) as response:
                    response.raise_for_status()
                    total_size=int(response.headers.get("content-length", 0))
                    with open(tmp, "wb") as file:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                file.write(chunk)
                                downloaded+=len(chunk)
                                if total_size:
                                    progress=int((downloaded/total_size)*100)
                                    if progress>=last_progress+5:
                                        log.write(f"Downloading: {progress}%")
                                        last_progress=progress
                                elif downloaded//(1024*1024) > last_progress:
                                    last_progress=downloaded//(1024*1024)
                                    log.write(f"Downloaded: {downloaded/(1024*1024):.2f} MB")
                if not zipfile.is_zipfile(tmp):
                    raise ValueError("Downloaded file is not a zip/xlsx")
                break
            except Exception as e:
                log.write(f"Download failed: {e}")
                if attempt==3:
                    raise

        with zipfile.ZipFile(tmp) as z:
            names=z.namelist()
            is_xlsx="xl/workbook.xml" in names
            if not is_xlsx:
                member=[n for n in names if n.lower().endswith(".xlsx")][0]
                with z.open(member) as src, open(path, "wb") as dst:
                    dst.write(src.read())
        if is_xlsx:
            tmp.replace(path)
        else:
            tmp.unlink()

        log.write("Download complete.")
        df=pd.read_excel(path)
        log.write("Data read. Now cleaning.")
        df=cleaner.cleanup(df, log)
        cleaner.partition(df,log, host, port, name, username, password)

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