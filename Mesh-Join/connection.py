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
            log.write("[green]Database connection successful.[/green]")
            cursor=connection.cursor()

            # execution of queries

    except Error as e:
        log.write(f"[red]Error occured while connecting to database {e}.[/red]")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            log.write(f"[green]Database connection closed.[/green]")