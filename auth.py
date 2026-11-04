import bcrypt
from database import get_connection


def hash_password(password):
    password_bytes = password.encode("utf-8")

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hashed.decode("utf-8")


def verify_password(password, stored_hash):
    password_bytes = password.encode("utf-8")
    hash_bytes = stored_hash.encode("utf-8")

    return bcrypt.checkpw(password_bytes, hash_bytes)


def create_user(
    full_name,
    username,
    password,
    role,
    hospital_id=None,
    phone=None,
    location=None
):
    allowed_roles = ["admin", "doctor", "staff", "driver"]

    if role not in allowed_roles:
        return False, "Invalid user role."

    if not full_name.strip() or not username.strip():
        return False, "Name and username are required."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    password_hash = hash_password(password)

    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO users (
                full_name,
                username,
                password_hash,
                role,
                hospital_id,
                phone,
                location
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                full_name.strip(),
                username.strip(),
                password_hash,
                role,
                hospital_id,
                phone,
                location
            )
        )

        conn.commit()
        return True, "User created successfully."

    except Exception as error:
        print("User creation error:", error)
        return False, "Could not create user. Check whether the username already exists."

    finally:
        conn.close()


def login_user(username, password):
    conn = get_connection()

    try:
        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            AND is_active = 1
            """,
            (username.strip(),)
        ).fetchone()

        if user is None:
            return None

        if verify_password(password, user["password_hash"]):
            return {
                "user_id": user["user_id"],
                "full_name": user["full_name"],
                "username": user["username"],
                "role": user["role"],
                "hospital_id": user["hospital_id"],
                "location": user["location"]
            }

        return None

    finally:
        conn.close()


def admin_exists():
    conn = get_connection()

    count = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role='admin'"
    ).fetchone()[0]

    conn.close()
    return count > 0


def create_first_admin(full_name, username, password, phone=None):
    if admin_exists():
        return False, "Admin already exists."

    return create_user(
        full_name=full_name,
        username=username,
        password=password,
        role="admin",
        phone=phone
    )