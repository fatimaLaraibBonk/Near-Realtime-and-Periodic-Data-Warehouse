# main threads
import threading
import pandas as pd
import connection
import time
import mesh_join_helpers 

# periodic and online threads DONE
# shedding DONE
# unshedding
# meshjoin
#consolidation
# going to datawarehouse 


# flow
# threads -> buffer -> mesh join -> consolidation -> data warehouse -> finally we have queries
# now this part basically reads the data from the tables and csvs and sends it to the shedding and mesh join
class settings:
    def __init__(self, rate, mode, speed):
        #default values
        self.rate=rate
        self.mode=mode
        self.speed=speed  #im only keeping this to strictly enforce the shedding and unshedding rules
        self.hour=60 #meaning 1 hour is 60 seconds
        self.lock=threading.Lock()
        self.config_changed=threading.Event() #when we change the peak and nonpeak values
        self.stop_event=threading.Event()

    #during peak mode we only receive peak value
    #during non-peak mode we only receibe non-peak value
    #basically at any time we are receiving a single value

    #online thread only needs to know how many tuples to read
    def update_speed(self, value):
        with self.lock:
            self.speed=value
            self.config_changed.set()

    def update_mode(self, value):
        with self.lock:
            self.mode=value
            self.config_changed.set()

    def update_rate(self, value):
        with self.lock:
            self.rate=int(value)  
            self.config_changed.set()

    def get_config(self):
        with self.lock:
            return self.mode, self.rate, self.hour, self.speed


class CSVReader:
    def __init__(self, filepath):
        self.data = pd.read_csv(filepath)
        self.pointer = 0

    def read_rows(self, n):
        batch = self.data.iloc[self.pointer:self.pointer+n]
        self.pointer += len(batch)
        return batch


#peak and non-peak is used by online
# online thread
# now their job is to read the data and send it to mesh join which then enriches it
def online_thread(Settings, main_object, stream_buff):
    reader=CSVReader("..\\Data\\online_sales_stream.csv")
    count_of_batches=0
    while not Settings.stop_event.is_set():
        Settings.config_changed.clear() 
        mode, rate, hour, speed = Settings.get_config()
        if mode in ("both", "online"):
            #in these modes online is working
            #it reads rate number of rows every second
            #needs to read rate amount of rows
            batch=reader.read_rows(rate)
            #main_object.log.write(f"[black]Read {len(batch)} number of rows[/black]")
            count_of_batches+=1
            if batch.empty:
                break
            #send batch to our fav stream buffer
            batch=list(batch.itertuples(index=False, name=None))
            left_over=stream_buff.receive_batch("online",batch, main_object)
            if left_over:
                reader.pointer-=len(left_over) #unread them
                time.sleep(0.05) #let meshjoin catchup 
            Settings.config_changed.wait(timeout=1)
            if(count_of_batches==hour):
                main_object.log.write(f"[bold green]{count_of_batches} number of groups read for online.[/bold green]")
                count_of_batches=0
                #This was just to like count or stuff 
        else:
            Settings.config_changed.wait()


# periodic threads
def periodic_thread(Settings, main_object, stream_buff):
    #it sends the data every 60 seconds, i.e every hour
    release_hour=0 #so we start releasing from zero and make our way up
    #connection
    db_connection=connection.connect(main_object.host, main_object.username, main_object.password, "dw_retail_fatima", main_object.log)
    if db_connection and db_connection.is_connected():
        main_object.log.write(f"[bold green]DB connection successful for periodic thread[/bold green]")
        cursor=db_connection.cursor()
        next_release=time.monotonic()   # first group goes out immediately
        paused=False
        while not Settings.stop_event.is_set():
            Settings.config_changed.clear()
            mode, rate, hour, speed = Settings.get_config()
            if mode in ("both", "periodic"):
                if paused:
                    #we just switched back from online-only, so start a fresh hour
                    next_release=time.monotonic()+hour
                    paused=False
                remaining=next_release-time.monotonic()
                if remaining>0:
                    #not time yet: sleep the rest of the hour, then re-check
                    #(a config change wakes us, but we just loop back here and keep waiting)
                    Settings.config_changed.wait(timeout=remaining)
                    continue
                #it reads an entire group every 60 seconds
                try:
                    query=f"select * from periodic_sales_data where release_hour=%s AND released=0"
                    cursor.execute(query, (release_hour,))
                    batch=cursor.fetchall() 
                    stream_buff.receive_batch("periodic", batch, main_object)
                    query=f"update periodic_sales_data set released=1 where release_hour=%s AND released=0"
                    cursor.execute(query, (release_hour,))
                    db_connection.commit()
                    release_hour+=1
                    main_object.log.write(f"[bold green]Group {release_hour} read.[/bold green]")
                    next_release=time.monotonic()+hour
                except Exception as e :
                    main_object.log.write(f"Error while fetching perioidic sales {e}")
            else:
                paused=True
                Settings.config_changed.wait()
        cursor.close()
        db_connection.close()
    else:
        main_object.log.write(f"[bold red]DB connection not successful for periodic thread[/bold red]")


#mesh join 
#flow 
"""
1. take a chunk from the stream buffer
2. put that chunk in the hash table 
3. record the chunk in the queue
4. read the next master data page
5. probe
6. check oldest chunk 
"""

def start_threads(settings, main_object):
    #making sure our shedding table is already prepared 
    mesh_join_helpers.make_shedding_table(main_object)
    stream_buff=mesh_join_helpers.stream_buffer()
    t1=threading.Thread(target=online_thread, args=(settings, main_object, stream_buff), daemon=True)
    t2=threading.Thread(target=periodic_thread, args=(settings, main_object, stream_buff), daemon=True)
    t1.start()
    t2.start()