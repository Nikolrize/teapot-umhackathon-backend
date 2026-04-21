import os
import psycopg2
from dotenv import load_dotenv

# read .env file
load_dotenv()

# get connection string
conn_string = os.getenv("DATABASE_URL")
conn = None

# connect to database
try:
    with psycopg2.connect(conn_string) as conn:
        print("Connection established")
except Exception as e:
    print("Connection failed.")
    print(e)