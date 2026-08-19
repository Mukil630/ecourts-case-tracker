import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import datetime
from app.db.database import get_db_connection, get_current_ist_date
from app.config import Config

def update_dates_to_today():
    today = get_current_ist_date()
    today_dt = datetime.datetime.strptime(today, "%Y-%m-%d").date()
    tomorrow = (today_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    in_2d = (today_dt + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
    in_3d = (today_dt + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    in_5d = (today_dt + datetime.timedelta(days=5)).strftime("%Y-%m-%d")
    in_7d = (today_dt + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    in_10d = (today_dt + datetime.timedelta(days=10)).strftime("%Y-%m-%d")
    in_14d = (today_dt + datetime.timedelta(days=14)).strftime("%Y-%m-%d")
    past_date = (today_dt - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Today's Court Hearing Board Cases (14 Cases across Karur Courts)
    today_cnrs = [
        "TNKR010010352023", "TNKR020003832025", "TNKR030000252025",
        "TNKR040003612025", "TNKR050003592024", "TNKR050001392021",
        "TNKR090000692024", "TNKR090001392025", "TNKR090003952025",
        "TNKR090008312025", "TNKR090005552023", "TNKR090000942025",
        "TNKR090004662025", "TNKR090000722021"
    ]
    for cnr in today_cnrs:
        cursor.execute("UPDATE cases SET next_hearing_date = ?, case_status = 'PENDING' WHERE cnr_number = ?", (today, cnr))

    # 2. Tomorrow's Evening Docket (6 Cases)
    tomorrow_cnrs = [
        "TNKR030006182025", "TNKR010016322026", "TNKR030000132026",
        "TNKR030007162025", "TNKR030016152025", "TNKR040004462024"
    ]
    for cnr in tomorrow_cnrs:
        cursor.execute("UPDATE cases SET next_hearing_date = ?, case_status = 'PENDING' WHERE cnr_number = ?", (tomorrow, cnr))

    # 3. Upcoming Confirmed Hearings Pipeline (Next 2 - 14 Days)
    pipeline_mappings = [
        (in_2d, ["TNKR030006732025", "TNKR030007322025", "TNKR030008432025"]),
        (in_3d, ["TNKR030008982025", "TNKR030009772025"]),
        (in_5d, ["TNKR030010832025", "TNKR030011532025"]),
        (in_7d, ["TNKR030012252025", "TNKR030012872025", "TNKR030013622025"]),
        (in_10d, ["TNKR030014372025", "TNKR030015092025"]),
        (in_14d, ["TNKR030015842025", "TNKR030016592025"])
    ]
    for d, cnrs in pipeline_mappings:
        for cnr in cnrs:
            cursor.execute("UPDATE cases SET next_hearing_date = ?, case_status = 'PENDING' WHERE cnr_number = ?", (d, cnr))

    # 4. Disposed Cases
    cursor.execute("UPDATE cases SET next_hearing_date = ?, case_status = 'DISPOSED' WHERE case_title LIKE '%DISPOSED%' OR cnr_number IN ('TNKR030017342025', 'TNKR030018092025')", (past_date,))

    # 5. Populate Case History Logs with Adjournments / Re-schedulings
    cursor.execute("DELETE FROM case_history_logs")
    sample_logs = [
        ("TNKR090000692024", past_date, today, "Written Statement Filed - Trial date fixed"),
        ("TNKR050003592024", past_date, today, "Defendant appearance awaited - Matter taken up"),
        ("TNKR020003832025", past_date, today, "NBW re-issued to respondent"),
        ("TNKR030006182025", today, tomorrow, "Adjourned on request of respondent advocate"),
        ("TNKR010016322026", today, tomorrow, "For framing of issues by Learned Judge"),
        ("TNKR030007322025", today, in_2d, "Counter statement extended by 2 days"),
        ("TNKR030009772025", today, in_3d, "Pre-trial compromise memo scheduled")
    ]
    for cnr, prev, nxt, det in sample_logs:
        cursor.execute("""
            INSERT INTO case_history_logs (cnr_number, change_type, previous_hearing_date, new_hearing_date, details, notified, detected_at)
            VALUES (?, 'HEARING_DATE', ?, ?, ?, 0, CURRENT_TIMESTAMP)
        """, (cnr, prev, nxt, det))

    conn.commit()
    conn.close()

    print(f"Successfully synchronized case dates and hearing pipeline! Today (IST) is: {today}")

if __name__ == "__main__":
    update_dates_to_today()
