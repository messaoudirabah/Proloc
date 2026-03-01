import sqlite3

DB_NAME = "car_rental.db"

def get_db_connection():
    return sqlite3.connect(DB_NAME)

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users (for login)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # Cars
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model TEXT,
        brand TEXT,
        year INTEGER,
        status TEXT
    )
    """)

    # Clients
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        phone TEXT
    )
    """)

    # Reservations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        car_id INTEGER,
        start_date TEXT,
        end_date TEXT,
        total_price REAL,
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (car_id) REFERENCES cars(id)
    )
    """)

    # Invoices
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reservation_id INTEGER,
        amount REAL,
        date TEXT,
        FOREIGN KEY (reservation_id) REFERENCES reservations(id)
    )
    """)

    # Insert default admin if not exists
    cursor.execute("SELECT * FROM users WHERE username=?", ("admin",))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", "admin"))

    conn.commit()
    conn.close()
