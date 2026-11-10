#database connection code 
import mysql.connector 
from mysql.connector import Error

def connect(HOST, USER, PASSWORD, DATABASE, log):
    try:
        connection=mysql.connector.connect(
            host=HOST, 
            user=USER, 
            password=PASSWORD,
            database=DATABASE
        )
        if connection.is_connected():
            #log.write("[green]Database connection successful.[/green]")    # execution of queries
            return connection 
    except Error as e:
        log.write(f"[red]Error occured while connecting to database {e}.[/red]")
    return 0

def execute_query(connection, log, query):
     if connection.is_connected():
        cursor=connection.cursor()
        #this cursor will then be used to execute our queries
        cursor.execute(query)
        return cursor
    
def end_connection(connection, log, cursor):
    if 'connection' in locals() and connection.is_connected():
        cursor.close()
        connection.close()
        #log.write(f"[green]Database connection closed.[/green]")