"""Draws docs/images/how-it-works.png from config/backup-tiers.json.

Uses Microsoft's Azure architecture icons, which Microsoft allows in architecture
diagrams. Download them from https://learn.microsoft.com/azure/architecture/icons/
and point --icons at the folder that holds the SVGs.

    python tools/build_diagram.py --icons <icon folder> --out /tmp/how-it-works.svg
    rsvg-convert /tmp/how-it-works.svg -o docs/images/how-it-works.png
"""
import argparse
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---- Settings -------------------------------------------------------------
REGION = "East US 2"
REGION_CODE = "eastus2"
PAIRED_REGION = "Central US"
SUBSCRIPTION = "sub-contoso-prod"
WORKLOAD_RG = "rg-workloads"
VAULT_RG = f"rg-backup-{REGION_CODE}"
VAULT = f"rsv-contoso-prod-{REGION_CODE}"
WORKSPACE = "law-contoso-prod"
SAMPLE_VMS = ["vm-web01", "vm-erp01", "vm-files01", "vm-dev01"]
AUTHOR = "Rae Rucker"
REVISION = "Rev 2026-11"
ICONS = {
    "vm": "Virtual-Machine.svg",
    "policy": "Policy.svg",
    "vault": "Recovery-Services-Vaults.svg",
    "law": "Log-Analytics-Workspaces.svg",
    "sub": "Subscriptions.svg",
    "rg": "Resource-Groups.svg",
    "tag": "Tags.svg",
}
# ---------------------------------------------------------------------------

NAVY = "#0B2545"
BLUE = "#1F5FBF"
INK = "#1D2733"
MUTED = "#5B6875"
LINE = "#8A96A3"
FAINT = "#C9D1D9"
TIER_COLORS = {"Critical": "#B42318", "Business-Essential": "#C4661F", "Operational": "#1F5FBF", "Non-Production": "#6B7785"}
SANS = 'font-family="DejaVu Sans Condensed, DejaVu Sans, sans-serif"'
MONO = 'font-family="DejaVu Sans Mono, monospace"'

parts = []


def text(x, y, s, size=15, weight=400, fill=INK, anchor="start", mono=False, spacing=None):
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    parts.append(f'<text x="{x}" y="{y}" {MONO if mono else SANS} font-size="{size}" font-weight="{weight}" '
                 f'fill="{fill}" text-anchor="{anchor}"{ls}>{s}</text>')


