import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

updates = [
    ('2026-08-20', 'Counter', 'Room 3', '25', 'Tmt K.L.Priyanga.,B.A..,B.L.,(Hons)', 'TNKR030006182025'),
    ('2026-08-20', 'Hearing', 'Room 4', '59', 'Thiru. BALAMURUGAN V.S.', 'TNKR030016152025'),
    ('2026-08-24', 'Hearing', 'Room 1', '13', 'Tmt. S.SUMATHY, M.L.', 'TNKR010016322026'),
    ('2026-08-25', 'Steps', 'Room 5', '21', 'Thiru. N.Nilaveshwaran, B.A., B.L.', 'TNKR040004462024'),
    ('2026-08-27', 'Evidence', 'Room 4', '51', 'Thiru. BALAMURUGAN V.S.', 'TNKR030007162025'),
    ('2026-09-02', 'Filing Counter', 'Room 1', '18', 'Tmt. S.SUMATHY, M.L.', 'TNKR010042722025'),
    ('2026-09-08', 'Written Statement', 'Room 1', '24', 'Tmt. S.SUMATHY, M.L.', 'TNKR010041112025'),
    ('2026-09-15', 'Arguments', 'Room 3', '32', 'Tmt K.L.Priyanga.,B.A..,B.L.', 'TNKR030000122026'),
    ('2026-09-22', 'Summons Return', 'Room 10', '15', 'Thiru R.Mahesh, B.A., LL.B.', 'TNKR060012832025'),
    ('2026-09-29', 'Trial', 'Room 5', '19', 'Thiru. N.Nilaveshwaran', 'TNKR040001512024')
]

for d, stage, room, item, judge, cnr in updates:
    conn.execute('''
        UPDATE cases 
        SET next_hearing_date = ?, case_stage = ?, court_room = ?, item_number = ?, judge_name = ?, case_status = 'PENDING'
        WHERE cnr_number = ?
    ''', (d, stage, room, item, judge, cnr))

conn.commit()

# Set clean history logs
conn.execute('DELETE FROM case_history_logs')
logs = [
    ('TNKR030007162025', '2026-08-14', '2026-08-27', 'Hearing adjourned from 14-Aug to 27-Aug for Evidence'),
    ('TNKR040004462024', '2026-08-14', '2026-08-25', 'Hearing adjourned from 14-Aug to 25-Aug for Steps'),
    ('TNKR030016152025', '2026-08-14', '2026-08-20', 'Hearing posted to 20-Aug for Final Hearing')
]
for cnr, prev_d, new_d, det in logs:
    conn.execute('''
        INSERT INTO case_history_logs (cnr_number, change_type, previous_hearing_date, new_hearing_date, details, detected_at)
        VALUES (?, 'HEARING_DATE_CHANGE', ?, ?, ?, datetime('now', 'localtime'))
    ''', (cnr, prev_d, new_d, det))

conn.commit()

cursor.execute('SELECT case_title, next_hearing_date, item_number, court_name FROM cases WHERE next_hearing_date >= ? ORDER BY next_hearing_date', ('2026-08-20',))
rows = cursor.fetchall()
print(f'Total upcoming scheduled cases: {len(rows)}')
for r in rows:
    print(f"{r['next_hearing_date']} | Item #{r['item_number']} | {r['case_title']} | {r['court_name']}")

conn.close()
