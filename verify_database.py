import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "med_waste.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    AND name NOT LIKE 'sqlite_%'
""")

tables = cursor.fetchall()

print("\nMED WASTE AI - DATABASE VERIFICATION")
print("------------------------------------")

for table in tables:
    table_name = table[0]
    print(f"\nTable: {table_name}")

    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    for column in columns:
        print(f"  - {column[1]}")

print("\nTotal tables created:", len(tables))

conn.close()