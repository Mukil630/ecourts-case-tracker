import json
from pathlib import Path

def run():
    base_dir = Path(__file__).resolve().parent.parent
    with open(base_dir / 'authentic_cases.json', 'r', encoding='utf-8') as f:
        cases = json.load(f)

    code_lines = [
        'from typing import Optional',
        'from app.db.database import get_db_connection',
        '',
        'def ensure_today_hearings_synchronized(db_path: Optional[str] = None):',
        '    """No-op: Preserves authentic court diary dates without artificial shifts."""',
        '    pass',
        '',
        'def import_karur_sample_data(db_path: Optional[str] = None):',
        '    """Populates the 44 authentic Advocate R. Anbaiya chamber cases with their exact court dates."""',
        '    conn = get_db_connection(db_path)',
        '    cursor = conn.cursor()',
        '',
        '    cases_data = ['
    ]

    for c in cases:
        c_clean = {
            'cnr_number': c.get('cnr_number', ''),
            'case_number_formatted': c.get('case_number_formatted', '') or c.get('cnr_number', ''),
            'case_title': c.get('case_title', ''),
            'court_name': c.get('court_name', ''),
            'court_room': c.get('court_room', ''),
            'item_number': c.get('item_number', ''),
            'judge_name': c.get('judge_name', ''),
            'case_stage': c.get('case_stage', 'Hearing'),
            'case_status': c.get('case_status', 'PENDING'),
            'next_hearing_date': c.get('next_hearing_date', ''),
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
        '            item["next_hearing_date"],',
        '            item["client_name"],',
        '            item["client_phone"],',
        '            item["notes"],',
        '            item["parties"] or f"{item[\'client_name\']} | Opposing Party",',
        '            item["advocates"] or "Advocate R. Anbaiya",',
        '            "2026-07-15"',
        '        ))',
        '',
        '    conn.commit()',
        '    conn.close()',
        '    print(f"Successfully imported {len(cases_data)} authentic chamber cases.")'
    ])

    target_file = base_dir / 'app' / 'db' / 'seed_data.py'
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(code_lines))
    print(f"Generated authentic seed data in {target_file}")

if __name__ == '__main__':
    run()
