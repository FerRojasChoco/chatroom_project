#cosas de sql :p
from flask_login import UserMixin
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
import os


db = SQLAlchemy()

#~~~ Load mysql credentials ~~~#
load_dotenv()   

host=os.getenv("DB_HOST")
user=os.getenv("DB_USER")
pw=os.getenv("DB_PASSWORD")


# Separate function for database creation
import mysql.connector
db_connector = mysql.connector.connect(
    host=host,
    user=user,
    password=pw
)
cursor = db_connector.cursor()
cursor.execute("CREATE DATABASE IF NOT EXISTS chatroomdb")
cursor.close()
db_connector.close()


#~~~ Tables creation (class definition) ~~~#
#This is done so we can treat each table as an object and use SQLalchemy functions on them
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=True, unique=True)
    password = db.Column(db.String(80), nullable=True)
    score = db.Column(db.BigInteger, nullable=True)

class Code(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_code = db.Column(db.Text, nullable=False)
    error_line_number = db.Column(db.Integer, nullable=False)
    correct_line = db.Column(db.String(255), nullable=False) #fixed size since one line of code won't be that long

