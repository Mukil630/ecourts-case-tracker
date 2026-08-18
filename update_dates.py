import datetime
import sqlite3
import os
from db import DB_PATH, get_current_ist_date

today = get_current_ist_date()
today_dt = datetime.datetime.strptime(today, "%Y-%m-%d").date()
tomorrow = (today_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
in_2d = (today_dt + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
in_5d = (today_dt + datetime.timedelta(days=5)).strftime("%Y-%m-%d")
past = (today_dt - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Set pending today's cases to today's real IST date
cursor.execute("UPDATE cases SET next_hearing_date = ? WHERE case_status = 'PENDING'", (today,))

# Set upcoming cases to tomorrow and in 2 days
cursor.execute("UPDATE cases SET next_hearing_date = ? WHERE case_number_formatted = 'HMA/245/2024'", (tomorrow,))
cursor.execute("UPDATE cases SET next_hearing_date = ? WHERE case_number_formatted = 'OS/842/2024'", (in_2d,))

# Set disposed cases to past date
cursor.execute("UPDATE cases SET next_hearing_date = ? WHERE case_status = 'DISPOSED'", (past,))

conn.commit()
conn.close()

print(f"Successfully updated case dates. Today (IST) is: {today}")
