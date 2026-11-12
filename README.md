# Data Warehouse Project

- Note: I don't recommend downloading the file via the link, its very slow. There is downloaded file in the data, asnd it ensures smooother runs. 

- Step by Step Instructions

1. First go to the Mesh-Join folder and run the "initial_setup.sql" file. This creates the database with name "dw_retail_fatima"
2. Then in the Create-DW folder run the "data_warehouse.sql" file, this file must always be ran before any run in the terminal to get rid of the previous tables and data.
3. Then go back to the Mesh-Join folder and run "terminal.py" in command prompy "py terminal.py"
4. Input the database host, port, username and password and the url link to the data (link: https://archive.ics.uci.edu/static/public/352/online+retail.zip) and database name is "dw_retail_fatima".
5. The project will start automatically, you can run any commands in the prompt box.
6. Once all of the data has loaded in, go to "Queries-DW" folder and run "20_Queries.sql"

- Commands and what they do 

online: changes incoming data to online alone
perioidic: changes incoming data to periodic alone.
both: uses both periodiic and online data 
peak: switch to peak mode
non-peak: switch to non-peak mode
status: print the current status: mode, speed etc
change: change the peak and non-peak rates from the terminal
help: see all commands
quit: exit 


Dataset citation
Chen, Sain and Guo, Online Retail, UCI Machine Learning Repository 
Downloaded on 3rd November 2026 
Link: https://archive.ics.uci.edu/static/public/352/online+retail.zip
