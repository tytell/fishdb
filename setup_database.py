import sys
import toml
import sqlite3

def load_db_password():
    """Load database password from secrets.toml"""
    try:
        secrets = toml.load('.streamlit/secrets.toml')
        return secrets['DB_PASSWORD']
    except FileNotFoundError:
        print("✗ Error: .streamlit/secrets.toml file not found!")
        print("  Please create the file with DB_PASSWORD key.")
        sys.exit(1)
    except KeyError:
        print("✗ Error: DB_PASSWORD not found in secrets.toml!")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error loading secrets: {e}")
        sys.exit(1)

def setup_database():
    """Create and populate the Sqlite database with tables and foreign keys"""
    
    # Connect to sqlite (creates file if it doesn't exist)
    conn = sqlite3.connect('fish.db')
    cursor = conn.cursor()
    
    print("Creating database structure...")
    
    # Create Systems table (no foreign keys)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Systems (
            Name TEXT PRIMARY KEY,
            MaxVolume DOUBLE,
            Active INTEGER
        )
    ''')
    print("✓ Created Systems table")
    
    # Create Tanks table with foreign key to Systems
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Tanks (
            Name TEXT PRIMARY KEY,
            System TEXT,
            Volume DOUBLE,
            Shelf TEXT,
            Divisions INTEGER,
            Notes TEXT, 
            FOREIGN KEY(System) REFERENCES Systems(Name)
        )
    ''')
    print("✓ Created Tanks table with foreign key to Systems")

    # Create Species table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Species (
            Name TEXT PRIMARY KEY,
            Common_name TEXT,
            NumAllowed INTEGER,
            Date_Approved DATE,
            Date_Expires DATE,
            Protocol TEXT
        )
    ''')
    print("✓ Created Fish table with foreign key to Tanks")

    # Create Fish table with foreign key to Tanks
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Fish (
            ID TEXT PRIMARY KEY,
            Tank TEXT,
            Species TEXT,
            Status TEXT,
            FOREIGN KEY(Tank) REFERENCES Tanks(Name),
            FOREIGN KEY(Species) REFERENCES Species(Name)
        )
    ''')
    print("✓ Created Fish table with foreign key to Tanks")
    
    # Create People table for authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS People (
            Name TEXT PRIMARY KEY,
            Username TEXT UNIQUE NOT NULL,
            Password TEXT NOT NULL,
            Access INTEGER DEFAULT 3,
            Level TEXT,
            Active BOOL,
            Email TEXT,
            NonTufts_Email TEXT,
            MobilePhone TEXT,
            Notes TEXT
        )
    ''')
    print("✓ Created People table")

    # Create Feeding table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Feeding (
            Date DATETIME PRIMARY KEY,
            Fish TEXT NOT NULL,
            Fed BOOL,
            Ate BOOL,
            Notes TEXT,
            Person TEXT,
            FOREIGN KEY(Fish) REFERENCES Fish(ID),
            FOREIGN KEY(Person) REFERENCES People(Name)
        )
    ''')
    print("✓ Created Feeding table")

    # Create Health table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Health (
            Date DATETIME PRIMARY KEY,
            Fish TEXT NOT NULL,
            Notes TEXT,
            StartTreatment TEXT,
            EndTreatment TEXT,
            FromTank TEXT,
            ToTank TEXT,
            ChangeStatus TEXT,
            Person TEXT,
            FOREIGN KEY(Fish) REFERENCES Fish(ID),
            FOREIGN KEY(FromTank) REFERENCES Tanks(Name),
            FOREIGN KEY(ToTank) REFERENCES Tanks(Name),
            FOREIGN KEY(Person) REFERENCES People(Name)
        )
    ''')
    print("✓ Created Health table")

    # Create WaterQuality table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS WaterQuality (
            Date DATETIME PRIMARY KEY,
            System TEXT,
            Tank TEXT,
            Notes TEXT,
            Conductivity DOUBLE,
            pH DOUBLE,
            Ammonia DOUBLE,
            Nitrite DOUBLE,
            Nitrate DOUBLE,
            WaterChangePct DOUBLE,
            Person TEXT,
            FOREIGN KEY(System) REFERENCES Systems(Name),
            FOREIGN KEY(Tank) REFERENCES Tanks(Name),
            FOREIGN KEY(Person) REFERENCES People(Name)
        )
    ''')
    print("✓ Created WaterQuality table")

    # Create Maintenance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Maintenance (
            Date DATETIME PRIMARY KEY,
            System TEXT,
            Tank TEXT,
            Task TEXT,
            Notes TEXT,
            Person TEXT,
            FOREIGN KEY(System) REFERENCES Systems(Name),
            FOREIGN KEY(Tank) REFERENCES Tanks(Name),
            FOREIGN KEY(Person) REFERENCES People(Name)
        )
    ''')
    print("✓ Created Maintenance table")

    # Create Experiments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Experiments (
            Date DATETIME PRIMARY KEY,
            Fish TEXT NOT NULL,
            Details TEXT,
            Person TEXT,
            FOREIGN KEY(Fish) REFERENCES Fish(ID),
            FOREIGN KEY(Person) REFERENCES People(Name)
        )
    ''')
    print("✓ Created Maintenance table")
    
    conn.commit()
    conn.close()
    print("\n✓ Database setup complete! File: fish.duckdb")

if __name__ == '__main__':
    setup_database()
