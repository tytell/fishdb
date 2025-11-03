import hashlib
import argparse
import sys
from getpass import getpass
from supabase import create_client, Client
import toml

def load_secrets():
    """Load database credentials from secrets.toml"""
    try:
        secrets = toml.load('.streamlit/secrets.toml')
        db_url = secrets.get('DB_URL')
        db_key = secrets.get('DB_KEY')
        
        if not db_url or not db_key:
            print("✗ Error: DB_URL and DB_KEY must be set in secrets.toml!")
            sys.exit(1)
        
        return db_url, db_key
    except FileNotFoundError:
        print("✗ Error: .streamlit/secrets.toml file not found!")
        print("  Please create the file with DB_URL and DB_KEY.")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error loading secrets: {e}")
        sys.exit(1)

def get_supabase_client():
    """Get Supabase client connection"""
    db_url, db_key = load_secrets()
    return create_client(db_url, db_key)

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
        supabase = get_supabase_client()
        
        hashed_password = hash_password(password)
        access_number = USER_ACCESS.get(access.lower(), 3)  # Default to 'user' access (3)
        
        # Check if user already exists
        response = supabase.table('People').select('username').eq('username', username).execute()
        user_exists = len(response.data) > 0
        
        if user_exists:
            # Update existing user's password and level
            response = supabase.table('People').update({
                'password': hashed_password,
                'access': access_number
            }).eq('username', username).execute()
            
            print(f"✓ Password and level updated for user '{username}' (access: {access} = {access_number})!")
            return True
        else:
            # Insert new user
            response = supabase.table('People').insert({
                'full_name': name,
                'username': username,
                'password': hashed_password,
                'access': access_number
            }).execute()
            
            print(f"✓ User '{username}' added successfully with level '{access}' ({access_number})!")
            return True
            
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

def remove_user(username):
    """Remove a user from the database"""
    try:
        supabase = get_supabase_client()
        
        # Check if user exists
        response = supabase.table('People').select('username').eq('username', username).execute()

        if len(response.data) == 0:
            print(f"✗ Error: User '{username}' does not exist!")
            return False
        
        # Delete the user
        response = supabase.table('People').delete().eq('username', username).execute()
        
        print(f"✓ User '{username}' removed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

def list_users():
    """List all users in the database"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('People').select('full_name, username, access').order('username').execute()
        users = response.data
        
        if not users:
            print("No users found in the database.")
            return
        
        # Reverse lookup for access level names
        access_names = {v: k for k, v in USER_ACCESS.items()}
        
        print(f"\n{'Name':<30} {'Username':<20} {'Access':<15} {'Access #':<8}")
        print("-" * 50)
        for user in users:
            access_name = access_names.get(user['access'], 'unknown')
            print(f"{user['full_name']:<30} {user['username']:<20} {access_name:<15} {user['access']:<8}")
        print(f"\nTotal users: {len(users)}")
        
    except Exception as e:
        print(f"✗ Database error: {e}")

def check_password(username, password):
    """Check if the provided password matches the user's stored password"""
    try:
        supabase = get_supabase_client()
        
        # Get user from database
        response = supabase.table('People').select('username, password').eq('username', username).execute()
        
        if len(response.data) == 0:
            print(f"✗ Error: User '{username}' does not exist!")
            return False
        
        user = response.data[0]
        stored_password = user['password']
        hashed_input = hash_password(password)
        
        if stored_password == hashed_input:
            print(f"✓ Password matches for user '{username}'!")
            return True
        else:
            print(f"✗ Password does NOT match for user '{username}'!")
            return False
            
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Manage users in the fish.db database',
        formatter_class=argparse.RawDescriptionHelpFormatter
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
    
    # Check if database connection works
    try:
        supabase = get_supabase_client()
        # Test connection by trying to query People table
        supabase.table('People').select('username').limit(1).execute()
    except Exception as e:
        print(f"✗ Error: Could not connect to database: {e}")
        print("  Please check your DB_URL and DB_KEY in .streamlit/secrets.toml")
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