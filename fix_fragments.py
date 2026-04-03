"""
Fix all injected fragment files so they work correctly when loaded into a parent page via innerHTML:
1. WA scripts  — wa_showTab uses implicit `event` global + unscoped querySelectorAll('.pane/.tab')
2. Scout brief — show() uses implicit `event` global + unscoped querySelectorAll('.pane/.tab')
Both need:
  a) Pass the clicked button as an argument instead of using event.target
  b) Scope querySelectorAll to the panel root element, not the whole document
"""
import re, pathlib
BASE = pathlib.Path(r"c:\Users\dell\Desktop\KI\agents_website")

# ── Helpers ────────────────────────────────────────────────────────────────────
def fix_showtab_fn(text, fn_name, pane_prefix='pane-'):
    """
    Replace:
      function wa_showTab(id){
        document.querySelectorAll('.pane').forEach(...)
        document.querySelectorAll('.tab').forEach(...)
        document.getElementById('pane-'+id).classList.add('active');
        event.target.classList.add('active');
      }
    With a version that accepts (id, btn) and scopes queries to the closest
    ancestor with class 'wa-panel-root' / 'scout-panel-root'.
    """
    # Replace function signature to accept btn parameter
    text = re.sub(
        rf'function {fn_name}\(id\)',
        rf'function {fn_name}(id, btn)',
        text
    )
    # Replace event.target with btn
    text = text.replace('event.target.classList.add(\'active\');',
                        'if(btn){var root=btn.closest(\'[data-panel-root]\');'
                        '(root||document).querySelectorAll(\'.pane\').forEach(function(p){p.classList.remove(\'active\');});'
                        '(root||document).querySelectorAll(\'.tab\').forEach(function(t){t.classList.remove(\'active\');});'
                        'var target=document.getElementById(\''+pane_prefix+'\'+id);if(target)target.classList.add(\'active\');'
                        'btn.classList.add(\'active\');}')
    # Remove the now-duplicate querySelectorAll lines that came before event.target
    text = re.sub(
        r"document\.querySelectorAll\('\.pane'\)\.forEach\([^)]+=>p\.classList\.remove\('active'\)\);",
        '', text
    )
    text = re.sub(
        r"document\.querySelectorAll\('\.tab'\)\.forEach\([^)]+=>t\.classList\.remove\('active'\)\);",
        '', text
    )
    text = re.sub(
        r"document\.getElementById\('pane-'\+id\)\.classList\.add\('active'\);",
        '', text
    )
    return text

# ── Fix WA fragment ────────────────────────────────────────────────────────────
wa_path = BASE / "KI_whatsapp_outreach_scripts.html"
wa = wa_path.read_text(encoding='utf-8')

# Fix onclick attributes to pass `this`
wa = wa.replace("onclick=\"wa_showTab('sequence')\"", "onclick=\"wa_showTab('sequence',this)\"")
wa = wa.replace("onclick=\"wa_showTab('preview')\"",  "onclick=\"wa_showTab('preview',this)\"")
wa = wa.replace("onclick=\"wa_showTab('objections')\"","onclick=\"wa_showTab('objections',this)\"")
wa = wa.replace("onclick=\"wa_showTab('rules')\"",     "onclick=\"wa_showTab('rules',this)\"")

# Add data-panel-root to the outermost div
wa = wa.replace('<div style="padding:1rem 0;">', '<div style="padding:1rem 0;" data-panel-root="wa">')

# Replace the entire wa_showTab function body with a scoped version
old_fn = """function wa_showTab(id, btn){
  document.querySelectorAll('.pane').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('pane-'+id).classList.add('active');
  event.target.classList.add('active');
}"""

