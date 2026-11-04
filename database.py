import sqlite3
from pathlib import Path

# Database file location
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "med_waste.db"


# Connect to database
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Create all required tables
def init_db():

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Hospitals table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (
            hospital_id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_name TEXT NOT NULL,
            address TEXT,
            city TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 2. Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (
                role IN ('admin', 'doctor', 'staff', 'driver')
            ),
            hospital_id INTEGER,
            phone TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hospital_id)
                REFERENCES hospitals(hospital_id)
        )
        """)

        # 3. Waste records table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS waste_records (
            waste_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            hospital_id INTEGER NOT NULL,
            waste_weight REAL NOT NULL,
            colour_category TEXT NOT NULL CHECK (
                colour_category IN ('Yellow', 'Red', 'White', 'Blue')
            ),
            waste_materials TEXT NOT NULL,
            facility_type TEXT,
            facility_name TEXT,
            facility_location TEXT,
            image_path TEXT,
            ai_suggested_category TEXT,
            verification_status TEXT DEFAULT 'Pending',
            collection_status TEXT DEFAULT 'Not Requested',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (hospital_id)
                REFERENCES hospitals(hospital_id)
        )
        """)

        # 4. QR records table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS qr_records (
            qr_id INTEGER PRIMARY KEY AUTOINCREMENT,
            waste_id INTEGER NOT NULL UNIQUE,
            qr_code_path TEXT NOT NULL,
            qr_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (waste_id)
                REFERENCES waste_records(waste_id)
        )
        """)

        # 5. Verification history
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_history (
            verification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            waste_id INTEGER NOT NULL,
            verifier_id INTEGER NOT NULL,
            decision TEXT NOT NULL CHECK (
                decision IN ('Approved', 'Rejected', 'Correction Requested')
            ),
            reason TEXT,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (waste_id)
                REFERENCES waste_records(waste_id),
            FOREIGN KEY (verifier_id)
                REFERENCES users(user_id)
        )
        """)

        # 6. Collection requests
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS collection_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            waste_id INTEGER NOT NULL,
            requested_by INTEGER NOT NULL,
            assigned_driver INTEGER,
            status TEXT DEFAULT 'Requested',
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (waste_id)
                REFERENCES waste_records(waste_id),
            FOREIGN KEY (requested_by)
                REFERENCES users(user_id),
            FOREIGN KEY (assigned_driver)
                REFERENCES users(user_id)
        )
        """)

        # 7. Transportation logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transport_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            driver_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            location_updated_at TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (request_id)
                REFERENCES collection_requests(request_id),
            FOREIGN KEY (driver_id)
                REFERENCES users(user_id)
        )
        """)

        # 8. Notifications
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            related_waste_id INTEGER,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (related_waste_id)
                REFERENCES waste_records(waste_id)
        )
        """)

        # 9. Activity logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)

        # 10. Add Gemini AI result columns
        cursor.execute("PRAGMA table_info(waste_records)")
        existing_columns = {
            row["name"] for row in cursor.fetchall()
        }

        if "ai_explanation" not in existing_columns:
            cursor.execute("""
                ALTER TABLE waste_records
                ADD COLUMN ai_explanation TEXT
            """)

        if "ai_confidence" not in existing_columns:
            cursor.execute("""
                ALTER TABLE waste_records
                ADD COLUMN ai_confidence TEXT
            """)

        # 11. Add location column to users
        cursor.execute("PRAGMA table_info(users)")
        user_columns = {
            row["name"] for row in cursor.fetchall()
        }

        if "location" not in user_columns:
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN location TEXT
            """)

        # 12. Add driver assignment response columns
        cursor.execute("PRAGMA table_info(collection_requests)")
        request_columns = {
            row["name"] for row in cursor.fetchall()
        }

        if "driver_response" not in request_columns:
            cursor.execute("""
                ALTER TABLE collection_requests
                ADD COLUMN driver_response TEXT DEFAULT 'Pending'
            """)

        if "driver_response_at" not in request_columns:
            cursor.execute("""
                ALTER TABLE collection_requests
                ADD COLUMN driver_response_at TIMESTAMP
            """)

        conn.commit()
        print("DATABASE UPDATED SUCCESSFULLY")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()