import re, yaml, gspread, collections
from oauth2client.service_account import ServiceAccountCredentials

src=open('main.py',encoding='utf-8').read()
exec(src[src.index("def format_phone_number"):src.index("interview_count = len(new_rows)")], globals())

p=yaml.safe_load(open(open("settings_path.txt").read().strip()))
s=p["sheet_settings"]; C=p["columns"]
scope=['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
cl=gspread.authorize(ServiceAccountCredentials.from_json_keyfile_name('credentials.json',scope))
rows=cl.open_by_url(s["target_sheet_url"]).worksheet(s["target_worksheet_name"]).get_all_values()
hdr=rows[0]; iw=hdr.index(C["whatsapp_number"]); im=hdr.index(C["mobile_number"])
ip=hdr.index(C["preference1"]); target=p["subsystem_settings"]["target_subsystem"]

bad=[]; same=0; total=0; lens=collections.Counter()
for n,r in enumerate(rows[1:],2):
    if r[ip].strip().lower()!=target.strip().lower(): continue
    total+=1
    w=format_phone_number(r[iw], phone_number_backup=r[im]) if r[iw] else None
    m=format_phone_number(r[im]) if r[im] else None
    lens[len(w) if w else 0]+=1
    if w==m: same+=1
    if not w or len(w)!=13 or not w.startswith("+91"):
        bad.append((n, r[iw], r[im], w))

print(f"AI ({target}) rows: {total}")
print(f"\nFormatted length distribution (13 = +91 + 10 digits = correct):")
for L,c in sorted(lens.items()): print(f"  len {L:>3}: {c:>4} rows {'  <-- OK' if L==13 else '  <-- SUSPECT'}")
print(f"\nRows where WhatsApp == Mobile (fallback tries same number): {same} / {total} ({100*same/max(total,1):.0f}%)")
print(f"Rows producing a suspect number: {len(bad)} ({100*len(bad)/max(total,1):.1f}%)")
for n,w,m,f in bad[:15]:
    print(f"  row {n:>4}: whatsapp={w!r:<22} mobile={m!r:<22} -> {f!r}")
