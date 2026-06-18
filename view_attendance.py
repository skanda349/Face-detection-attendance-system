from database import connect

def view_attendance(date):
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT userId, email, date, attendance_status FROM attendance
        WHERE date = %s ORDER BY userId
        """, (date,))
        records = cursor.fetchall()
        conn.close()
        return records, None
    except Exception as e:
        return None, f"Error: {str(e)}"
