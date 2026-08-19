import json
from pathlib import Path

def run():
    base_dir = Path(__file__).resolve().parent.parent
    with open(base_dir / 'data_dump.json', 'r', encoding='utf-8') as f:
        cases = json.load(f)

    code_lines = [
        'import datetime',
        'from typing import Optional',
        'from app.db.database import get_db_connection, get_current_ist_date',
        '',
        'def get_relative_date(days_offset: int) -> str:',
        '    """Calculates YYYY-MM-DD date offset from today in IST."""',
        '    try:',
        '        today_str = get_current_ist_date()',
        '        base_dt = datetime.datetime.strptime(today_str, "%Y-%m-%d").date()',
        '        return (base_dt + datetime.timedelta(days=days_offset)).strftime("%Y-%m-%d")',
        '    except Exception:',
        '        return datetime.date.today().strftime("%Y-%m-%d")',
        '',
        'def ensure_today_hearings_synchronized(db_path: Optional[str] = None):',
        '    """Keeps today\'s court board synchronized if database was previously initialized."""',
        '    pass',
        '',
        'def import_karur_sample_data(db_path: Optional[str] = None):',
        '    """Pre-populates the complete 44 Advocate R. Anbaiya chamber cases with live synchronized dates."""',
        '    conn = get_db_connection(db_path)',
        '    cursor = conn.cursor()',
        '',
        '    cases_data = ['
    ]

    disposed_indices = {23, 25, 26, 29, 31, 32, 39, 40}

    for idx, c in enumerate(cases):
        if idx in disposed_indices or c.get('case_status') == 'DISPOSED':
            offset = -(15 + (idx * 5))
            status = 'DISPOSED'
        elif idx < 6:
            offset = 0  # Today!
            status = 'PENDING'
        elif idx < 11:
            offset = 1  # Tomorrow!
            status = 'PENDING'
        elif idx < 14:
            offset = 2
            status = 'PENDING'
        elif idx < 23:
            offset = 3 + ((idx - 14) % 5)
            status = 'PENDING'
        else:
            offset = 8 + ((idx - 23) % 15)
            status = 'PENDING'

        c_clean = {
            'cnr_number': c.get('cnr_number', ''),
            'case_number_formatted': c.get('case_number_formatted', ''),
            'case_title': c.get('case_title', ''),
            'court_name': c.get('court_name', ''),
            'court_room': c.get('court_room', ''),
            'item_number': c.get('item_number', ''),
            'judge_name': c.get('judge_name', ''),
            'case_stage': c.get('case_stage', 'Hearing'),
            'case_status': status,
            'days_offset': offset,
            'client_name': c.get('client_name', 'Chamber Client'),
            'client_phone': c.get('client_phone', '+919842112233'),
            'notes': c.get('notes', ''),
            'parties': c.get('parties', ''),
            'advocates': c.get('advocates', 'Advocate R. Anbaiya')
        }
        code_lines.append(f'        {json.dumps(c_clean, indent=8).strip()},')

    code_lines.extend([
        '    ]',
        '',
        '    for item in cases_data:',
        '        hearing_date = get_relative_date(item["days_offset"])',
        '        cursor.execute("""',
        '            INSERT OR REPLACE INTO cases (',
        '                cnr_number, case_number_formatted, case_title, court_name, court_room,',
        '                item_number, judge_name, case_stage, case_status, next_hearing_date,',
        '                client_name, client_phone, notes, parties, advocates,',
        '                track_next_hearing, track_orders, track_case_status, auto_whatsapp_enabled,',
        '                last_hearing_date, last_checked_at',
        '            ) VALUES (',
        '                ?, ?, ?, ?, ?,',
        '                ?, ?, ?, ?, ?,',
        '                ?, ?, ?, ?, ?,',
        '                1, 1, 1, 1,',
        '                ?, CURRENT_TIMESTAMP',
        '            )',
        '        """, (',
        '            item["cnr_number"],',
        '            item["case_number_formatted"],',
        '            item["case_title"],',
        '            item["court_name"],',
        '            item["court_room"],',
        '            item["item_number"],',
        '            item["judge_name"],',
        '            item["case_stage"],',
        '            item["case_status"],',
        '            hearing_date,',
        '            item["client_name"],',
        '            item["client_phone"],',
        '            item["notes"],',
        '            item["parties"] or f"{item[\'client_name\']} | Opposing Party",',
        '            item["advocates"] or "Advocate R. Anbaiya",',
        '            get_relative_date(-30)',
        '        ))',
        '',
        '    # Sample Prospective Client Leads if empty',
        '    cursor.execute("SELECT COUNT(*) FROM leads")',
        '    if cursor.fetchone()[0] == 0:',
        '        sample_leads = [',
        '            ("K. Soundararajan", "+919842177889", "Property Partition Suit", "Principal Sub Court, Karur", "NEW", "Consultation scheduled for ancestral land division dispute"),',
        '            ("V. Meenatchi", "+919443388776", "Cheque Dishonour NI Act 138", "Fast Track Court, Karur", "CONTACTED", "Notice statutory 15 days period expired"),',
        '            ("S. Loganathan", "+919789055443", "Motor Accident Claim MCOP", "Principal District Court, Karur", "SCHEDULED", "Medical disability records submitted for compensation claim")',
        '        ]',
        '        cursor.executemany("""',
        '            INSERT INTO leads (client_name, client_phone, matter_type, expected_court, status, notes)',
        '            VALUES (?, ?, ?, ?, ?, ?)',
        '        """, sample_leads)',
        '',
        '    # Sample History Logs for Adjournment Audit',
        '    cursor.execute("SELECT COUNT(*) FROM case_history_logs")',
        '    if cursor.fetchone()[0] == 0:',
        '        sample_logs = [',
        '            ("TNKR010010352023", "HEARING_DATE_CHANGE", get_relative_date(-14), get_relative_date(0), "Court adjourned for cross examination of PW1", 1),',
        '            ("TNKR040003612025", "HEARING_DATE_CHANGE", get_relative_date(-21), get_relative_date(0), "Injunction application hearing posted for orders", 1),',
        '            ("TNKR090001392025", "HEARING_DATE_CHANGE", get_relative_date(-7), get_relative_date(1), "Bank proof affidavit verification", 1)',
        '        ]',
        '        cursor.executemany("""',
        '            INSERT INTO case_history_logs (cnr_number, change_type, previous_hearing_date, new_hearing_date, details, notified)',
        '            VALUES (?, ?, ?, ?, ?, ?)',
        '        """, sample_logs)',
        '',
        '    conn.commit()',
        '    conn.close()',
        '    print(f"Successfully seeded {len(cases_data)} cases, leads, and history logs.")'
    ])

    target_file = base_dir / 'app' / 'db' / 'seed_data.py'
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(code_lines))
    print(f"Generated seed data in {target_file}")

if __name__ == '__main__':
    run()
