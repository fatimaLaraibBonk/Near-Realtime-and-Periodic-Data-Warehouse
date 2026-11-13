# main threads
import threading
import pandas as pd
import connection
import time
import mesh_join_helpers 
from collections import deque 
import math
from collections import defaultdict, deque
import hashlib 
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
        self.hour=1 #meaning 1 hour is 60 seconds
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
def OnlineThread(Settings, main_object, stream_buff):
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
                main_object.log.write(f"[bold black]Reached the end of online file.[/bold black]")
                break
            #send batch to our fav stream buffer
            batch=list(batch.itertuples(index=False, name=None))
            left_over=stream_buff.receive_batch("online",batch, main_object, speed)
            if left_over:
                reader.pointer-=len(left_over) #unread them
                time.sleep(0.05) #let meshjoin catchup 
            Settings.config_changed.wait(timeout=1)
            if(count_of_batches==hour):
                main_object.log.write(f"[bold green]{count_of_batches*rate} rows read for online.[/bold green]")
                count_of_batches=0
                #This was just to like count or stuff 
        else:
            Settings.config_changed.wait()


# periodic threads
def PeriodicThread(Settings, main_object, stream_buff):
    #it sends the data every 60 seconds, i.e every hour
    release_hour=0 #so we start releasing from zero and make our way up
    #connection
    db_connection=connection.connect(main_object.host, main_object.port, main_object.username, main_object.password, main_object.name , main_object.log)
    if db_connection and db_connection.is_connected():
        main_object.log.write(f"[bold green]DB connection successful for periodic thread[/bold green]")
        cursor=db_connection.cursor()
        next_release=time.monotonic()   # first group goes out immediately
        paused=False
        while not Settings.stop_event.is_set():
            Settings.config_changed.clear()
            mode, rate, hour, speed = Settings.get_config()
            if mode in ("both", "periodic"):
                if(release_hour==48):
                    break
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
                    stream_buff.receive_batch("periodic", batch, main_object, speed)
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
        main_object.log.write(f"[bold black]Reached the end of periodic groups[/bold black]")
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


