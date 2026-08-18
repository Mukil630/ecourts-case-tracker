import datetime
from typing import Optional
from app.db.database import get_db_connection

def ensure_today_hearings_synchronized(db_path: Optional[str] = None):
    """No-op: Does NOT overwrite real case dates artificially."""
    pass

def import_karur_sample_data(db_path: Optional[str] = None):
    """Pre-populates the accurate 14 Karur Court hearings with their real dates (2026-08-14)."""
    sample_hearings = [
        {
            "cnr_number": "TNKR010010352023",
            "case_number_formatted": "STC/1035/2023",
            "case_title": "M Palanisamy vs M Velmurugan",
            "court_name": "Chief Judicial Magistrate Court, Karur",
            "court_room": "Room 8",
            "item_number": "4",
            "judge_name": "M. CHARLES ALBERT, Judicial Magistrate No.II",
            "case_stage": "Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "M Palanisamy",
            "client_phone": "+919443322110",
            "notes": "Complainant evidence cross examination"
        },
        {
            "cnr_number": "TNKR020003832025",
            "case_number_formatted": "STC/383/2025",
            "case_title": "G Eniyavan vs D Jeevanandham",
            "court_name": "Fast Track Court at Magisterial Level, Karur",
            "court_room": "Room 10",
            "item_number": "174",
            "judge_name": "Thiru R.Mahesh, B.A., LL.B(Hons)., LL.M.",
            "case_stage": "Service Pending - Warrant",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "G Eniyavan",
            "client_phone": "+919842112233",
            "notes": "NBW execution pending"
        },
        {
            "cnr_number": "TNKR030000252025",
            "case_number_formatted": "EP/25/2025",
            "case_title": "Shalini vs Managing Director TNSTC & 3 Ors",
            "court_name": "Mahila Court, Karur",
            "court_room": "Room 9",
            "item_number": "2",
            "judge_name": "Thiru P.Thangavel, B.Sc., LL.M., Sessions Judge",
            "case_stage": "For Attachment / Arrest / Deposit",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "Shalini",
            "client_phone": "+919789012345",
            "notes": "Execution petition for deposit"
        },
        {
            "cnr_number": "TNKR040003612025",
            "case_number_formatted": "OS/361/2025",
            "case_title": "S Nirmala vs C Velusamy & 10 Ors",
            "court_name": "Principal District Court, Karur",
            "court_room": "Room 1",
            "item_number": "108",
            "judge_name": "Tmt. S.SUMATHY, M.L., District Judge",
            "case_stage": "IA Pending",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "S Nirmala",
            "client_phone": "+919655443322",
            "notes": "Injunction application hearing"
        },
        {
            "cnr_number": "TNKR050003592024",
            "case_number_formatted": "OS/359/2024",
            "case_title": "State Bank of India vs M/s Kathiravan Tea Stall",
            "court_name": "Principal District Munsif Court, Karur",
            "court_room": "Room 5",
            "item_number": "16",
            "judge_name": "Thiru. N.Nilaveshwaran, B.A., B.L.",
            "case_stage": "Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "Kathiravan (Proprietor)",
            "client_phone": "+919944112233",
            "notes": "Bank loan recovery suit"
        },
        {
            "cnr_number": "TNKR050001392021",
            "case_number_formatted": "OS/139/2021",
            "case_title": "A Palaniyappan vs R Manokaran & 5 Ors",
            "court_name": "Principal District Munsif Court, Karur",
            "court_room": "Room 5",
            "item_number": "23",
            "judge_name": "Thiru. N.Nilaveshwaran, B.A., B.L.",
            "case_stage": "Trial",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "A Palaniyappan",
            "client_phone": "+919842555666",
            "notes": "Final trial arguments"
        },
        {
            "cnr_number": "TNKR090000692024",
            "case_number_formatted": "COS/69/2024",
            "case_title": "Shobika Impex Private LTD vs Sundar A N Sundarapandiyan",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 3",
            "item_number": "1",
            "judge_name": "Tmt K.L.Priyanga, B.A., B.L.(Hons)",
            "case_stage": "Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "Shobika Impex Ltd",
            "client_phone": "+919843011223",
            "notes": "Commercial dispute evidence"
        },
        {
            "cnr_number": "TNKR090001392025",
            "case_number_formatted": "OS/139/2025",
            "case_title": "Bank of Baroda Karur vs P Kalyani & Anr",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 3",
            "item_number": "31",
            "judge_name": "Tmt K.L.Priyanga, B.A., B.L.(Hons)",
            "case_stage": "Ex-parte Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "Bank of Baroda Main",
            "client_phone": "+919444111222",
            "notes": "Proof affidavit filing"
        },
        {
            "cnr_number": "TNKR090003952025",
            "case_number_formatted": "OS/395/2025",
            "case_title": "Bank of Baroda vs B Priyadharshini & 2 Ors",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 3",
            "item_number": "35",
            "judge_name": "Tmt K.L.Priyanga, B.A., B.L.(Hons)",
            "case_stage": "Ex-parte Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "BOB Aravakurichi",
            "client_phone": "+919444333444",
            "notes": "Recovery suit exparte"
        },
        {
            "cnr_number": "TNKR090008312025",
            "case_number_formatted": "OS/831/2025",
            "case_title": "State Bank of India vs P Arumugam",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 3",
            "item_number": "37",
            "judge_name": "Tmt K.L.Priyanga, B.A., B.L.(Hons)",
            "case_stage": "Ex-parte Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "SBI Aravakurichi",
            "client_phone": "+919445112233",
            "notes": "Exparte order hearing"
        },
        {
            "cnr_number": "TNKR090005552023",
            "case_number_formatted": "OS/555/2023",
            "case_title": "SBI Kovai Road vs D Yasotha",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 3",
            "item_number": "46",
            "judge_name": "Tmt K.L.Priyanga, B.A., B.L.(Hons)",
            "case_stage": "Steps",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "SBI Kovai Road",
            "client_phone": "+919445998877",
            "notes": "Legal heir steps petition"
        },
        {
            "cnr_number": "TNKR090000942025",
            "case_number_formatted": "OS/94/2025",
            "case_title": "Bank of Baroda vs V Kumar",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 4",
            "item_number": "42",
            "judge_name": "Thiru. BALAMURUGAN V.S., Addl Subordinate Judge",
            "case_stage": "Ex-parte Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "BOB Karur Main",
            "client_phone": "+919444111222",
            "notes": "Proof affidavit"
        },
        {
            "cnr_number": "TNKR090004662025",
            "case_number_formatted": "OS/466/2025",
            "case_title": "T Shankar vs A A Thangavelu & 10 Ors",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 4",
            "item_number": "43",
            "judge_name": "Thiru. BALAMURUGAN V.S., Addl Subordinate Judge",
            "case_stage": "Ex-parte Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "T Shankar",
            "client_phone": "+919842199887",
            "notes": "Partition suit exparte"
        },
        {
            "cnr_number": "TNKR090000722021",
            "case_number_formatted": "OS/72/2021",
            "case_title": "K Lakshmi vs V Vadivel",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 4",
            "item_number": "106",
            "judge_name": "Thiru. BALAMURUGAN V.S., Addl Subordinate Judge",
            "case_stage": "IA Pending",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "K Lakshmi",
            "client_phone": "+919842333221",
            "notes": "Commissioner report objection"
        }
    ]

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    for item in sample_hearings:
        cursor.execute("""
            INSERT OR REPLACE INTO cases (
                cnr_number, case_number_formatted, case_title, court_name, court_room,
                item_number, judge_name, case_stage, case_status, next_hearing_date,
                client_name, client_phone, notes, parties, advocates,
                track_next_hearing, track_orders, track_case_status, auto_whatsapp_enabled,
                last_hearing_date, last_checked_at
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                1, 1, 1, 1,
                '2026-07-15', CURRENT_TIMESTAMP
            )
        """, (
            item["cnr_number"],
            item["case_number_formatted"],
            item["case_title"],
            item["court_name"],
            item["court_room"],
            item["item_number"],
            item["judge_name"],
            item["case_stage"],
            item["case_status"],
            item["next_hearing_date"],
            item["client_name"],
            item["client_phone"],
            item["notes"],
            f"{item['client_name']} | Opposing Party",
            "Advocate R. Anbaiya"
        ))

    conn.commit()
    conn.close()
