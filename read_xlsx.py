import zipfile, xml.etree.ElementTree as ET, sys
sys.stdout.reconfigure(encoding='utf-8')

xl = r'c:/Users/dell/Desktop/KI/agents_website/KI_Imago_Tender_Register.xlsx'
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'

def tag(t): return f'{{{NS}}}{t}'

with zipfile.ZipFile(xl) as z:
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    sheets = wb.findall(f'.//{tag("sheet")}')

    ss_root = ET.fromstring(z.read('xl/sharedStrings.xml'))
    strings = []
    for si in ss_root.findall(f'.//{tag("si")}'):
        text = ''.join(t.text or '' for t in si.iter(tag('t')))
        strings.append(text)

    def get_cell_val(c):
        t = c.get('t', '')
        v_el = c.find(tag('v'))
        if v_el is None: return ''
        val = v_el.text or ''
        if t == 's':
            try: return strings[int(val)]
            except: return val
        return val

    # Get rels to map rId -> sheet file
    rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rid_map = {}
    for r in rels:
        rid_map[r.get('Id')] = r.get('Target')

    for s in sheets:
        name = s.get('name')
        rid = s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        target = rid_map.get(rid, '')
        filepath = 'xl/' + target if not target.startswith('xl/') else target
        try:
            ws = ET.fromstring(z.read(filepath))
        except: continue
        rows = ws.findall(f'.//{tag("row")}')
        print(f"\n=== {name} ({len(rows)} rows) ===")
        for row in rows[:6]:
            cells = [get_cell_val(c) for c in row.findall(tag('c'))]
            print('  ' + ' | '.join(cells))
