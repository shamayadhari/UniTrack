
import psycopg2
from config import DB_CONFIG

def get_db_connection():
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        return connection
    except psycopg2.Error as error:
        print("Database connection failed:", error)
        return None
