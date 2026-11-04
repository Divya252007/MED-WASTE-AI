from database import get_connection

conn = get_connection()

try:
    conn.execute(
        """
        UPDATE users
        SET hospital_id = ?
        WHERE username = ?
        AND role = 'admin'
        """,
        (1, "medadmin")
    )

    conn.commit()

    admin = conn.execute(
        """
        SELECT user_id, username, hospital_id
        FROM users
        WHERE username = ?
        """,
        ("medadmin",)
    ).fetchone()

    print("Updated admin account:")
    print(dict(admin))

finally:
    conn.close()