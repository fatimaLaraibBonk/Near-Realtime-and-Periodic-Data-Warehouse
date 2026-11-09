
# main threads
import threading 

# flow 
#threads -> buffer -> mesh join -> consolidation -> data warehouse -> finally we have queries 
#now this part basically reads the data from the tables and csvs and sends it to the shedding and mesh join
class Settings:
    def __init__(self):
        #default values 
        self.rate=80 #default rate 
        self.mode="both"
        self.speed="peak"  #im only keeping this to strictly enforce the shedding and unshedding rules 
        self.hour=60 #meaning 1 hour is 60 seconds
        self.lock=threading.Lock() #while one thread is working with a variable it locks it 
        self.config_changed=threading.Event() #when we change the peak and nonpeak values 
        self.stop_event=threading.Event()

    #during peak mode we only receive peak value
    #during non-peak mode we only receibe non-peak value  
    #basically at any time we are receiving a single value 
    #the peak, non-peak distinction is just for us 

    #online thread only needs to know how many tuples to read
    def update_speed(self, value):
        with self.lock:
            self.speed=value #peak/nonpeak
    def update_mode(self, value):
        with self.lock:
            self.mode=value #periodic/online/both

    def update_rate(self, value):
        with self.lock:
            self.rate=value #how many rows/tuples the thread needs to read rn 
    
    def get_config(self):
        with self.lock:
            return self.mode, self.rate, self.hour, self.speed

#peak and non-peak is used by online 
# online threadd
# now their job is to read the data and send it to mesh join which then enriches it 
def online_thread(Settings):
    while not Settings.stop_event.is_set():
        mode, rate, hour, speed = Settings.get_config()
        if mode in ("both", "online"):
            #in these modes online is working 
            #it reads rate number of rows every second
            pass
        else:
            Settings.config_changed.wait()
        Settings.config_changed.clear()

# periodic threads
def periodic_thread():
    #it sends the data every 60 seconds, i.e every hour 
    while not Settings.stop_event.is_set():
        mode, rate, hour, speed = Settings.get_config()
        if mode in ("both", "periodic"):
            #in these modes periodic is working 
            #it reads an entire group every 60 seconds 
            Settings.config_changed.wait(timeout=hour) #wait for 60 seconds 
        else:
            Settings.config_changed.wait()
        Settings.config_changed.clear()

# buffer, we have two buffers stream buffer and disk buffer 
class stream_buffer:
    def __init__(self):
        self.size=1000 #size of buffer 
        #the buffer is just an array 
# meshjoin thread + algorithm 