#int(hashlib.md5(x.encode('utf-8')).hexdigest()[:8], 16) % 10
#flow 
#chunks->master data->consolidation->data warehouse 
def MeshJoinThread(Settings, main_object, stream_buff):
    #this function removes from stream buff instead of adding into it 
    H=defaultdict(list) #hash tabel
    queue=deque()
    known={"cust":set(), "prod":set(), "time":set()} #keeping track of what ids we already know 
    periodic_hold=[] #finished periodic transactions waiting for the hourly load
    db_connection=connection.connect(main_object.host, main_object.port, main_object.username, main_object.password, main_object.name , main_object.log)
    if db_connection.is_connected():
        #tables
        query="select count(*) from customer_master_data"
        cursor=db_connection.cursor()
        cursor.execute(query)
        count_customers=cursor.fetchone()[0]
        query="select count(*) from product_master_data"
        cursor.execute(query)
        count_product=cursor.fetchone()[0]
        customers_pages=math.ceil(count_customers/500)
        product_pages=math.ceil(count_product/500)
        N_ITER=max(customers_pages, product_pages)#max (customer, product_pages) 
        main_object.log.write(f"[PAGES COUNT] Customer Pages: {customers_pages}, Product Pages: {product_pages}")
        #stores=[("London Bridge" ,"London"),("Manchester Arndale", "Manchester"),("Birmingham Bullring", "Birmingham"),("Edinburgh Princes", "Edinburgh")]
        #we also need a queue 
        cust_page=0
        prod_page=0
        next_flush=time.monotonic()+Settings.get_config()[2] #when the next hourly periodic load is due
        while not Settings.stop_event.is_set():
            mode, rate, hour, speed = Settings.get_config()
            #hourly load of the held periodic transactions (this check is at the top so no continue can skip it)
            if time.monotonic()>=next_flush:
                if periodic_hold:
                    consolidate(periodic_hold, db_connection, cursor, main_object, speed, known)
                    main_object.log.write(f"[HOURLY LOAD] {len(periodic_hold)} periodic transactions loaded into the DW")
                    periodic_hold=[]
                next_flush=time.monotonic()+hour
            chunk=stream_buff.take_chunk(500)

            #UNSHEDDING 
            #unshedding: shed rows only fill the unused slots of the chunk, so online and periodic always go first
            #i was really confused by if u want or not want unshedding for peak or nah 

            spare=500-len(chunk)
            #if spare>0 and mode!="online": #periodic work is paused in online-only mode 
                #allowance=spare if speed=="non-peak" else spare//4 #non-peak drains at full rate, peak at a reduced rate
                #the //4 is only done to slow down the drain for the peak mode
                #so for peak we only drain quarter 
                #to completely stop shedding for peak 
                #if allowance>0:
                    #chunk=chunk+stream_buff.read_shed_rows(db_connection, allowance, main_object, speed)
            if spare>0 and mode!="online" and speed=="non-peak":
                chunk=chunk+stream_buff.read_shed_rows(db_connection, spare, main_object, speed)


            txns=[]
            for row in chunk:
                #now for each row i will put it in the hash table 
                #im so hangry
                #tuples cant be changed so wrap each row in a dict to attach cust and prod later
                t={"row":row, "cust":None, "prod":None}
                H[("C", str(row[1]))].append(t)
                H[("P", str(row[2]))].append(t)
                txns.append(t)
            #that chunk has been put in hash now we put this chunck 
            if txns:
                queue.append({"rows":txns, "iters":0})
            #nothing in the stream and nothing in the queue, no point reading master data
            if not queue:
                Settings.h_count=0
                time.sleep(0.05)
                continue
            #so to load these master tables we need the connection
            #but now we need offset to get 500-500-500 like
            #ok now we load in the 500 rows tables
            query="select * from customer_master_data order by customer_id limit 500 offset %s"
            #nowe we read the next customer page 
            cursor.execute(query, (cust_page*500,))
            #now we will fetch that data and then use that data to join 
            customers_data=cursor.fetchall()
            #and the next product page 
            query="select * from product_master_data order by product_id limit 500 offset %s"
            cursor.execute(query, (prod_page*500,))
            product_data=cursor.fetchall()
            #THE JOIN, every master row looks itself up in H and gets attached to the transactions it matches
            for m in customers_data:
                for t in H.get(("C", str(m[0])), ()):
                    t["cust"]=m
            for m in product_data:
                for t in H.get(("P", str(m[0])), ()):
                    t["prod"]=m
            #move to the next or wrap arounf 
            cust_page=(cust_page+1)%customers_pages
            prod_page=(prod_page+1)%product_pages
            #then we incrmenet or age 
            for c in queue:
                c["iters"]+=1
            #queue is first in first out 
            if queue and queue[0]["iters"]>=N_ITER:
                done=queue.popleft()
                for t in done["rows"]:
                    H[("C", str(t["row"][1]))].remove(t)
                    H[("P", str(t["row"][2]))].remove(t)
                    #we also need to conslidate these rows
                    #if this prints the id is missing from master data or the key types dont match
                    if t["cust"] is None or t["prod"] is None:
                        main_object.log.write(f"Missing master match for transaction {t['row'][0]}")
                #next step is consolidation :3
                #consolidate(done["rows"]) -> revenue, dimension keys, fact table
                #once conslidated they will go into our warehouse 

                #for each transaction we find the sales 
                #dimensions and fact tables 
                #t["cust"]->customer dimension 
                #t["prod"]->product dimension
                #t["prod"]->also has supplier data 
                #we also need to fill in the dimensiomn tables
                #if the current key is not present in the dimension table then we have to insert it there as well 
                #what goes in the data warehouse
                #facts, customers, stores, products, time, supplier
                #store 
                #if transaction is online store it uses "Online"
                #consolidate(done["rows"], db_connection, cursor, main_object, speed, known) #REPLACED by the online/periodic split below
                online_rows=[t for t in done["rows"] if t["row"][6]=="Online"] #online loads right away
                periodic_hold.extend(t for t in done["rows"] if t["row"][6]!="Online") #periodic waits for the hourly load
                if online_rows:
                    consolidate(online_rows, db_connection, cursor, main_object, speed, known)
            Settings.h_count=sum(len(c["rows"]) for c in queue)
            if not chunk:
                time.sleep(0.05) #stream is empty but keep looping so old chunks can finish 
        #final flush so held periodic transactions are not lost on quit
        if periodic_hold:
            consolidate(periodic_hold, db_connection, cursor, main_object, Settings.get_config()[3], known)
            main_object.log.write(f"[FINAL LOAD] {len(periodic_hold)} periodic transactions loaded on quit")
        #once finished end the connection
        connection.end_connection(db_connection, main_object.log, cursor)
    else:
        main_object.log.write(f"Database failed to load for mesh join")