def rect(x, y, w, h, stroke=LINE, fill="none", sw=1.2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def line(points, color=INK, sw=1.6, dash=None, arrow=True):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    m = ' marker-end="url(#arrow)"' if arrow else ""
    pts = " ".join(f"{x},{y}" for x, y in points)
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{sw}"{d}{m}/>')


def icon(name, x, y, size=34):
    data = base64.b64encode((ICON_DIR / ICONS[name]).read_bytes()).decode()
    parts.append(f'<image x="{x}" y="{y}" width="{size}" height="{size}" href="data:image/svg+xml;base64,{data}"/>')


def step(n, x, y):
    parts.append(f'<rect x="{x - 11}" y="{y - 11}" width="22" height="22" fill="{NAVY}"/>')
    text(x, y + 5, str(n), 13, 700, "#FFFFFF", "middle")


def boundary(x, y, w, h, label, kind, dash=None):
    rect(x, y, w, h, LINE, "none", 1.2, dash)
    icon(kind, x + 10, y + 9, 20)
    text(x + 36, y + 24, label, 13, 700, MUTED, spacing="0.4")


def schedule(t):
    every = f"every {t['everyHours']} h" if t["frequency"] == "Hourly" else "daily"
    r = t["retention"]
    keep = [f"{r['days']}d"] + [f"{r[k]}{u}" for k, u in (("weeks", "w"), ("months", "m"), ("years", "y")) if r[k]]
    return every, " / ".join(keep)


def build(cfg):
    tiers = cfg["tiers"]
    tag = cfg["tagName"]
    W, H = 1840, 1150

    # Title block
    parts.append(f'<rect x="0" y="0" width="{W}" height="6" fill="{NAVY}"/>')
    text(48, 66, "Azure Backup auto-enroll by tier", 30, 700, NAVY)
    text(48, 96, f"A VM's {tag} tag decides which backup policy protects it. Azure Policy does the enrollment. Same layout in every region.", 16, 400, MUTED)
    rect(1480, 34, 312, 70, FAINT, "#FFFFFF", 1)
    parts.append(f'<line x1="1480" y1="69" x2="1792" y2="69" stroke="{FAINT}" stroke-width="1"/>')
    parts.append(f'<line x1="1636" y1="69" x2="1636" y2="104" stroke="{FAINT}" stroke-width="1"/>')
    text(1494, 58, AUTHOR.upper(), 14, 700, NAVY, spacing="1.5")
    text(1494, 93, "Architecture", 13, 400, MUTED)
    text(1650, 93, REVISION, 13, 400, MUTED, mono=True)

    # Subscription and region boundaries
    boundary(40, 130, 1760, 790, f"SUBSCRIPTION  ·  {SUBSCRIPTION}", "sub")
    boundary(70, 200, 1360, 690, f"REGION  ·  {REGION.upper()}", "rg", dash="6 4")
    boundary(96, 280, 380, 580, WORKLOAD_RG, "rg")
    boundary(960, 280, 450, 580, VAULT_RG, "rg")

    # Policy assignments sit at subscription scope, drawn across the region they target
    rect(540, 280, 356, 580, NAVY, "#F5F7FA", 1.4)
    icon("policy", 556, 294, 26)
    text(590, 313, "Azure Policy assignments", 14, 700, NAVY)
    text(556, 340, "Subscription scope, one per tier", 12.5, 400, MUTED)

    # Vault header
    icon("vault", 976, 318, 30)
    text(1014, 333, VAULT, 14, 700, INK, mono=True)
    text(1014, 352, "Recovery Services vault", 12.5, 400, MUTED)

    row_top = 392
    row_h = 104
    for i, t in enumerate(tiers):
        y = row_top + i * row_h
        cy = y + 38
        color = TIER_COLORS.get(t["name"], BLUE)

        # VM
        rect(112, y, 348, 78, FAINT, "#FFFFFF", 1)
        icon("vm", 124, y + 10, 30)
        text(166, y + 31, SAMPLE_VMS[i] if i < len(SAMPLE_VMS) else f"vm-{i + 1:02}", 15, 700, INK, mono=True)
        icon("tag", 166, y + 44, 16)
        parts.append(f'<rect x="188" y="{y + 45}" width="10" height="14" fill="{color}"/>')
        text(204, y + 57, f"{tag} = {t['name']}", 13, 400, MUTED, mono=True)

        # Assignment
        rect(556, y, 324, 78, color, "#FFFFFF", 1.4)
        parts.append(f'<rect x="556" y="{y}" width="5" height="78" fill="{color}"/>')
        text(572, y + 31, f"backup-{t['name'].lower()}-{REGION_CODE}", 13, 700, INK, mono=True)
        text(572, y + 56, f"{REGION_CODE} + {tag}={t['name']}", 12, 400, MUTED, mono=True)

        # Vault policy
        every, keep = schedule(t)
        rect(976, y, 418, 78, FAINT, "#FFFFFF", 1)
        parts.append(f'<rect x="976" y="{y}" width="5" height="78" fill="{color}"/>')
        text(994, y + 31, t["policyName"], 14, 700, INK, mono=True)
        text(994, y + 56, f"{every}   keep {keep}", 13, 400, MUTED, mono=True)

        # Connectors
        line([(460, cy), (554, cy)], LINE, 1.4)
        line([(880, cy), (974, cy)], color, 1.8)

    # Step markers on the first row
    step(1, 507, row_top + 38)
    step(2, 927, row_top + 38)

    # Vault properties
    py = row_top + 4 * row_h + 4
    props = ["Immutable", "Soft delete always on", "Geo-redundant + CRR"]
    x = 976
    for p in props:
        w = 20 + len(p) * 6.9
        rect(x, py, w, 28, NAVY, NAVY, 1)
        text(x + w / 2, py + 19, p, 12.5, 700, "#FFFFFF", "middle")
        x += w + 8

    # Paired region and Log Analytics, inside the subscription, outside the region
    boundary(1460, 200, 310, 270, f"PAIRED REGION  ·  {PAIRED_REGION.upper()}", "rg", dash="6 4")
    icon("vault", 1480, 256, 36)
    text(1526, 271, "Secondary copy", 15, 700, INK)
    text(1526, 292, "of every backup", 13, 400, MUTED)
    text(1480, 336, "Restore here with Cross", 13, 400, MUTED)
    text(1480, 356, "Region Restore if the", 13, 400, MUTED)
    text(1480, 376, "main region is down.", 13, 400, MUTED)
    line([(1410, 500), (1438, 500), (1438, 320), (1470, 320)], BLUE, 1.6, "7 5")
    step(3, 1438, 410)

    rect(1460, 560, 310, 230, LINE, "none", 1.2)
    icon("law", 1480, 580, 36)
    text(1526, 595, WORKSPACE, 13.5, 700, INK, mono=True)
    text(1526, 615, "Log Analytics workspace", 12.5, 400, MUTED)
    text(1480, 660, "Backup jobs, policies, storage", 13, 400, MUTED)
    text(1480, 680, "and protected items. Feeds the", 13, 400, MUTED)
    text(1480, 700, "daily backup report and alerts.", 13, 400, MUTED)
    line([(1410, 680), (1472, 680)], BLUE, 1.6, "7 5")
    step(4, 1438, 680)

    # Notes, like a drawing's notes block
    ny = 962
    text(48, ny, "NOTES", 13, 700, NAVY, spacing="1.5")
    parts.append(f'<line x1="48" y1="{ny + 10}" x2="1792" y2="{ny + 10}" stroke="{FAINT}" stroke-width="1"/>')
    notes = [
        ("1", "Tag match", f"Each assignment matches VMs in its region whose {tag} tag equals its tier. Untagged VMs are never enrolled."),
        ("2", "Enrollment", "DeployIfNotExists turns on backup in the vault with that tier's policy. New or newly tagged VMs enroll on their own."),
        ("3", "Paired region", "Geo-redundant storage copies each backup to the paired region. Cross Region Restore restores from it."),
        ("4", "Logs", "Diagnostic settings send backup logs to resource-specific tables in Log Analytics."),
    ]
    for i, (n, title, body) in enumerate(notes):
        y = ny + 44 + i * 30
        step(n, 60, y - 5)
        text(84, y, title, 14, 700, INK)
        text(204, y, body, 14, 400, MUTED)
    gy = ny + 44 + 4 * 30 + 12
    text(84, gy, "Also:", 14, 700, INK)
    text(204, gy, "VMs tagged before auto-enroll existed need one remediation task. Changing a tag doesn't move a VM that's already backed up. Custom-image VMs aren't matched.", 14, 400, MUTED)

    # Legend
    lx, ly = 1480, ny + 44
    line([(lx, ly - 5), (lx + 46, ly - 5)], INK, 1.8)
    text(lx + 58, ly, "Enrollment", 13, 400, MUTED)
    line([(lx, ly + 25), (lx + 46, ly + 25)], BLUE, 1.6, "7 5")
    text(lx + 58, ly + 30, "Data copy or logs", 13, 400, MUTED)
    rect(lx, ly + 47, 46, 18, LINE, "none", 1.2, "6 4")
    text(lx + 58, ly + 61, "Region boundary", 13, 400, MUTED)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>
<rect width="{W}" height="{H}" fill="#FFFFFF"/>
{chr(10).join(parts)}
</svg>'''


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--icons", required=True, help="Folder with Microsoft's Azure icon SVGs")
    ap.add_argument("--config", default=str(ROOT / "config" / "backup-tiers.json"))
    ap.add_argument("--out", required=True, help="SVG file to write")
    args = ap.parse_args()
    ICON_DIR = Path(args.icons)
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    Path(args.out).write_text(build(cfg), encoding="utf-8")
    print(f"wrote {args.out}")
