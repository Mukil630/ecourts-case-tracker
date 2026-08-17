import datetime
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "cases.db")

today = datetime.date.today().strftime("%Y-%m-%d")
tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
in_2d = (datetime.date.today() + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
in_5d = (datetime.date.today() + datetime.timedelta(days=5)).strftime("%Y-%m-%d")
past = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Set pending today's cases to today's real date
cursor.execute("UPDATE cases SET next_hearing_date = ? WHERE case_status = 'PENDING'", (today,))

# Set upcoming cases to tomorrow and in 2 days
cursor.execute("UPDATE cases SET next_hearing_date = ? WHERE case_number_formatted = 'HMA/245/2024'", (tomorrow,))
cursor.execute("UPDATE cases SET next_hearing_date = ? WHERE case_number_formatted = 'OS/842/2024'", (in_2d,))

# Set disposed cases to past date
cursor.execute("UPDATE cases SET next_hearing_date = ? WHERE case_status = 'DISPOSED'", (past,))

conn.commit()
conn.close()

print(f"Successfully updated case dates. Today is: {today}")