def consolidate(done_rows, db_connection, cursor, main_object, processing_mode, known):
    #here we actually do the consolidation 
    cust_new, prod_new, time_new, facts={},{},{},[]
    for t in done_rows:
        row=t["row"]
        if t["cust"] is None or t["prod"] is None:
            #theyre just missing this shi 
            continue
        txn_id,cust_id, prod_id = str(row[0]), str(row[1]), str(row[2])
        qty, price, sales_mode = int(row[3]), float(row[4]), row[6]

        #store 
        if sales_mode=="Online":
            store_id=1
        else:
            store_id=2+((int(hashlib.md5(txn_id.encode("utf-8")).hexdigest()[:8], 16) % 4))

        #now time 
        #time (event_time may be a string from the csv or a datetime from MySQL)
        ts=pd.Timestamp(row[5])
        time_key=int(ts.strftime("%Y%m%d%H"))

        supplier_id=t["prod"][3]

        #collect only dimension rows we havent inserted before or like havent seen before
        if cust_id not in known["cust"]:
            cust_new[cust_id]=tuple(t["cust"][:7])
        if prod_id not in known["prod"]:
            prod_new[prod_id] = (t["prod"][0], t["prod"][1], t["prod"][2])
        #time is our least prepared dimension as of now 
        #so we also need to...prepare it lol
        if time_key not in known["time"]:
            m = ts.month
            season = ("Winter" if m in (12, 1, 2) else "Spring" if m in (3, 4, 5)
                      else "Summer" if m in (6, 7, 8) else "Fall")
            time_new[time_key] = (time_key, ts.date(), ts.hour, ts.day, m, (m - 1)//3 + 1,
                                  ts.year, ts.day_name(),
                                  "Weekend" if ts.dayofweek >= 5 else "Weekday",
                                  season, 1 if m <= 6 else 2)
        revenue=round(qty * price, 2)
        facts.append((txn_id, cust_id, prod_id, supplier_id, str(store_id),
                      time_key, qty, revenue, sales_mode, processing_mode))

        #now that our row is ready we cna append it heheheheeh
    try:
        if cust_new:
            cursor.executemany("""insert ignore into dim_customer
            (customer_id, gender, age_group, occupation, city_category,
            stay_in_current_city_years, marital_status)
            values (%s,%s,%s,%s,%s,%s,%s)""", list(cust_new.values()))
        if prod_new:
            cursor.executemany("""insert ignore into dim_product
            (product_id, product_name, product_category)
            values (%s,%s,%s)""", list(prod_new.values()))
        if time_new:
            cursor.executemany("""insert ignore into dim_time
            (time_key, full_date, hour, day_of_month, month, quarter, year,
            day_of_week, weekday_weekend, season, half_year)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", list(time_new.values()))
        if facts:
            cursor.executemany("""insert into fact_sales
            (transaction_id, customer_id, product_id, supplier_id, store_id,
            time_key, quantity, revenue, sales_mode, processing_mode)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", facts)
        db_connection.commit()                          # dimensions + facts together
        known["cust"].update(cust_new); known["prod"].update(prod_new); known["time"].update(time_new)
    except Exception as e:
        db_connection.rollback()
        main_object.log.write(f"Consolidation failed for {len(facts)} facts: {e}")
def start_threads(settings, main_object):
    #making sure our shedding table is already prepared 
    mesh_join_helpers.make_shedding_table(main_object)
    stream_buff=mesh_join_helpers.stream_buffer()
    settings.stream_buff=stream_buff
    t1=threading.Thread(target=OnlineThread, args=(settings, main_object, stream_buff), daemon=True)
    t2=threading.Thread(target=PeriodicThread, args=(settings, main_object, stream_buff), daemon=True)
    t3=threading.Thread(target=MeshJoinThread, args=(settings, main_object, stream_buff), daemon=True)
    t1.start()
    t2.start()
    t3.start()