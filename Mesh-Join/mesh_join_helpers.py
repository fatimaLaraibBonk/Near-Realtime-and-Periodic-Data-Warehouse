#mesh join helpers
#so basically hash, queue, 
import connection 
import threading

class stream_buffer:
    def __init__(self):
        self.buffer_size=1000
        self.buffer=[]
        self.n_online=0 #this basically keeps track of the last online trasnaction in the array 
        self.cond=threading.Condition() #lock stuff 
        self.stats={"online_in":0, "periodic_in":0, "evicted":0, "overflowed":0, "backpressure":0, "shed_written":0}
    #now this buffer stores transactions and feeds them into mesh join 


    #logic 
    #stream buffer is an array or a list of transactions
    #i will keep the list alwaus sorts as [online trasactions ---- periodic transactions]
    #whenever we receive online transactions, the periodic transactions from the end are cut out and sent to the shedding tables
    #and the online ones are placed right before the periodic trasnactions/end
    #[old online----new online----old staging]
    #if its just online then [old online----new online] and if it goes over the limit stop the online source from reading (backpressur)
    #if its just periodic then [old periodic----new periodic] and the remaining ones of the new periodic are sent to shedding 
    def space_available(self):
        return self.buffer_size-len(self.buffer)
    #this took me so much time im so bad
    def receive_batch(self, source, batch, main_object):
        #this function receives the batches of data 
        #i like really dont wanna code this bro im scared 
        #if theres space in the buffer we put the rows
        #else we apply priority 
        #main_object.log.write(f"batch type={type(batch)} first={repr(batch[0]) if isinstance(batch, list) else repr(batch)[:200]}")
        #checks
        #if buffer has enough space to hold all the incoming transactions 
        batch_size=len(batch)
        shed_rows=[] #shedded rows, these will be sent to our shedding table 
        leftover=[] #online rows that had no space 
        inserted=0 
        evicted=0 
        overflowed=0 
        written=0 #how many gotten written in shedding table 
        with self.cond:
            if source=="online":
                for row in batch:
                    #what to do if we got data from online source 
                    #theres no space in the stream buffer and theres periodic rows
                    #kick out the perioidic rows
                    if self.space_available()==0 and len(self.buffer)>self.n_online:
                        shed_rows.append(self.buffer.pop())
                        #main_object.log.write(f"Eviction of periodic sales for online sales: {len(shed_rows)}") #kick out the periodic ones sitting at the end 
                        evicted+=1
                    #if after periodic rows are kicked out  theres still not enough space for the online rows
                    if self.space_available()==0:
                        leftover.append(row)
                        continue
                    #else we insert
                    #main_object.log.write(f"Inserting {len(batch)} online rows.")
                    self.buffer.insert(self.n_online, row) #else insert the online row 
                    self.n_online+=1 #and move its boundary point 
                    inserted+=1 
            else: #periodic
                for row in batch:
                    #if no space then shut up and shed 
                    if self.space_available()>0:
                        #main_object.log(f"Inserting {len(batch)} periodic rows.")
                        self.buffer.append(row)
                        inserted+=1 
                    else:
                        #main_object.log.write(f"Periodic row going to shed..")
                        shed_rows.append(row)
                        overflowed+=1 
            buf_len=len(self.buffer)
            n_on=self.n_online
            self.stats["evicted"]+=evicted #how many periodics got kicked out 
            self.stats["overflowed"]+=overflowed #how many overflow in perioridic
            self.stats["backpressure"]+=len(leftover) #how many leftovers in online 
            self.stats["online_in" if source=="online" else "periodic_in"]+=inserted 

            if shed_rows:
                #main_object.log.write(f"Shedding {len(shed_rows)} periodic rows")
                #here we will then shed our stupid rows 
                try:
                    db_connection=connection.connect(main_object.host, main_object.username, main_object.password, "dw_retail_fatima", main_object.log)
                    if db_connection.is_connected():
                        query="""
                            insert into shedding_table(
                            transaction_id, customer_id, product_id, quantity, unit_price, event_time, sales_mode,release_hour, released)
                            values (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """
                        rows_to_write = [
                            (r[0], r[1], r[2], r[3], r[4], r[5], r[6],
                            r[7] if len(r) > 7 else None, 0)
                            for r in shed_rows
                        ]
                        cursor=db_connection.cursor()
                        cursor.executemany(query, rows_to_write)
                        db_connection.commit()
                        written=len(rows_to_write) 
                        self.stats["shed_written"]+=written 
                        connection.end_connection(db_connection, main_object.log, cursor)
                except Exception as e:
                    main_object.log.write(f"An error occured for shedding table {e}")
        #these prints are basically to ensure that the shedding is being done properly 
        accounted=inserted+overflowed+len(leftover)
        ok="OK" if accounted==batch_size else f"MISMATCH ({accounted}/{batch_size})"
        if source=="periodic" or shed_rows or leftover:
            """
            main_object.log.write(
                f"[{source.upper()}] batch={batch_size} in={inserted} "
                f"evicted={evicted} overflowed={overflowed} backpressure={len(leftover)} "
                f"shed_written={written} | buffer={buf_len}/{self.buffer_size} "
                f"(online={n_on}, periodic={buf_len-n_on}) | "
                f"TOTAL shed={self.stats['evicted']+self.stats['overflowed']} "
                f"TOTAL written={self.stats['shed_written']} | check={ok}"
            )
            """
        return leftover

    def summary(self):
        with self.cond:
            s=dict(self.stats)
            s["buffer"]=len(self.buffer)
            s["n_online"]=self.n_online
        return s

def make_shedding_table(main_object):
    #makes the shedding table
    #HOST, USER, PASSWORD, DATABASE, log   
    db_connection=connection.connect(main_object.host, main_object.username, main_object.password, "dw_retail_fatima", main_object.log)
    if db_connection.is_connected():
        #if connected then we make the table 
        query="""
        drop table if exists shedding_table;
        """
        cursor=db_connection.cursor()
        cursor.execute(query)
        query="create table if not exists shedding_table (" \
                "transaction_id varchar(255)," \
                "customer_id varchar(255), " \
                "product_id text, " \
                "quantity int, " \
                "unit_price float, " \
                "event_time timestamp, " \
                "sales_mode text, " \
                "release_hour int, " \
                "released int default 0);"
        cursor.execute(query)
        connection.end_connection(db_connection, main_object.log, cursor)