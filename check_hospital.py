from database import get_connection

conn = get_connection()

print("\nREGISTERED HOSPITALS")

hospitals = conn.execute(
    "SELECT hospital_id, hospital_name FROM hospitals"
).fetchall()

for hospital in hospitals:
    print(dict(hospital))

print("\nADMIN ACCOUNTS")

admins = conn.execute(
    """
    SELECT user_id, full_name, username, hospital_id
    FROM users
    WHERE role = 'admin'
    """
).fetchall()

for admin in admins:
    print(dict(admin))

conn.close()