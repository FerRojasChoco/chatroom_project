import os
from dotenv import load_dotenv

#~~~ Load environment variables from .env ~~~#
load_dotenv()   

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    DB_HOST = os.getenv("DB_HOST")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    SQLALCHEMY_DATABASE_URI = (
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/chatroomdb'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    