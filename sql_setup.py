#cosas de sql :p
from dotenv import load_dotenv
import os
import mysql.connector

load_dotenv()

host=os.getenv("DB_HOST")
user=os.getenv("DB_USER")
pw=os.getenv("DB_PASSWORD")

db = mysql.connector.connect(
    host=host,
    user=user,
    password=pw
)

cursor = db.cursor()

create_database="""
CREATE DATABASE IF NOT EXISTS chatroomdb
"""

create_table="""

"""

cursor.execute(create_database)



db.close()