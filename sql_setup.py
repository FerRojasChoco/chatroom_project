#cosas de sql :p
from dotenv import load_dotenv
import os
import mysql.connector

#~~~ Load mysql credentials ~~~#
load_dotenv()   

host=os.getenv("DB_HOST")
user=os.getenv("DB_USER")
pw=os.getenv("DB_PASSWORD")

db = mysql.connector.connect(   #not using the defined function down below for connecting since this takes less args (database creation purpose)
    host=host,
    user=user,
    password=pw
)

cursor = db.cursor()

#~~~ Database creation ~~~#
cursor.execute("CREATE DATABASE IF NOT EXISTS chatroomdb")  
cursor.execute("USE chatroomdb")


#~~~ Tables creation ~~~#
cursor.execute("CREATE TABLE IF NOT EXISTS user "
"(id INT PRIMARY KEY, " \
"username VARCHAR(255) UNIQUE, " \
"email VARCHAR(255)," \
"password_hash VARCHAR(255)," \
"total_score INT)")

db.commit()
cursor.close()
db.close()

#~~~ Function for connecting to the chatroom database (avoid writing multiple times) ~~~#
def db_connect():   
    db = mysql.connector.connect(
        host=host,
        user=user,
        password=pw,
        database='chatroomdb'
    )
    return db

#~~~ Search a given username (used for checking username existence) ~~~#
def find_username(username):
    db = db_connect()
    cursor = db.cursor()
    
    query = "SELECT username FROM user WHERE username = %s"

    cursor.execute(query, (username,))

    result = cursor.fetchone()

    cursor.close()
    db.close()

    return result[0] if result else None  

#~~~ Add entry (new user registration) to the user table ~~~#
def register_user(username, password):
    db = db_connect()
    cursor = db.cursor()

    # next id calculation
    cursor.execute("SELECT MAX(id) FROM user")
    max_id = cursor.fetchone()[0]
    new_id = 1 if max_id is None else max_id+1

    #new user insertion
    query = "INSERT INTO user (id, username, password_hash, total_score) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (new_id, username, password, 0))

    db.commit()
    cursor.close() 
    db.close()