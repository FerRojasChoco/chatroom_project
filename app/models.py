from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

#~~~ Tables creation (class definition) ~~~#
#This is done so we can treat each table as an object and use SQLalchemy functions on them
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=True, unique=True)
    password = db.Column(db.String(80), nullable=True)
    score = db.Column(db.BigInteger, nullable=True, default=0)

class Code(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_code = db.Column(db.Text, nullable=False)
    error_line_number = db.Column(db.Integer, nullable=False)
    correct_line = db.Column(db.String(255), nullable=False) #fixed size since one line of code won't be that long
