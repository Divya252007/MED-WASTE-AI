from auth import hash_password, verify_password

# Test password hashing
password = "Test@12345"

hashed_password = hash_password(password)

print("Original password:", password)
print("Hashed password:", hashed_password)

# Verify correct password
result1 = verify_password(password, hashed_password)

print("Correct password test:", result1)

# Verify incorrect password
result2 = verify_password("WrongPassword", hashed_password)

print("Wrong password test:", result2)