import hashlib
import argparse
import sys
from getpass import getpass
import sqlite3

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

# User access mapping
USER_ACCESS = {
    'administrator': 10,
    'manager': 5,
    'user': 3,
    'limited': 2,
    'guest': 1
}

def add_user(username, name, password, access='user'):
    """Add a new user or update password if user already exists"""
    try:
        conn = sqlite3.connect('fish.db')
        cursor = conn.cursor()
        
        hashed_password = hash_password(password)
        access_number = USER_ACCESS.get(access.lower(), 3)  # Default to 'user' access (3)
        
        # Check if user already exists
        cursor.execute('SELECT Username FROM People WHERE Username = ?', (username,))
        user_exists = cursor.fetchone() is not None
        
        if user_exists:
            # Update existing user's password and access
            cursor.execute(
                'UPDATE People SET Password = ?, Access = ? WHERE Username = ?',
                (hashed_password, access_number, username)
            )
            conn.commit()
            conn.close()
            print(f"✓ Password and access updated for user '{username}' (access: {access} = {access_number})!")
            return True
        else:
            # Insert new user
            cursor.execute(
                'INSERT INTO People (Name, Username, Password, Access) VALUES (?, ?, ?, ?)',
                (name, username, hashed_password, access_number)
            )
            conn.commit()
            conn.close()
            print(f"✓ User '{username}' added successfully with access '{access}' ({access_number})!")
            return True
            
    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        return False

def check_password(username, password):
    """Add a new user or update password if user already exists"""
    try:
        conn = sqlite3.connect('fish.db')
        cursor = conn.cursor()
        
        hashed_password = hash_password(password)
        
        # Check if user already exists
        cursor.execute('SELECT Username FROM People WHERE Username = ?', (username,))
        user_exists = cursor.fetchone() is not None
        
        if not user_exists:
            print(f"✗ Error: User '{username}' does not exist!")
            conn.close()
            return False

        cursor.execute('SELECT Password FROM People WHERE Username = ?', (username,))

        db_password = cursor.fetchone()[0]
        if hashed_password == db_password:
            print(f"✓ Password matches for user '{username}'!")
        else:
            print(f"✗ Password does not match for user '{username}': {hashed_password} != {db_password}!")

    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        return False

def remove_user(username):
    """Remove a user from the database"""
    try:
        conn = sqlite3.connect('fish.db')
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT Username FROM People WHERE Username = ?', (username,))
        if cursor.fetchone() is None:
            print(f"✗ Error: User '{username}' does not exist!")
            conn.close()
            return False
        
        # Delete the user
        cursor.execute('DELETE FROM People WHERE Username = ?', (username,))
        conn.commit()
        conn.close()
        
        print(f"✓ User '{username}' removed successfully!")
        return True
    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        return False

def list_users():
    """List all users in the database"""
    try:
        conn = sqlite3.connect('fish.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT Username, Name, Access FROM People ORDER BY username')
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            print("No users found in the database.")
            return
        
        # Reverse lookup for access names
        access_names = {v: k for k, v in USER_ACCESS.items()}
        print(access_names)

        print(f"\n{'ID':<5} {'Username':<20}: {'Name':<20} {'Access':<15} {'Access #':<8}")
        print("-" * 50)
        for username, Name, access in users:
            access_name = access_names.get(int(access), 'unknown')
            print(f"{username:<20}: {Name:<20} {access_name:<15} {access:<8}")
        print(f"\nTotal users: {len(users)}")
        
    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")

def main():
    parser = argparse.ArgumentParser(
        description='Manage users in the fish.db database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_users.py add john                          # Add user with default 'user' access
  python manage_users.py add john -p secret123             # Add user with password
  python manage_users.py add john -l administrator         # Add admin user
  python manage_users.py add jane -p pass456 -l manager    # Add manager with password
  python manage_users.py remove john                       # Remove user
  python manage_users.py list                              # List all users
  
User Access:
  administrator = 10, manager = 5, user = 3, limited = 2, guest = 1
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add user command
    add_parser = subparsers.add_parser('add', help='Add a new user')
    add_parser.add_argument('username', help='Username to add')
    add_parser.add_argument('name', help='Full name')
    add_parser.add_argument('-p', '--password', help='Password (will prompt if not provided)')
    add_parser.add_argument('-a', '--access', 
                           choices=['administrator', 'manager', 'user', 'limited', 'guest'],
                           default='user',
                           help='User access (default: user)')

    # Check user command
    check_parser = subparsers.add_parser('check', help='Check user password')
    check_parser.add_argument('username', help='Username to add')
    check_parser.add_argument('-p', '--password', help='Password (will prompt if not provided)')

    # Remove user command
    remove_parser = subparsers.add_parser('remove', help='Remove a user')
    remove_parser.add_argument('username', help='Username to remove')
    
    # List users command
    list_parser = subparsers.add_parser('list', help='List all users')
    
    args = parser.parse_args()
    
    # Check if database exists
    try:
        conn = sqlite3.connect('fish.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='People'")
        if cursor.fetchone() is None:
            print("✗ Error: People table does not exist. Run setup_db.py first!")
            conn.close()
            sys.exit(1)
        conn.close()
    except sqlite3.Error as e:
        print(f"✗ Error: Could not connect to database: {e}")
        sys.exit(1)
    
    # Execute commands
    if args.command == 'add':
        if args.password:
            password = args.password
        else:
            password = getpass('Enter password: ')
            password_confirm = getpass('Confirm password: ')
            
            if password != password_confirm:
                print("✗ Error: Passwords do not match!")
                sys.exit(1)
        
        if not password:
            print("✗ Error: Password cannot be empty!")
            sys.exit(1)
        
        add_user(args.username, args.name, password, args.access)
    
    elif args.command == 'check':
        if args.password:
            password = args.password
        else:
            password = getpass('Enter password: ')
            password_confirm = getpass('Confirm password: ')
            
            if password != password_confirm:
                print("✗ Error: Passwords do not match!")
                sys.exit(1)
        
        if not password:
            print("✗ Error: Password cannot be empty!")
            sys.exit(1)

        check_password(args.username, password)

    elif args.command == 'remove':
        confirm = input(f"Are you sure you want to remove user '{args.username}'? (yes/no): ")
        if confirm.lower() in ['yes', 'y']:
            remove_user(args.username)
        else:
            print("Operation cancelled.")
    
    elif args.command == 'list':
        list_users()
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()