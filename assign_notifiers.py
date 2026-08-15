"""Round-robin assign MemberNotifier so several people can each send a slice."""
import yaml, gspread
from oauth2client.service_account import ServiceAccountCredentials

SENDERS = ["athrv", "member2", "member3", "member4", "member5"]  # <-- EDIT

p = yaml.safe_load(open(open("settings_path.txt").read().strip()))
s = p["sheet_settings"]; C = p["columns"]
target = p["subsystem_settings"]["target_subsystem"]
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
cl = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope))
ws = cl.open_by_url(s["target_sheet_url"]).worksheet(s["target_worksheet_name"])
rows = ws.get_all_values(); hdr = rows[0]

if C["notifier"] not in hdr:
    ws.update_cell(1, len(hdr) + 1, C["notifier"])
    hdr.append(C["notifier"])
    print(f"Created column {C['notifier']!r}")
ni = hdr.index(C["notifier"])
pi = hdr.index(C["preference1"])
notified = "Notified_" + target
di = hdr.index(notified) if notified in hdr else None

updates = []; counts = {n: 0 for n in SENDERS}; k = 0
for rn, r in enumerate(rows[1:], 2):
    if r[pi].strip().lower() != target.strip().lower():
        continue
    if di is not None and len(r) > di and r[di].strip():
        continue                       # already messaged - skip
    if len(r) > ni and r[ni].strip():
        counts[r[ni]] = counts.get(r[ni], 0) + 1
        continue                       # already assigned
    who = SENDERS[k % len(SENDERS)]; k += 1
    counts[who] += 1
    updates.append({'range': gspread.utils.rowcol_to_a1(rn, ni + 1),
                    'values': [[who]]})

if updates:
    for i in range(0, len(updates), 500):
        ws.batch_update(updates[i:i+500])
print(f"\nAssigned {len(updates)} unmessaged people across {len(SENDERS)} senders:")
for n, c in counts.items():
    print(f"  {n:<12} {c:>4}")
print("\nEach sender: set notifier to their name and check_notifier_column: true")
