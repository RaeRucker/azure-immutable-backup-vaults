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
SUBSCRIPTION = "sub-contoso"
WORKLOAD_RG = "rg-workloads"
VAULT_RG = f"rg-backup-{REGION_CODE}"
VAULT = f"rsv-contoso-{REGION_CODE}"
WORKSPACE = "law-contoso"
WORKSPACE_RG = "rg-contoso-platform"
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
}
# ---------------------------------------------------------------------------

NAVY = "#0B2545"
BLUE = "#1F5FBF"
INK = "#17202A"
MUTED = "#46525E"
FADE = "#7E8A97"
LINE = "#7F8C99"
FAINT = "#D3DAE1"
TIER_COLORS = {"Critical": "#B42318", "Business-Essential": "#B4561A", "Operational": "#1F5FBF", "Non-Production": "#5F6B78"}
SANS = 'font-family="DejaVu Sans Condensed, DejaVu Sans, sans-serif"'
MONO = 'font-family="DejaVu Sans Mono, monospace"'

parts = []
ICON_DIR = Path(".")


def text(x, y, s, size=18, weight=400, fill=INK, anchor="start", mono=False, spacing=None):
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    parts.append(f'<text x="{x}" y="{y}" {MONO if mono else SANS} font-size="{size}" font-weight="{weight}" '
                 f'fill="{fill}" text-anchor="{anchor}"{ls}>{s}</text>')


