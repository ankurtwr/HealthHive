import sys
import os
import re

from app import create_app
from db import get_connection

def run_migration():
    app = create_app()
    with app.app_context():
        print("Starting Database Migration v2...")
        
        migration_file = 'schema_migration_v2.sql'
        if not os.path.exists(migration_file):
            print(f"Error: {migration_file} not found!")
            return
            
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
            
        # Split statements by semicolon, ignoring comments and empty lines
        statements = []
        # Remove comments
        clean_sql = re.sub(r'--.*$', '', sql_content, flags=re.MULTILINE)
        
        # Split by semicolon
        raw_statements = clean_sql.split(';')
        for stmt in raw_statements:
            stmt = stmt.strip()
            if stmt:
                statements.append(stmt)
                
        print(f"Loaded {len(statements)} SQL statements to execute.")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        for stmt in statements:
            # We skip 'USE medcompare' if we are already connected to it, 
            # but executing it is fine too.
            try:
                print(f"Executing: {stmt[:50]}...")
                cursor.execute(stmt)
            except Exception as e:
                # If ADD COLUMN IF NOT EXISTS is not supported, catch and print warning
                if "Duplicate column name" in str(e) or "already exists" in str(e):
                    print(f"Warning (ignored): {e}")
                else:
                    print(f"Error executing statement: {e}")
                    conn.rollback()
                    cursor.close()
                    conn.close()
                    sys.exit(1)
                    
        conn.commit()
        cursor.close()
        conn.close()
        print("Database migration v2 completed successfully!")

if __name__ == '__main__':
    run_migration()
