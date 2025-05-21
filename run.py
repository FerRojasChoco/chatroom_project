import os
import csv
import mysql.connector 
from app import create_app, db, socketio
# Added by Nico: Also import GlobalLeaderboard along with Code.
from app.models import Code, GlobalLeaderboard 
from app.config import Config 

app = create_app()

def ensure_database_exists():
    try:
        db_connector = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        cursor = db_connector.cursor()
        db_name = app.config['SQLALCHEMY_DATABASE_URI'].split('/')[-1].split('?')[0] 
        
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        app.logger.info(f"Database '{db_name}' ensured to exist.")
        cursor.close()
        db_connector.close()
    except mysql.connector.Error as err:
        app.logger.error(f"Error connecting to MySQL or ensuring database: {err}") #log

    except Exception as e:
        app.logger.error(f"An unexpected error occurred during database check: {e}") #log


def populate_codes_from_csv_if_empty():
    if not Code.query.first(): 
        app.logger.info("Code table is empty. Populating from code.csv...") #log
        try:
            Code.query.delete()
            db.session.commit()

            with open('code.csv', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                codes_to_add = []
                for row in reader:
                    code_entry = Code(
                        id=int(row['id']),
                        full_code=row['full_code'],
                        error_line_number=int(row['error_line_number']),
                        correct_line=row['correct_line']
                    )
                    db.session.add(code_entry)
                db.session.commit()
                    

        except FileNotFoundError:
            app.logger.error("code.csv not found. Cannot populate Code table.")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error populating Code table from CSV: {e}")
    else:
        app.logger.info("Code table already contains data. Skipping CSV population.")


#~~~ Main structure: make sure db exists, create tables based on models if they don't exist, populate codes table ~~~#
if __name__ == "__main__":
    with app.app_context():
        ensure_database_exists() 
        db.create_all()          
        populate_codes_from_csv_if_empty() 

    # For production, consider debug=False and more robust host/port settings
    # socketio.run(app, host='0.0.0.0', port=5000, debug=False) #run with this for testing non localhost
    socketio.run(app, debug=True)