"""
Extract KI_Imago_Tender_Register.xlsx into a JS data file embedded in
ki_tender_data.js — consumed by the CEO agent panel.
"""
import zipfile, xml.etree.ElementTree as ET, pathlib, json, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = pathlib.Path(r"c:\Users\dell\Desktop\KI\agents_website")
xl   = BASE / "KI_Imago_Tender_Register.xlsx"
NS   = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'

def tag(t): return f'{{{NS}}}{t}'

with zipfile.ZipFile(xl) as z:
    # Shared strings
    ss_root = ET.fromstring(z.read('xl/sharedStrings.xml'))
    strings = []
    for si in ss_root.findall(f'.//{tag("si")}'):
        text = ''.join(t.text or '' for t in si.iter(tag('t')))
        strings.append(text)

    # Rels
    rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rid_map = {r.get('Id'): r.get('Target') for r in rels}

    wb = ET.fromstring(z.read('xl/workbook.xml'))
    sheets = wb.findall(f'.//{tag("sheet")}')
    rid_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

    def get_cell_val(c):
        t = c.get('t', '')
        v_el = c.find(tag('v'))
        if v_el is None: return ''
        val = v_el.text or ''
        if t == 's':
            try: return strings[int(val)]
            except: return val
        return val

    def read_sheet(name):
        for s in sheets:
            if s.get('name') == name:
                rid = s.get(f'{{{rid_ns}}}id')
                target = rid_map.get(rid, '')
                fp = ('xl/' + target) if not target.startswith('xl/') else target
                ws = ET.fromstring(z.read(fp))
                rows = ws.findall(f'.//{tag("row")}')
                return [[get_cell_val(c) for c in r.findall(tag('c'))] for r in rows]
        return []

    # ── Tender Register (row 0-1 = title, row 2 = col headers, row 3+ = data)
    tr_rows = read_sheet('Tender Register')
    tr_headers = [h.strip() for h in tr_rows[2]] if len(tr_rows) > 2 else []
    tr_data = []
    for row in tr_rows[3:]:
        if not any(row): continue
        # Pad row to header length
        while len(row) < len(tr_headers): row.append('')
        obj = {tr_headers[i]: row[i] for i in range(len(tr_headers)) if tr_headers[i]}
        if obj.get('#') and obj.get('Institution'):
            tr_data.append(obj)

    # ── Dashboard summary row (row index 5 = values)
    dash = read_sheet('Dashboard')
    dash_labels = dash[4] if len(dash) > 4 else []
    dash_vals   = dash[5] if len(dash) > 5 else []
    dashboard = {}
    for i, lbl in enumerate(dash_labels):
        if lbl and i < len(dash_vals):
            dashboard[lbl.strip()] = dash_vals[i]

    # ── Bid Tracker
    bt_rows = read_sheet('Bid Tracker')
    bt_headers = [h.strip() for h in bt_rows[2]] if len(bt_rows) > 2 else []
    bt_data = []
    for row in bt_rows[3:]:
        if not any(row): continue
        while len(row) < len(bt_headers): row.append('')
        obj = {bt_headers[i]: row[i] for i in range(len(bt_headers)) if bt_headers[i]}
        if obj.get('Tender ID') and obj.get('Institution'):
            bt_data.append(obj)

    # ── Competitor Intel
    ci_rows = read_sheet('Competitor Intel')
    ci_headers = [h.strip() for h in ci_rows[2]] if len(ci_rows) > 2 else []
    ci_data = []
    for row in ci_rows[3:]:
        if not any(row): continue
        while len(row) < len(ci_headers): row.append('')
        obj = {ci_headers[i]: row[i] for i in range(len(ci_headers)) if ci_headers[i]}
        if obj.get('Tender ID') and obj.get('Institution'):
            ci_data.append(obj)

# Write as JS
out = BASE / "ki_tender_data.js"
out.write_text(
    f"const KI_TENDER_DATA = {json.dumps({'tenders': tr_data, 'dashboard': dashboard, 'bids': bt_data, 'competitors': ci_data}, ensure_ascii=False, indent=2)};\n",
    encoding='utf-8'
)
print(f"Written ki_tender_data.js")
print(f"  Tenders: {len(tr_data)}")
print(f"  Bid tracker rows: {len(bt_data)}")
print(f"  Competitor rows: {len(ci_data)}")
print(f"  Dashboard: {dashboard}")