def rect(x, y, w, h, stroke=LINE, fill="none", sw=1.4, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def path(points, color=INK, sw=2, dash=None, marker="arrow"):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    pts = " ".join(f"{x},{y}" for x, y in points)
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{sw}"{d} marker-end="url(#{marker})"/>')


def icon(name, x, y, size=34, opacity=None):
    data = base64.b64encode((ICON_DIR / ICONS[name]).read_bytes()).decode()
    op = f' opacity="{opacity}"' if opacity is not None else ""
    parts.append(f'<image x="{x}" y="{y}" width="{size}" height="{size}"{op} href="data:image/svg+xml;base64,{data}"/>')


def boundary(x, y, w, h, label, kind, dash=None, fill="none"):
    rect(x, y, w, h, LINE, fill, 1.4, dash)
    icon(kind, x + 12, y + 10, 22)
    text(x + 42, y + 28, label, 16, 700, MUTED, spacing="0.6")


def chevron(x, w, n, title, caption, y=118, h=78):
    tip = 24
    pts = [(x, y), (x + w - tip, y), (x + w, y + h / 2), (x + w - tip, y + h), (x, y + h)]
    if n > 1:
        pts.append((x + tip, y + h / 2))
    parts.append(f'<polygon points="{" ".join(f"{a},{b}" for a, b in pts)}" fill="#FFFFFF" stroke="{NAVY}" stroke-width="2"/>')
    cx = x + (22 if n == 1 else 40)
    parts.append(f'<circle cx="{cx + 14}" cy="{y + 30}" r="14" fill="{NAVY}"/>')
    text(cx + 14, y + 36, str(n), 16, 700, "#FFFFFF", "middle")
    text(cx + 38, y + 37, title, 21, 700, NAVY)
    text(cx + 2, y + 64, caption, 16, 400, MUTED)


def arrow_label(x, y, s, color):
    w = len(s) * 8.6 + 14
    parts.append(f'<rect x="{x - w / 2}" y="{y - 17}" width="{w}" height="24" fill="#FFFFFF"/>')
    text(x, y, s, 15, 700, color, "middle")


def retention(t):
    r = t["retention"]
    keep = [f"{r['days']} days"]
    for key, unit in (("weeks", "wk"), ("months", "mo"), ("years", "yr")):
        if r.get(key):
            keep.append(f"{r[key]} {unit}")
    return ", ".join(keep)


def build(cfg):
    tiers = cfg["tiers"]
    tag = cfg["tagName"]
    W, H = 1640, 1130

    # Title
    parts.append(f'<rect x="0" y="0" width="{W}" height="6" fill="{NAVY}"/>')
    text(40, 62, "Azure Backup: auto-enroll by tier", 32, 700, NAVY)
    text(40, 96, f"Follow vm-web01. It's tagged {tag} = Critical, so Azure Policy backs it up with the Critical policy in its region's vault.", 18, 400, MUTED)
    text(W - 40, 62, f"{AUTHOR}  ·  {REVISION}", 15, 400, MUTED, "end", mono=True)

    # Columns: VMs, policy, vault, right side
    c1, c2, c3, c4 = 50, 470, 900, 1316
    cw = 360

    # The four steps, each over its column
    chevron(40, 400, 1, "Tag the VM", f"Set {tag} to a tier name")
    chevron(460, 400, 2, "Policy checks it", "On create or when first tagged")
    chevron(890, 400, 3, "Backup turns on", "Region's vault, tier's policy")
    chevron(1320, 280, 4, "Copy and logs", "Paired region, Log Analytics")

    # Boundaries. Azure Policy is assigned at subscription scope, so it crosses the region box.
    boundary(30, 222, W - 60, 830, f"SUBSCRIPTION  ·  {SUBSCRIPTION}", "sub")
    boundary(40, 290, 1250, 720, f"REGION  ·  {REGION.upper()}", "rg", dash="8 5")
    boundary(c1 + 10, 348, cw, 640, WORKLOAD_RG, "rg")
    boundary(c3, 348, 380, 640, VAULT_RG, "rg")

    rect(c2 - 10, 262, 390, 772, NAVY, "#F3F6FA", 2)
    icon("policy", c2 + 4, 276, 30)
    text(c2 + 42, 299, "Azure Policy", 19, 700, NAVY)
    text(c2 + 4, 330, "Subscription scope, one per tier per region", 15, 400, MUTED)

    icon("vault", c3 + 16, 388, 36)
    text(c3 + 60, 404, VAULT, 16, 700, INK, mono=True)
    text(c3 + 60, 426, "Recovery Services vault, Enhanced policies", 15, 400, MUTED)

    row_top, row_h, card_h = 462, 98, 76
    for i, t in enumerate(tiers):
        y = row_top + i * row_h
        cy = y + card_h / 2
        color = TIER_COLORS.get(t["name"], BLUE)
        lead = i == 0
        ink = INK if lead else FADE
        sub = MUTED if lead else FADE
        frame = color if lead else FAINT
        sw = 2.4 if lead else 1.2

        # VM card
        rect(c1 + 24, y, cw - 28, card_h, frame, "#FFFFFF", sw)
        icon("vm", c1 + 36, y + 10, 30, None if lead else 0.45)
        vm = SAMPLE_VMS[i] if i < len(SAMPLE_VMS) else f"vm-{i + 1:02}"
        text(c1 + 76, y + 31, vm, 18, 700, ink, mono=True)
        parts.append(f'<rect x="{c1 + 45}" y="{y + 46}" width="11" height="16" fill="{color}" opacity="{1 if lead else 0.45}"/>')
        text(c1 + 64, y + 59, f"{tag} = {t['name']}", 15, 400, sub, mono=True)

        # Policy assignment card
        rect(c2 + 6, y, 358, card_h, frame, "#FFFFFF", sw)
        text(c2 + 22, y + 31, f"backup-{t['name'].lower()}-{REGION_CODE}", 15, 700, ink, mono=True)
        text(c2 + 22, y + 58, f"Looks for {tag} = {t['name']}", 14, 400, sub)

        # Backup policy card
        rect(c3 + 14, y, 352, card_h, frame, "#FFFFFF", sw)
        text(c3 + 30, y + 31, t["policyName"], 16, 700, ink, mono=True)
        every = f"Every {t['everyHours']} hours" if t["frequency"] == "Hourly" else "Once a day"
        text(c3 + 30, y + 58, f"{every}, keeps {retention(t)}", 14, 400, sub)

        # Connectors
        path([(c1 + cw - 4, cy), (c2 + 4, cy)], INK if lead else FAINT, 2.4 if lead else 1.4,
             marker="arrow" if lead else "arrowFaint")
        path([(c2 + 364, cy), (c3 + 12, cy)], INK if lead else FAINT, 2.4 if lead else 1.4,
             marker="arrow" if lead else "arrowFaint")

    # Arrow labels on the example row
    arrow_label((c1 + cw - 4 + c2 + 4) / 2, row_top + card_h / 2 + 26, "checks", INK)
    arrow_label((c2 + 364 + c3 + 12) / 2, row_top + card_h / 2 + 26, "turns on", INK)

    # Step numbers on the example path, matching the strip at the top
    for n, (bx, by) in enumerate([(c1 + 24, row_top), (c2 + 6, row_top), (c3 + 14, row_top), (c4, 290), (c4, 640)], 1):
        n = min(n, 4)
        parts.append(f'<circle cx="{bx}" cy="{by}" r="13" fill="{NAVY}" stroke="#FFFFFF" stroke-width="2"/>')
        text(bx, by + 5, str(n), 14, 700, "#FFFFFF", "middle")

    # Managed identity and remediation, inside the policy panel
    my = row_top + 4 * row_h + 6
    rect(c2 + 6, my, 358, 84, NAVY, "#FFFFFF", 1.4)
    text(c2 + 22, my + 25, "Each assignment's managed identity", 15, 700, NAVY)
    text(c2 + 22, my + 49, "VM Contributor on the subscription", 15, 400, MUTED)
    text(c2 + 22, my + 72, "Backup Contributor on the vault RG", 15, 400, MUTED)
    rect(c2 + 6, my + 98, 358, 62, LINE, "#FFFFFF", 1.4, "6 4")
    text(c2 + 22, my + 123, "Remediation task, run once by hand", 15, 700, INK)
    text(c2 + 22, my + 146, "Catches VMs tagged before setup", 15, 400, MUTED)

    # Vault settings
    sy = row_top + 4 * row_h + 10
    x = c3 + 14
    for chip in ["Immutable, unlocked", "Soft delete always on"]:
        w = 22 + len(chip) * 7.6
        rect(x, sy, w, 32, NAVY, "#FFFFFF", 1.4)
        text(x + w / 2, sy + 21, chip, 14, 700, NAVY, "middle")
        x += w + 8
    text(c3 + 14, sy + 64, "Early deletes are blocked from day one.", 15, 400, MUTED)
    text(c3 + 14, sy + 86, "Locking it after a restore test makes it permanent.", 15, 400, MUTED)

    # Paired region copy
    boundary(c4, 290, 280, 300, "PAIRED REGION", "rg", dash="8 5")
    text(c4 + 14, 345, PAIRED_REGION, 17, 700, INK)
    icon("vault", c4 + 14, 362, 34)
    text(c4 + 56, 384, "Geo-redundant copy", 16, 700, INK)
    for k, line in enumerate(["Each day's vault backup.", "Can run up to 36 hours", "behind. Restore to this", "region any time with Cross", "Region Restore."]):
        text(c4 + 14, 428 + k * 24, line, 15, 400, MUTED)
    path([(c3 + 380, 380), (c4 + 12, 380)], BLUE, 2.2, "9 6", marker="arrowBlue")

    # Log Analytics
    boundary(c4, 640, 280, 370, WORKSPACE_RG, "rg")
    text(c4 + 14, 740 + 5 * 24 + 26, "Any region, same subscription", 14, 400, MUTED)
    icon("law", c4 + 14, 690, 34)
    text(c4 + 56, 712, WORKSPACE, 15, 700, INK, mono=True)
    for k, line in enumerate(["Diagnostic settings send", "backup jobs, policies,", "storage and protected", "items here. Feeds the", "daily backup report."]):
        text(c4 + 14, 756 + k * 24, line, 15, 400, MUTED)
    path([(c3 + 380, 420), (c3 + 404, 420), (c3 + 404, 706), (c4 + 12, 706)], MUTED, 2.4, "2 5", marker="arrowGrey")

    # Legend
    ly = H - 42
    path([(40, ly), (96, ly)], INK, 2.4)
    text(108, ly + 6, "Enrollment", 15, 400, MUTED)
    path([(250, ly), (306, ly)], BLUE, 2.2, "9 6", marker="arrowBlue")
    text(318, ly + 6, "Geo-redundant copy", 15, 400, MUTED)
    path([(510, ly), (566, ly)], MUTED, 2.4, "2 5", marker="arrowGrey")
    text(578, ly + 6, "Diagnostic logs", 15, 400, MUTED)
    rect(740, ly - 10, 56, 20, LINE, "none", 1.4, "8 5")
    text(808, ly + 6, "Region", 15, 400, MUTED)
    text(W - 40, ly + 6, "Same layout in every region. Each region has its own vault and assignments.", 15, 400, MUTED, "end")

    def marker(mid, fill):
        return (f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{fill}"/></marker>')

    defs = "".join(marker(m, c) for m, c in (("arrow", INK), ("arrowFaint", FAINT), ("arrowRed", TIER_COLORS["Critical"]),
                                             ("arrowBlue", BLUE), ("arrowGrey", MUTED)))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
            f'<defs>{defs}</defs>\n<rect width="{W}" height="{H}" fill="#FFFFFF"/>\n' + "\n".join(parts) + "\n</svg>")


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
