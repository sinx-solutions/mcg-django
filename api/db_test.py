import os
import sys
import psycopg2
import socket
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test DNS resolution
print("Testing DNS resolution:")
try:
    host_ip = socket.gethostbyname('tpiipfpvepfvwlqdvcqq.supabase.co')
    print(f"Resolved tpiipfpvepfvwlqdvcqq.supabase.co to {host_ip}")
except Exception as e:
    print(f"DNS resolution failed: {e}")

# Try with different host formats
hosts_to_try = [
    'tpiipfpvepfvwlqdvcqq.supabase.co',  # Try without 'db.' prefix
    'db.tpiipfpvepfvwlqdvcqq.supabase.co'  # Original
]

db_name = os.getenv('DB_NAME', 'postgres')
db_user = os.getenv('DB_USER', 'postgres')
db_password = os.getenv('DB_PASSWORD', 'm3UMu8KXeFHhfmFh')
db_port = os.getenv('DB_PORT', '5432')

for host in hosts_to_try:
    print(f"\nAttempting to connect to database with host: {host}")
    print(f"Database: {db_name}")
    print(f"User: {db_user}")
    print(f"Password: {'*' * len(db_password) if db_password else 'Not provided'}")
    print(f"Port: {db_port}")
    print("-" * 50)
    
    try:
        # Try connecting to the database
        conn = psycopg2.connect(
            host=host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port,
            sslmode='require',
            connect_timeout=10  # Add a timeout
        )
        
        # Create a cursor
        cur = conn.cursor()
        
        # Execute a simple query
        cur.execute('SELECT version();')
        
        # Get the result
        db_version = cur.fetchone()
        
        print("Connection successful!")
        print(f"PostgreSQL database version: {db_version[0]}")
        
        # Close the connection
        cur.close()
        conn.close()
        
        # Exit if successful
        sys.exit(0)
        
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e).__name__}")
        print("Connection failed.")

# Try direct connection string
print("\nTrying direct connection string:")
try:
    conn_string = f"postgresql://{db_user}:{db_password}@{hosts_to_try[0]}:{db_port}/{db_name}?sslmode=require"
    print(f"Connection string (password hidden): postgresql://{db_user}:****@{hosts_to_try[0]}:{db_port}/{db_name}?sslmode=require")
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor()
    cur.execute('SELECT version();')
    db_version = cur.fetchone()
    print("Connection successful!")
    print(f"PostgreSQL database version: {db_version[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e).__name__}")
    print("Connection failed.")

print("\nAll connection attempts failed.") 