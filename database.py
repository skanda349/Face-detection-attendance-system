import mysql.connector

def connect():
    return mysql.connector.connect(
        host="localhost",
        user="root",        # change if needed
        password="",    # your MySQL password
        database="attendance_system"
    )


def create_database():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="attendance_system"
    )
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS attendance_system")
    conn.close()


def create_tables():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user (
        userId VARCHAR(50),
        email VARCHAR(100),
        face_encoding LONGBLOB
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        userId VARCHAR(50),
        email VARCHAR(100),
        date DATE,
        attendance_status VARCHAR(20)
    )
    """)

    conn.commit()
    conn.close()