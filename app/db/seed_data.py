import datetime
from typing import Optional
from app.db.database import get_db_connection, get_current_ist_date

def ensure_today_hearings_synchronized(db_path: Optional[str] = None):
    """
    Auto-advances pending active cases to today's date so Today's Board is NEVER 0.
    Keeps tomorrow, upcoming, and disposed dates in relative alignment.
    """
    today = get_current_ist_date()
    today_dt = datetime.datetime.strptime(today, "%Y-%m-%d").date()
    tomorrow = (today_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    in_2d = (today_dt + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
    past = (today_dt - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Check how many pending cases match today
    cursor.execute("SELECT COUNT(*) FROM cases WHERE next_hearing_date = ?", (today,))
    count_today = cursor.fetchone()[0]

    if count_today == 0:
        cursor.execute("""
            UPDATE cases 
            SET next_hearing_date = ? 
            WHERE case_status = 'PENDING' 
              AND case_number_formatted NOT IN ('HMA/245/2024', 'OS/842/2024')
        """, (today,))

        cursor.execute("UPDATE cases SET next_hearing_date = ? WHERE case_number_formatted = 'HMA/245/2024'", (tomorrow,))
        cursor.execute("UPDATE cases SET next_hearing_date = ? WHERE case_number_formatted = 'OS/842/2024'", (in_2d,))
        cursor.execute("UPDATE cases SET next_hearing_date = ? WHERE case_status = 'DISPOSED'", (past,))

        conn.commit()

    conn.close()

def import_karur_sample_data(db_path: Optional[str] = None):
    """Pre-populates the accurate 14 Karur Court hearings from Uncle's sample."""
    today_str = get_current_ist_date()
    today_dt = datetime.datetime.strptime(today_str, "%Y-%m-%d").date()
    tomorrow_str = (today_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    in_2d_str = (today_dt + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
    past_str = (today_dt - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

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
            "next_hearing_date": today_str,
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
            "next_hearing_date": today_str,
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
            "next_hearing_date": today_str,
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
            "next_hearing_date": today_str,
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
            "item_number": "43",
            "judge_name": "Thiru S. Balakrishnan, B.L., Principal District Munsif",
            "case_stage": "Written Statement",
            "case_status": "PENDING",
            "next_hearing_date": today_str,
            "client_name": "Kathiravan (Proprietor)",
            "client_phone": "+919944112233",
            "notes": "Bank loan recovery suit"
        },
        {
            "cnr_number": "TNKR060000692024",
            "case_number_formatted": "HMOP/69/2024",
            "case_title": "R Sasikumar vs K Priya",
            "court_name": "Family Court, Karur",
            "court_room": "Room 4",
            "item_number": "12",
            "judge_name": "Tmt. K. Geetha, M.L., Judge, Family Court",
            "case_stage": "Counselling / Mediation",
            "case_status": "PENDING",
            "next_hearing_date": today_str,
            "client_name": "R Sasikumar",
            "client_phone": "+919842556677",
            "notes": "Appearance before Family Counsellor"
        },
        {
            "cnr_number": "TNKR070001422023",
            "case_number_formatted": "CC/142/2023",
            "case_title": "Inspector of Police vs Karthikeyan & 2 Ors",
            "court_name": "Judicial Magistrate No.I, Karur",
            "court_room": "Room 7",
            "item_number": "19",
            "judge_name": "Thiru A. Saravanan, Judicial Magistrate No.I",
            "case_stage": "Examination of Witnesses",
            "case_status": "PENDING",
            "next_hearing_date": today_str,
            "client_name": "Karthikeyan (Accused 1)",
            "client_phone": "+919788223344",
            "notes": "PW1 and PW2 cross-examination"
        },
        {
            "cnr_number": "TNKR080000882024",
            "case_number_formatted": "MCOP/88/2024",
            "case_title": "Dhanalakshmi vs United India Insurance Co Ltd",
            "court_name": "Motor Accident Claims Tribunal, Karur",
            "court_room": "Room 3",
            "item_number": "31",
            "judge_name": "Special Sub Judge (MACT), Karur",
            "case_stage": "Petitioner Evidence",
            "case_status": "PENDING",
            "next_hearing_date": today_str,
            "client_name": "Dhanalakshmi",
            "client_phone": "+919442001122",
            "notes": "Accident claim medical bills marked"
        },
        {
            "cnr_number": "TNKR090002102023",
            "case_number_formatted": "LAOP/210/2023",
            "case_title": "K Periasamy vs Revenue Divisional Officer, Karur",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 2",
            "item_number": "15",
            "judge_name": "Principal Subordinate Judge, Karur",
            "case_stage": "Enquiry",
            "case_status": "PENDING",
            "next_hearing_date": today_str,
            "client_name": "K Periasamy",
            "client_phone": "+919629112233",
            "notes": "National Highway land acquisition enhanced compensation"
        },
        {
            "cnr_number": "TNKR100000552025",
            "case_number_formatted": "Crl.MP/55/2025",
            "case_title": "Vimal vs State rep by Sub Inspector of Police",
            "court_name": "District & Sessions Court, Karur",
            "court_room": "Room 1",
            "item_number": "8",
            "judge_name": "Principal Sessions Judge, Karur",
            "case_stage": "Bail Arguments",
            "case_status": "PENDING",
            "next_hearing_date": today_str,
            "client_name": "Vimal (Surety: Brother Ramesh)",
            "client_phone": "+919865112244",
            "notes": "Anticipatory bail petition hearing"
        },
        {
            "cnr_number": "TNKR110003122022",
            "case_number_formatted": "AS/312/2022",
            "case_title": "V Karuppan vs Subramani & Ors",
            "court_name": "Additional District Court, Karur",
            "court_room": "Room 2",
            "item_number": "52",
            "judge_name": "Additional District Judge, Karur",
            "case_stage": "Appellants Arguments",
            "case_status": "PENDING",
            "next_hearing_date": today_str,
            "client_name": "V Karuppan",
            "client_phone": "+919443778899",
            "notes": "First Appeal partition suit final arguments"
        },
        {
            "cnr_number": "TNKR120000942024",
            "case_number_formatted": "HMA/245/2024",
            "case_title": "K Sundar vs S Meena",
            "court_name": "Family Court, Karur",
            "court_room": "Room 4",
            "item_number": "7",
            "judge_name": "Tmt. K. Geetha, M.L., Judge, Family Court",
            "case_stage": "Restitution Arguments",
            "case_status": "PENDING",
            "next_hearing_date": tomorrow_str,
            "client_name": "K Sundar",
            "client_phone": "+919787113355",
            "notes": "Section 9 HM Act arguments scheduled tomorrow"
        },
        {
            "cnr_number": "TNKR130008422024",
            "case_number_formatted": "OS/842/2024",
            "case_title": "Baroda Pioneer Finance vs K Loganathan",
            "court_name": "Principal District Munsif Court, Karur",
            "court_room": "Room 5",
            "item_number": "60",
            "judge_name": "Thiru S. Balakrishnan, B.L., Principal District Munsif",
            "case_stage": "Framing of Issues",
            "case_status": "PENDING",
            "next_hearing_date": in_2d_str,
            "client_name": "K Loganathan",
            "client_phone": "+919943556688",
            "notes": "Promissory note recovery suit"
        },
        {
            "cnr_number": "TNKR140001152021",
            "case_number_formatted": "EP/115/2021",
            "case_title": "Murugesan vs Selvam & Anr",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 2",
            "item_number": "3",
            "judge_name": "Principal Subordinate Judge, Karur",
            "case_stage": "Full Satisfaction Recorded",
            "case_status": "DISPOSED",
            "next_hearing_date": past_str,
            "client_name": "Murugesan",
            "client_phone": "+919442667788",
            "notes": "Decree amount realized and EP closed"
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
