from werkzeug.security import generate_password_hash

# Generate a fresh hash using your system's active library
new_hash = generate_password_hash("admin123")
print("\n--- COPY THE HASH BELOW ---")
print(new_hash)
print("---------------------------\n")