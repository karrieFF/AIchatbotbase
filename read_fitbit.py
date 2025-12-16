import csv
import os 
import sys
from datetime import datetime
from dotenv import load_dotenv
import database.db_sync as db

# parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# if parent_dir not in sys.path:
#     sys.path.insert(0, parent_dir)

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

activity_path = "C:/fitbitdata/20251214.csv"
match_path = "C:/fitbitdata/match.csv"

def import_fitbit_id_map():
    if db.pg_pool is None:
        raise RuntimeError("pg_pool not initialized. Call init_sync_pool() first.")

    conn = db.pg_pool.getconn()
    try:

        with conn.cursor() as cur:
            cur.execute("SELECT id, email From users;")
            rows = cur.fetchall()
            email_to_id = {email.lower(): user_id for (user_id, email) in rows}

            with open(match_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                #print(reader.fieldnames)
                reader.fieldnames = [name.lstrip("\ufeff") for name in reader.fieldnames] ## Clean BOM from all header names
                for row in reader:
                    fitbit_id = row["mid"].strip()
                    email = row["email"].strip()

                    user_id = email_to_id.get(email.lower())
                    if user_id is None:
                        print(f"[WARN] No registered user for email {email}, skipping mapping")
                        continue

                    cur.execute(
                        """
                        INSERT INTO fitbit_id_map (fitbit_id, user_id, email)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (fitbit_id) DO UPDATE
                        SET user_id = EXCLUDED.user_id,
                            email = EXCLUDED.email;
                        """,
                        (fitbit_id, user_id, email)
                    )
        conn.commit()
        print("fitbit_id_map imported successfully!")

    finally:
        db.pg_pool.putconn(conn)

def import_activity_data():
    if db.pg_pool is None:
        raise RuntimeError("pg_pool not initialized. Call init_sync_pool() first.")

    conn = db.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            #Preload fitbit_id > user_id mapping 
            cur.execute("SELECT fitbit_id, user_id FROM fitbit_id_map;")
            rows = cur.fetchall()
            fitbit_to_userid = {fitbit_id: user_id for (fitbit_id, user_id) in rows}

            with open(activity_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                reader.fieldnames = [name.lstrip("\ufeff") for name in reader.fieldnames] ## Clean BOM from all header names

                for row in reader:
                    fitbit_id = row["Id"].strip()
                    user_id = fitbit_to_userid.get(fitbit_id)
                    if user_id is None:
                        print(f"[WARN] No fitbit_id mapping found for {fitbit_id}, skipping activity data")
                        continue
                    
                    activity_date = datetime.strptime(row["ActivityDate"], "%m/%d/%Y").date()
                    total_steps = int(row["TotalSteps"]) if row["TotalSteps"] else None
                    total_distance = float(row["TotalDistance"]) if row["TotalDistance"] else None
                    tracker_distance = float(row["TrackerDistance"]) if row["TrackerDistance"] else None
                    logged_activities_distance = float(row["LoggedActivitiesDistance"]) if row["LoggedActivitiesDistance"] else None
                    very_active_distance = float(row["VeryActiveDistance"]) if row["VeryActiveDistance"] else None
                    moderately_active_distance = float(row["ModeratelyActiveDistance"]) if row["ModeratelyActiveDistance"] else None
                    light_active_distance = float(row["LightActiveDistance"]) if row["LightActiveDistance"] else None
                    sedentary_active_distance = float(row["SedentaryActiveDistance"]) if row["SedentaryActiveDistance"] else None
                    very_active_minutes = int(row["VeryActiveMinutes"]) if row["VeryActiveMinutes"] else None
                    fairly_active_minutes = int(row["FairlyActiveMinutes"]) if row["FairlyActiveMinutes"] else None
                    lightly_active_minutes = int(row["LightlyActiveMinutes"]) if row["LightlyActiveMinutes"] else None
                    sedentary_minutes = int(row["SedentaryMinutes"]) if row["SedentaryMinutes"] else None
                    calorie = int(row["Calories"]) if row["Calories"] else None
                    calories_bmr = int(row["CaloriesBMR"]) if row["CaloriesBMR"] else None
                    marginal_calories = int(row["MarginalCalories"]) if row["MarginalCalories"] else None
                    resting_heart_rate = int(row["RestingHeartRate"]) if row["RestingHeartRate"] else None

                    cur.execute(
                        """
                        INSERT INTO activity_data(fitbit_id, user_id, activity_date, total_steps, total_distance, tracker_distance, logged_activities_distance, very_active_distance, moderately_active_distance, light_active_distance, sedentary_active_distance, very_active_minutes, fairly_active_minutes, lightly_active_minutes, sedentary_minutes, calorie, calories_bmr, marginal_calories, resting_heart_rate)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, activity_date) DO UPDATE
                        SET 
                            fitbit_id = EXCLUDED.fitbit_id,
                            total_steps = EXCLUDED.total_steps,
                            total_distance = EXCLUDED.total_distance,
                            tracker_distance = EXCLUDED.tracker_distance,
                            logged_activities_distance = EXCLUDED.logged_activities_distance,
                            very_active_distance = EXCLUDED.very_active_distance,
                            moderately_active_distance = EXCLUDED.moderately_active_distance,
                            light_active_distance = EXCLUDED.light_active_distance,
                            sedentary_active_distance = EXCLUDED.sedentary_active_distance,
                            very_active_minutes = EXCLUDED.very_active_minutes,
                            fairly_active_minutes = EXCLUDED.fairly_active_minutes,
                            lightly_active_minutes = EXCLUDED.lightly_active_minutes,
                            sedentary_minutes = EXCLUDED.sedentary_minutes,
                            calorie = EXCLUDED.calorie,
                            calories_bmr = EXCLUDED.calories_bmr,
                            marginal_calories = EXCLUDED.marginal_calories,
                            resting_heart_rate = EXCLUDED.resting_heart_rate;
                        """,
                        (fitbit_id, user_id, activity_date, total_steps, total_distance, tracker_distance, logged_activities_distance, very_active_distance, moderately_active_distance, light_active_distance, sedentary_active_distance, very_active_minutes, fairly_active_minutes, lightly_active_minutes, sedentary_minutes, calorie, calories_bmr, marginal_calories, resting_heart_rate)
                    )
                conn.commit()
                print("Activity data imported successfully!")
    finally:
        db.pg_pool.putconn(conn)

if __name__ == "__main__":
    db.init_sync_pool()
    
    try:
        import_fitbit_id_map()
        import_activity_data()
    finally:
        db.close_sync_pool()