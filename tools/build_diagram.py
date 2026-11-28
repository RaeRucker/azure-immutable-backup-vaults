"""Draws docs/images/how-it-works.png from config/backup-tiers.json.

Run after changing the tier config:
    python tools/build_diagram.py config/backup-tiers.json /tmp/how-it-works.svg
    rsvg-convert /tmp/how-it-works.svg -o docs/images/how-it-works.png
"""
import json, sys
cfg = json.load(open(sys.argv[1]))
out = sys.argv[2]
tiers = cfg["tiers"]
COL = {"Critical": "#B03A2E", "Business-Essential": "#B9770E", "Operational": "#1F618D", "Non-Production": "#5D6D7E"}
W, H = 1800, 1130
F = "font-family=\"Inter, DejaVu Sans, sans-serif\""
el = []
def t(x, y, s, size=18, weight=400, fill="#1B2631", anchor="start"):
    el.append(f'<text x="{x}" y="{y}" {F} font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{s}</text>')
def box(x, y, w, h, stroke="#AAB7B8", fill="#FFFFFF", r=10, dash=None, sw=2):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
def arrow(x1, y1, x2, y2, color="#566573", dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    mx = (x1 + x2) / 2
    el.append(f'<path d="M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}" fill="none" stroke="{color}" stroke-width="2.5"{d} marker-end="url(#a)"/>')

def sched(tr):
    s = f"Every {tr['everyHours']} hours" if tr["frequency"] == "Hourly" else "Daily"
    r = tr["retention"]; parts = [f"{r['days']} days"]
    if r["weeks"]: parts.append(f"{r['weeks']} weekly")
    if r["months"]: parts.append(f"{r['months']} monthly")
    if r["years"]: parts.append(f"{r['years']} yearly")
    return s, "Keeps " + ", ".join(parts)

t(60, 70, "How auto-enroll and backup tiers work", 34, 700)
t(60, 106, f"Tag a VM with {cfg['tagName']} and Azure Policy backs it up in its region's vault with that tier's policy. This repeats in every region.", 19, 400, "#566573")

# column headers
for x, n, s in [(60, "1", "Tag the VM"), (560, "2", "Azure Policy, one assignment per tier"), (1100, "3", "Vault in the same region")]:
    el.append(f'<circle cx="{x+16}" cy="164" r="16" fill="#1B2631"/>'); t(x + 16, 170, n, 17, 700, "#FFFFFF", "middle")
    t(x + 44, 171, s, 22, 700)

# column 1: VMs
vms = ["vm-web01", "vm-erp01", "vm-files01", "vm-dev01"]
rowy = [215, 345, 475, 605]
for i, tr in enumerate(tiers):
    y = rowy[i]; c = COL[tr["name"]]
    box(60, y, 380, 100, c, "#FFFFFF")
    el.append(f'<rect x="60" y="{y}" width="10" height="100" rx="4" fill="{c}"/>')
    t(90, y + 40, vms[i], 20, 600)
    t(90, y + 72, f"{cfg['tagName']} = {tr['name']}", 18, 500, c)
box(60, 735, 380, 100, "#AAB7B8", "#FBFCFC", dash="8 6")
t(90, 775, "vm-test01", 20, 600, "#7B7D7D"); t(90, 807, "No tag: never enrolled", 18, 400, "#7B7D7D")

# column 2: assignments
for i, tr in enumerate(tiers):
    y = rowy[i]; c = COL[tr["name"]]
    box(560, y, 440, 100, c, "#FFFFFF")
    t(585, y + 40, f"backup-{tr['name'].lower()}-eastus2", 20, 600)
    t(585, y + 72, f"Tag = {tr['name']}  and  region = eastus2", 17, 400, "#566573")
    arrow(440, y + 50, 560, y + 50, c)
box(560, 735, 440, 100, "#D5D8DC", "#F4F6F6")
t(585, 772, "New or newly tagged VMs enroll on their own.", 17, 500)
t(585, 802, "VMs tagged before auto-enroll was set up", 17, 400, "#566573")
t(585, 826, "need a remediation task once.", 17, 400, "#566573")

# column 3: vault
box(1100, 195, 640, 660, "#1B2631", "#F8F9F9", r=14, sw=2.5)
t(1130, 240, "rsv-contoso-prod-eastus2", 22, 700)
t(1130, 268, "Recovery Services vault", 17, 400, "#566573")
for i, tr in enumerate(tiers):
    y = rowy[i] + 75 if False else 290 + i * 112; c = COL[tr["name"]]
    box(1130, y, 580, 96, c, "#FFFFFF")
    el.append(f'<rect x="1130" y="{y}" width="10" height="96" rx="4" fill="{c}"/>')
    s1, s2 = sched(tr)
    t(1158, y + 32, tr["policyName"], 19, 600)
    t(1158, y + 59, s1, 17, 500, c)
    t(1158, y + 83, s2, 16, 400, "#566573")
    arrow(1000, rowy[i] + 50, 1130, y + 48, c)
# vault settings chips
chips = ["Immutable", "Soft delete always on", "Geo-redundant"]
cx = 1130
for ch in chips:
    w = 22 + len(ch) * 9.6
    box(cx, 752, w, 40, "#1B2631", "#1B2631", r=20)
    t(cx + w / 2, 778, ch, 16, 600, "#FFFFFF", "middle"); cx += w + 14
t(1130, 830, "Immutability is locked only after a restore test passes.", 16, 400, "#566573")

# bottom row: what happens next
el.append('<circle cx="76" cy="908" r="16" fill="#1B2631"/>'); t(76, 914, "4", 17, 700, "#FFFFFF", "middle")
t(104, 915, "After that", 22, 700)
by = 950
box(60, by, 520, 140, "#AAB7B8"); t(85, by + 40, "Paired region copy", 20, 700)
t(85, by + 72, "Every backup is copied to the paired region.", 17, 400, "#566573")
t(85, by + 98, "Cross Region Restore lets you restore there", 17, 400, "#566573")
t(85, by + 122, "if the main region is down.", 17, 400, "#566573")
box(640, by, 520, 140, "#AAB7B8"); t(665, by + 40, "Logs to Log Analytics", 20, 700)
t(665, by + 72, "Jobs, policies, storage and protected items", 17, 400, "#566573")
t(665, by + 98, "feed the daily backup report and alerts.", 17, 400, "#566573")
box(1220, by, 520, 140, "#AAB7B8"); t(1245, by + 40, "Changing a VM's tier", 20, 700)
t(1245, by + 72, "Changing the tag doesn't move a VM that's", 17, 400, "#566573")
t(1245, by + 98, "already backed up. Switch its policy in the", 17, 400, "#566573")
t(1245, by + 122, "vault under Backup items.", 17, 400, "#566573")

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#566573"/></marker></defs>
<rect width="{W}" height="{H}" fill="#FFFFFF"/>
{chr(10).join(el)}
</svg>'''
open(out, "w").write(svg)
