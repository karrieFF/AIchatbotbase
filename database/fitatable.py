"""
Example: Creating a table using the connection pool pattern
This follows the same pattern as db_sync.py
"""

import os
from psycopg2.pool import ThreadedConnectionPool
from typing import Optional

# parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# if parent_dir not in sys.path:
#     sys.path.insert(0, parent_dir)

import database.db_sync as db

def create_activity_table():
    """Create the activity_data table using connection pool"""
    if db.pg_pool is None:
        raise RuntimeError("Connection pool not initialized. Call init_pool() first.")
    
    conn = db.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            # Create table SQL
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS activity_data (
                id BIGSERIAL PRIMARY KEY,
                user_id UUID NOT NULL,
                activity_date DATE NOT NULL,
                total_steps INTEGER,
                total_distance DECIMAL(10, 2),
                tracker_distance DECIMAL(10, 2),
                logged_activities_distance DECIMAL(10, 2),
                very_active_distance DECIMAL(10, 2),
                moderately_active_distance DECIMAL(10, 2),
                light_active_distance DECIMAL(10, 2),
                sedentary_active_distance DECIMAL(10, 2),
                very_active_minutes INTEGER,
                fairly_active_minutes INTEGER,
                lightly_active_minutes INTEGER,
                sedentary_minutes INTEGER,
                calorie INTEGER,
                calories_bmr INTEGER,
                marginal_calories INTEGER,
                resting_heart_rate INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
            
            # Create index
            create_index_sql = """
            CREATE INDEX IF NOT EXISTS idx_activity_date 
            ON activity_data (activity_date);
            """
            
            cur.execute(create_table_sql)
            cur.execute(create_index_sql)
        conn.commit()
        print("✓ Table 'activity_data' created successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"⚠ Error creating table: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        pg_pool.putconn(conn)

def fitbit_id_map_table():
    if db.pg_pool is None:
        raise RuntimeError("Connection pool not initialized. Call init_pool() first.")
    
    conn = db.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            # Create table SQL
            create_table2 = """
            CREATE TABLE IF NOT EXISTS fitbit_id_map (
                fitbit_id   TEXT PRIMARY KEY,             -- id from Fitbit / Fitabase CSV
                user_id  UUID NOT NULL,              -- global id from registered.id
                email    TEXT NOT NULL UNIQUE,
                created_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT activity_data
                    FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
            # Create index
            create_index2 = """
            CREATE INDEX IF NOT EXISTS idx_map_date 
            ON fitbit_id_map (fitbit_id);
            """
            cur.execute(create_table2)
            cur.execute(create_index2)

        conn.commit()
        print("✓ Table 'fitbit_id_map' created successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"⚠ Error creating table: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        pg_pool.putconn(conn)


if __name__ == "__main__":
    # Initialize pool
    db.init_sync_pool()
    
    try:
        # Create table
        #create_activity_table()
        fitbit_id_map_table()
    finally:
        # Close pool when done
        db.close_sync_pool()