# Find and replace the actual function in the file
wa_fn_pattern = re.compile(
    r'function wa_showTab\(id(?:,\s*btn)?\)\s*\{[^}]+\}',
    re.DOTALL
)
new_fn = """function wa_showTab(id, btn){
  var root = btn ? btn.closest('[data-panel-root]') : document;
  if(!root) root = document;
  root.querySelectorAll('.pane').forEach(function(p){ p.classList.remove('active'); });
  root.querySelectorAll('.tab').forEach(function(t){ t.classList.remove('active'); });
  var target = root.querySelector('#pane-'+id);
  if(target) target.classList.add('active');
  if(btn) btn.classList.add('active');
}"""
wa = wa_fn_pattern.sub(new_fn, wa)
wa_path.write_text(wa, encoding='utf-8')
print("WA: wa_showTab fixed")

# Verify
if 'event.target' in wa:
    print("  WARNING: event.target still present in WA")
else:
    print("  OK: no event.target in WA")
if "document.querySelectorAll('.pane')" in wa and "data-panel-root" not in wa:
    print("  WARNING: unscoped querySelectorAll still in WA")
else:
    print("  OK: querySelectorAll scoped in WA")

# ── Fix Scout fragment ─────────────────────────────────────────────────────────
scout_path = BASE / "scout_agent_tender_monitoring_brief.html"
scout = scout_path.read_text(encoding='utf-8')

# Find the show() function — it was already renamed? Check
print("\nScout show() occurrences:")
for m in re.finditer(r'function show\b|function scout_show\b', scout):
    print(f"  found: {m.group()} at pos {m.start()}")

# Add data-panel-root to outermost div
# Find first <div> after </style>
scout = re.sub(
    r'(<div style="padding:1rem 0;")',
    r'<div style="padding:1rem 0;" data-panel-root="scout">\n<!-- inner replaced -->',
    scout, count=1
)
# That doubled a div — let's do it cleaner
scout = scout.replace(
    '<div style="padding:1rem 0;" data-panel-root="scout">\n<!-- inner replaced -->\n(<div style="padding:1rem 0;")',
    '<div style="padding:1rem 0;" data-panel-root="scout">'
)

# Simpler: just find the first outer wrapper div
scout_orig = scout_path.read_text(encoding='utf-8')
# Find the tab onclick attributes
tab_onclicks = re.findall(r'onclick="(?:scout_)?show\(\'([^\']+)\'\)"', scout_orig)
print(f"  Scout tab IDs: {tab_onclicks}")

# Fix onclick to pass this
scout_orig = re.sub(
    r'onclick="(?:scout_)?show\(\'([^\']+)\'\)"',
    lambda m: f"onclick=\"scout_show('{m.group(1)}',this)\"",
    scout_orig
)

# Add data-panel-root
scout_orig = scout_orig.replace(
    '<div style="padding:1rem 0;">',
    '<div style="padding:1rem 0;" data-panel-root="scout">',
    1  # only first occurrence
)

# Replace/add scout_show function
scout_fn_pattern = re.compile(
    r'function (?:scout_)?show\(id(?:,\s*btn)?\)\s*\{[^}]+\}',
    re.DOTALL
)
new_scout_fn = """function scout_show(id, btn){
  var root = btn ? btn.closest('[data-panel-root]') : document;
  if(!root) root = document;
  root.querySelectorAll('.pane').forEach(function(p){ p.classList.remove('active'); });
  root.querySelectorAll('.tab').forEach(function(t){ t.classList.remove('active'); });
  var target = root.querySelector('#pane-'+id);
  if(target) target.classList.add('active');
  if(btn) btn.classList.add('active');
}"""

if scout_fn_pattern.search(scout_orig):
    scout_orig = scout_fn_pattern.sub(new_scout_fn, scout_orig)
    print("  Scout: replaced existing show() with scout_show()")
else:
    # Inject before </script>
    scout_orig = scout_orig.replace('</script>', new_scout_fn + '\n</script>', 1)
    print("  Scout: injected scout_show() before </script>")

scout_path.write_text(scout_orig, encoding='utf-8')

if 'event.target' in scout_orig:
    print("  WARNING: event.target still in Scout")
else:
    print("  OK: no event.target in Scout")
print("Scout fragment fixed")
