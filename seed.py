import getpass
import sys
from di import container
from services import AuthService
from database import Database

def seed_user():
    print("--- Create New User ---")
    
    # 1. Initialize Database (ensure tables exist)
    try:
        db = container.resolve(Database)
        db.init_tables()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return

    # 2. Resolve the Auth Service
    auth_service = container.resolve(AuthService)

    # 3. Prompt for credentials
    username = input("Enter username: ").strip()
    if not username:
        print("Error: Username cannot be empty.")
        return

    # getpass hides the input characters
    password = getpass.getpass("Enter password: ").strip()
    if not password:
        print("Error: Password cannot be empty.")
        return

    confirm_password = getpass.getpass("Confirm password: ").strip()
    if password != confirm_password:
        print("Error: Passwords do not match!")
        return

    # 4. Create the user
    print(f"\nAttempting to create user '{username}'...")
    success = auth_service.create_user(username, password, role="user")

    if success:
        print(f"✅ Success! User '{username}' created.")
    else:
        print(f"❌ Error: User '{username}' already exists.")

if __name__ == "__main__":
    seed_user()
