import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

# Configuration
DB_HOST = "localhost"
DB_USER = "postgres"
# Try passwords: 'postgres' (common), 'postgresql' (from app.py), '' (empty)


PASSWORDS_TO_TRY = ["postgres", "postgresql", "password", "", "Prim#2504"]

def get_connection(dbname=None, password=None):
    try:
        conn = psycopg2.connect(dbname=dbname, user=DB_USER, password=password, host=DB_HOST)
        return conn
    except psycopg2.Error:
        return None

def find_password():
    print("Attempting to connect to PostgreSQL to find correct password...")
    for pwd in PASSWORDS_TO_TRY:
        conn = get_connection("postgres", pwd)
        if conn:
            print(f"Success! Password is: '{pwd}'")
            conn.close()
            return pwd
    print("Could not connect to PostgreSQL with common passwords.")
    return None

def create_database(cursor, db_name):
    cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_name,))
    exists = cursor.fetchone()
    if not exists:
        print(f"Creating database {db_name}...")
        cursor.execute(f"CREATE DATABASE {db_name}")
    else:
        print(f"Database {db_name} already exists.")

def init_dbs():
    password = find_password()
    if password is None:
        print("Please ensure PostgreSQL is running and you know the password for 'postgres' user.")
        print("Update app.py and main.py with the correct password.")
        return

    # Connect to 'postgres' db to create other dbs
    conn = psycopg2.connect(dbname="postgres", user=DB_USER, password=password, host=DB_HOST)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Create databases
    create_database(cur, "cafe_v2_db")
    create_database(cur, "coffeeshop_cashflow")
    
    cur.close()
    conn.close()

    # Initialize cafe_v2_db (entries table)
    print("Initializing cafe_v2_db...")
    conn = psycopg2.connect(dbname="cafe_v2_db", user=DB_USER, password=password, host=DB_HOST)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            entry_type TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            details TEXT,
            staff_name TEXT,
            balance NUMERIC(12,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

    # Initialize coffeeshop_cashflow (from SQL file)
    print("Initializing coffeeshop_cashflow...")
    # Use psql command to execute the SQL file because it contains COPY FROM stdin
    import subprocess
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    
    try:
        subprocess.run(
            ["psql", "-h", DB_HOST, "-U", DB_USER, "-d", "coffeeshop_cashflow", "-f", "coffeeshop_db.sql"],
            check=True,
            env=env
        )
        print("Executed coffeeshop_db.sql successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error executing SQL file via psql: {e}")
    
    print("Database initialization complete.")
    
    # Check if we need to update passwords in files
    # This is a bit risky to auto-edit, but we can print instructions
    if password != "postgresql":
        print(f"NOTE: The password in app.py is 'postgresql'. Your password is '{password}'.")
        print("You might need to update DB_PASSWORD in app.py.")
    
    if password != "postgres":
        print(f"NOTE: The password in main.py is 'postgres'. Your password is '{password}'.")
        print("You might need to update DATABASE_URL in main.py.")

if __name__ == "__main__":
    init_dbs()
