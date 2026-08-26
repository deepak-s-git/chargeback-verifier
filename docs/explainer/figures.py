"""
Diagram + chart generator for the DisputeShield explainer PDF.

Every figure is rendered with matplotlib (Agg, fully offline) into ./assets as a
high-resolution PNG that build_pdf.py embeds. The visual language matches the
DisputeShield product: indigo brand, near-black ink, status greens/ambers/reds.

Nothing here invents facts about the system — labels and numbers are taken from
the codebase and the locked evaluation results.
"""
import os
os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "mpl"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle
from matplotlib.lines import Line2D
import numpy as np

# ------------------------------------------------------------------ palette ---
INK       = "#101116"
INK_SOFT  = "#3c3f48"
MUTED     = "#6e727c"
BRAND     = "#4338ca"
TEAL      = "#0e7490"
GREEN     = "#15803d"
AMBER     = "#b4530a"
RED       = "#b91c1c"
BLUE      = "#1d4ed8"
HAIR      = "#d8dae1"
CANVAS    = "#f5f5f6"
BRAND_SOFT= "#eef2ff"
GREEN_SOFT= "#e7f6ec"
RED_SOFT  = "#fdecec"
AMBER_SOFT= "#fdf3e7"
BLUE_SOFT = "#e8effd"
TEAL_SOFT = "#e5f3f6"
GREY_SOFT = "#eceef2"

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["savefig.facecolor"] = "white"

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
os.makedirs(ASSETS, exist_ok=True)


# ----------------------------------------------------------------- helpers ---
def _canvas(w_in, h_in, W, H):
    """Figure whose data-unit aspect matches the inch aspect (round corners stay round)."""
    fig, ax = plt.subplots(figsize=(w_in, h_in))
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    ax.set_aspect("equal")
    return fig, ax


def box(ax, x, y, w, h, fc, ec="none", lw=1.4, r=0.14, z=2):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={r}",
        fc=fc, ec=ec, lw=lw, zorder=z, mutation_aspect=1))


def label(ax, x, y, s, color=INK, fs=11, fw="normal", ha="center", va="center", z=5, style="normal"):
    ax.text(x, y, s, color=color, fontsize=fs, fontweight=fw, ha=ha, va=va,
            zorder=z, fontstyle=style)


def titled_box(ax, x, y, w, h, fc, title, sub=None, ec="none", tc=INK, sc=None,
               fs=11.5, subfs=8.6, r=0.14, z=2, lw=1.4):
    box(ax, x, y, w, h, fc, ec=ec, lw=lw, r=r, z=z)
    if sub:
        label(ax, x + w / 2, y + h * 0.62, title, color=tc, fs=fs, fw="bold", z=z + 2)
        label(ax, x + w / 2, y + h * 0.30, sub, color=sc or MUTED, fs=subfs, z=z + 2)
    else:
        label(ax, x + w / 2, y + h / 2, title, color=tc, fs=fs, fw="bold", z=z + 2)


def arrow(ax, x1, y1, x2, y2, color=INK_SOFT, lw=1.8, ms=15, rad=0.0, ls="-", z=3):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=ms, color=color,
        lw=lw, ls=ls, shrinkA=1, shrinkB=1,
        connectionstyle=f"arc3,rad={rad}", zorder=z))


def pill(ax, x, y, w, h, text, fc, tc="white", fs=8.2, z=6):
    box(ax, x, y, w, h, fc, r=h / 2, z=z)
    label(ax, x + w / 2, y + h / 2, text, color=tc, fs=fs, fw="bold", z=z + 1)


def save(fig, name):
    path = os.path.join(ASSETS, name)
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.07)
    plt.close(fig)
    return path


# ================================================================= FIGURES ===
def fig_ecosystem():
    """The five parties in a card dispute and what flows between them."""
    fig, ax = _canvas(9.4, 5.0, 9.4, 5.0)
    label(ax, 4.7, 4.75, "Who's who in a card dispute", fs=14, fw="bold", color=INK)

    parties = {
        "cardholder": (0.9, 2.7, 2.2, 1.0, "Cardholder", "buys, then\ndisputes", BRAND, "white"),
        "merchant":   (0.9, 0.7, 2.2, 1.0, "Merchant (you)", "sold the\nproduct", INK, "white"),
        "issuer":     (6.3, 2.7, 2.2, 1.0, "Issuing bank", "cardholder's\nbank", TEAL, "white"),
        "acquirer":   (6.3, 0.7, 2.2, 1.0, "Acquiring bank", "merchant's\nbank / Razorpay", TEAL, "white"),
        "network":    (3.6, 1.7, 2.2, 1.0, "Card network", "Visa /\nMastercard", "#334155", "white"),
    }
    for (x, y, w, h, t, s, fc, tc) in parties.values():
        titled_box(ax, x, y, w, h, fc, t, s, tc=tc, sc="#dfe3ee", fs=11, subfs=8.0)

    # flows
    arrow(ax, 2.0, 2.7, 2.0, 1.72, color=GREEN, lw=2.0)                 # goods/pay merchant<->cardholder
    label(ax, 1.35, 2.2, "pays ₹ /\ngets goods", fs=7.6, color=GREEN, ha="center")
    arrow(ax, 3.1, 3.2, 6.3, 3.2, color=RED, lw=2.0, rad=-0.18)          # cardholder->issuer dispute
    label(ax, 4.7, 3.75, "“I didn't authorize this”", fs=8.4, color=RED, fw="bold")
    arrow(ax, 6.3, 2.95, 5.8, 2.35, color=INK_SOFT, rad=0.15)           # issuer->network
    arrow(ax, 3.6, 1.95, 3.1, 1.35, color=INK_SOFT, rad=0.15)           # network->merchant side
    arrow(ax, 6.3, 1.0, 3.1, 1.0, color=INK_SOFT, lw=1.8, rad=0.0)      # acquirer<->merchant
    label(ax, 4.7, 0.72, "chargeback debited from merchant", fs=7.8, color=MUTED)
    arrow(ax, 5.8, 1.95, 6.3, 1.35, color=INK_SOFT, rad=0.15)          # network<->acquirer
    label(ax, 8.0, 1.85, "settle", fs=7.4, color=MUTED)

    label(ax, 4.7, 0.15,
          "The money moves cardholder → merchant at purchase, then is clawed back through the banks when disputed.",
          fs=8.2, color=MUTED)
    return save(fig, "ecosystem.png")


def fig_lifecycle():
    """Timeline of a chargeback and where DisputeShield helps."""
    fig, ax = _canvas(9.6, 3.4, 9.6, 3.4)
    label(ax, 4.8, 3.15, "The chargeback lifecycle — and the window that matters", fs=13, fw="bold")

    y = 1.75
    ax.add_line(Line2D([0.5, 9.1], [y, y], color=HAIR, lw=3, zorder=1))
    steps = [
        (0.9, "Purchase", "cardholder buys", BRAND),
        (2.75, "Dispute filed", "weeks later", AMBER),
        (4.6, "Chargeback", "issuer debits merchant", RED),
        (6.45, "Representment", "merchant answers with evidence", GREEN),
        (8.5, "Decision", "network / issuer rules", "#334155"),
    ]
    for (x, t, s, c) in steps:
        ax.add_patch(Circle((x, y), 0.12, fc=c, ec="white", lw=2, zorder=4))
        label(ax, x, y + 0.55, t, fs=10, fw="bold", color=c)
        label(ax, x, y + 0.25, s, fs=7.8, color=MUTED)

    # highlight representment window
    box(ax, 5.55, 0.55, 1.8, 0.72, GREEN_SOFT, ec=GREEN, lw=1.4, r=0.12)
    label(ax, 6.45, 1.02, "DisputeShield", fs=9.2, fw="bold", color=GREEN)
    label(ax, 6.45, 0.75, "compiles the draft here", fs=8.0, color=GREEN)
    arrow(ax, 6.45, 1.27, 6.45, 1.6, color=GREEN, lw=1.6)
    label(ax, 4.8, 0.16, "Merchants usually have only a short, fixed window (often ~7–30 days) to respond — and only one shot.",
          fs=8.2, color=MUTED)
    return save(fig, "lifecycle.png")


def fig_naive_vs_shield():
    """Two mindsets, side by side."""
    fig, ax = _canvas(9.4, 4.8, 9.4, 4.8)
    label(ax, 4.7, 4.55, "Two ways to point AI at a dispute", fs=14, fw="bold")

    box(ax, 0.4, 0.5, 4.2, 3.7, RED_SOFT, ec="#f1c6c6", lw=1.3, r=0.10)
    box(ax, 4.8, 0.5, 4.2, 3.7, GREEN_SOFT, ec="#bfe3cb", lw=1.3, r=0.10)
    label(ax, 2.5, 3.85, "Optimistic generator", fs=12.5, fw="bold", color=RED)
    label(ax, 2.5, 3.55, "(most AI tools)", fs=8.6, color=MUTED, style="italic")
    label(ax, 6.9, 3.85, "Adversarial auditor", fs=12.5, fw="bold", color=GREEN)
    label(ax, 6.9, 3.55, "(DisputeShield)", fs=8.6, color=MUTED, style="italic")

    bad = ["Summarizes everything it's given",
           "Fills gaps by guessing — invents facts",
           "Glosses over contradictions",
           "Can't say where a fact came from",
           "Wants to answer, always"]
    good = ["Extracts only stated facts, then stops",
            "No evidence → abstains, never guesses",
            "Hunts for contradictions on purpose",
            "Every claim traced to source bytes",
            "Declining a bad case is a success"]
    for i, (b, g) in enumerate(zip(bad, good)):
        yy = 3.15 - i * 0.55
        label(ax, 0.7, yy, "✗", fs=12, fw="bold", color=RED, ha="left")
        label(ax, 1.05, yy, b, fs=8.7, color=INK_SOFT, ha="left")
        label(ax, 5.1, yy, "✓", fs=12, fw="bold", color=GREEN, ha="left")
        label(ax, 5.45, yy, g, fs=8.7, color=INK_SOFT, ha="left")
    return save(fig, "naive_vs_shield.png")


def fig_pipeline():
    """The three-phase pipeline, with the AI boxed into phase 1."""
    fig, ax = _canvas(9.6, 4.6, 9.6, 4.6)
    label(ax, 4.8, 4.35, "The three-phase pipeline", fs=14, fw="bold")

    # phase panels
    box(ax, 0.3, 0.5, 3.0, 3.4, BRAND_SOFT, ec="#c7cff5", lw=1.4, r=0.10)
    box(ax, 3.5, 0.5, 3.0, 3.4, TEAL_SOFT, ec="#bfe0e6", lw=1.4, r=0.10)
    box(ax, 6.7, 0.5, 2.6, 3.4, GREEN_SOFT, ec="#bfe3cb", lw=1.4, r=0.10)

    label(ax, 1.8, 3.6, "1 · Ingest & Extract", fs=10.5, fw="bold", color=BRAND)
    label(ax, 5.0, 3.6, "2 · Analyze  (pure)", fs=10.5, fw="bold", color=TEAL)
    label(ax, 8.0, 3.6, "3 · Package", fs=10.5, fw="bold", color=GREEN)

    pill(ax, 1.05, 3.05, 1.5, 0.34, "AI lives here", BRAND, fs=7.6)
    pill(ax, 4.05, 3.05, 1.9, 0.34, "no AI · no I/O", TEAL, fs=7.6)
    pill(ax, 7.15, 3.05, 1.7, 0.34, "verified only", GREEN, fs=7.6)

    p1 = ["Parse CSV / JSON", "PDF / TXT files", "AI + regex extract", "→ structured facts"]
    for i, t in enumerate(p1):
        label(ax, 1.8, 2.65 - i * 0.42, t, fs=8.4, color=INK_SOFT)
    p2 = ["Requirements", "CE 3.0 · timeline", "contradictions", "injection · scoring", "grounded claims", "review gate"]
    for i, t in enumerate(p2):
        label(ax, 5.0, 2.72 - i * 0.36, t, fs=8.2, color=INK_SOFT)
    p3 = ["Draft package", "citations [EV-…]", "action = \"draft\"", "→ human reviews"]
    for i, t in enumerate(p3):
        label(ax, 8.0, 2.65 - i * 0.42, t, fs=8.4, color=INK_SOFT)

    arrow(ax, 3.3, 2.2, 3.5, 2.2, color=INK_SOFT, ms=16)
    arrow(ax, 6.5, 2.2, 6.7, 2.2, color=INK_SOFT, ms=16)
    label(ax, 4.8, 0.18, "The language model only proposes facts in phase 1. Every decision that follows is deterministic Python.",
          fs=8.2, color=MUTED)
    return save(fig, "pipeline.png")


def fig_grounding():
    """The trust boundary that turns a proposed fact into a usable one."""
    fig, ax = _canvas(9.4, 3.9, 9.4, 3.9)
    label(ax, 4.7, 3.65, "Grounding — the trust boundary", fs=14, fw="bold")

    titled_box(ax, 0.4, 1.55, 2.5, 1.0, "#e2e3e8",
               "Proposed fact", "“IP = 192.168.1.100”", tc=INK, sc=MUTED, fs=10.5, subfs=8.2)
    label(ax, 1.65, 1.35, "from AI or regex — untrusted", fs=7.6, color=MUTED)

    # gate
    box(ax, 3.5, 1.15, 2.5, 1.8, "white", ec=BRAND, lw=1.8, r=0.10)
    label(ax, 4.75, 2.62, "Two checks", fs=9.6, fw="bold", color=BRAND)
    label(ax, 4.75, 2.25, "① hash of source bytes", fs=8.4, color=INK_SOFT)
    label(ax, 4.75, 1.95, "    matches?", fs=8.4, color=INK_SOFT)
    label(ax, 4.75, 1.6, "② value present in", fs=8.4, color=INK_SOFT)
    label(ax, 4.75, 1.3, "    raw content?", fs=8.4, color=INK_SOFT)

    arrow(ax, 2.9, 2.05, 3.5, 2.05, color=INK_SOFT)
    # outcomes
    titled_box(ax, 6.6, 2.15, 2.5, 0.85, GREEN, "VERIFIED", "can support a claim", tc="white", sc="#d7f0df", fs=11, subfs=8.0)
    titled_box(ax, 6.6, 1.05, 2.5, 0.85, RED, "BLOCKED", "never asserted", tc="white", sc="#f6d5d5", fs=11, subfs=8.0)
    arrow(ax, 6.0, 2.35, 6.6, 2.58, color=GREEN, rad=0.12)
    label(ax, 6.32, 2.82, "both pass", fs=7.0, color=GREEN, fw="bold")
    arrow(ax, 6.0, 1.7, 6.6, 1.45, color=RED, rad=-0.12)
    label(ax, 6.32, 1.14, "either fails", fs=7.0, color=RED, fw="bold")

    label(ax, 4.7, 0.5, "A model that hallucinates a fact absent from the bytes produces a BLOCKED claim — not an asserted one.",
          fs=8.4, color=INK_SOFT, fw="bold")
    label(ax, 4.7, 0.18, "Honest limit: presence is a case-insensitive substring test, not semantic proof.",
          fs=7.8, color=MUTED, style="italic")
    return save(fig, "grounding.png")


def fig_scoring():
    """The 0–100 strength-weighted score and its decision bands."""
    fig, ax = _canvas(9.6, 3.3, 9.6, 3.3)
    label(ax, 4.8, 3.05, "How the score maps to a recommendation", fs=13.5, fw="bold")

    x0, x1, y, h = 0.7, 8.9, 1.35, 0.7
    span = x1 - x0
    bands = [(0, 25, "#9aa0ab", "ABSTAIN", "< 25"),
             (25, 50, AMBER, "INSUFFICIENT", "25–49"),
             (50, 75, BLUE, "REVIEW", "50–74"),
             (75, 100, GREEN, "CONTEST", "≥ 75")]
    for (a, b, c, name, rng) in bands:
        xa = x0 + span * a / 100
        xb = x0 + span * b / 100
        box(ax, xa, y, xb - xa - 0.04, h, c, r=0.05)
        label(ax, (xa + xb) / 2, y + h / 2, name, color="white", fs=9.0, fw="bold")
        label(ax, (xa + xb) / 2, y - 0.22, rng, color=MUTED, fs=8.0)

    # auto-win marker at 90
    xw = x0 + span * 90 / 100
    ax.add_line(Line2D([xw, xw], [y - 0.05, y + h + 0.35], color=INK, lw=1.6, ls="--", zorder=6))
    label(ax, xw, y + h + 0.55, "auto-win floor 90", fs=8.0, fw="bold", color=INK)
    label(ax, xw + 0.05, y + h + 0.30, "(3-D Secure / CE 3.0)", fs=7.2, color=MUTED, ha="left")

    # scale ends
    label(ax, x0, y - 0.5, "0", fs=8, color=MUTED)
    label(ax, x1, y - 0.5, "100", fs=8, color=MUTED)
    label(ax, 4.8, 0.55,
          "Evidence is scored by strength (Required = 3, Strong = 2, Supporting = 1) over a network-specific total.",
          fs=8.4, color=INK_SOFT)
    label(ax, 4.8, 0.22,
          "Safety overrides sit on top: a contradiction or prompt injection forces human review regardless of the number.",
          fs=8.2, color=MUTED)
    return save(fig, "scoring.png")


def fig_gate():
    """How recommendation + safety flags resolve to a gate status."""
    fig, ax = _canvas(9.4, 4.3, 9.4, 4.3)
    label(ax, 4.7, 4.05, "The human-review gate — what reaches a person, and how", fs=13, fw="bold")

    titled_box(ax, 0.4, 1.9, 2.3, 0.95, BRAND_SOFT, "Analysis result",
               "score + flags", ec="#c7cff5", tc=BRAND, sc=MUTED, fs=10, subfs=8)

    # diamond-ish decision nodes as boxes
    box(ax, 3.1, 3.0, 2.6, 0.8, AMBER_SOFT, ec=AMBER, lw=1.4, r=0.10)
    label(ax, 4.4, 3.4, "Injection or contradiction?", fs=8.8, fw="bold", color=AMBER)
    box(ax, 3.1, 1.9, 2.6, 0.8, BLUE_SOFT, ec=BLUE, lw=1.4, r=0.10)
    label(ax, 4.4, 2.3, "Recommendation = CONTEST?", fs=8.6, fw="bold", color=BLUE)
    box(ax, 3.1, 0.8, 2.6, 0.8, GREY_SOFT, ec=MUTED, lw=1.2, r=0.10)
    label(ax, 4.4, 1.2, "Otherwise (weak / abstain)", fs=8.6, fw="bold", color=INK_SOFT)

    arrow(ax, 2.7, 2.5, 3.1, 3.4, color=INK_SOFT, rad=0.2)
    arrow(ax, 2.7, 2.35, 3.1, 2.3, color=INK_SOFT)
    arrow(ax, 2.7, 2.2, 3.1, 1.2, color=INK_SOFT, rad=-0.2)

    titled_box(ax, 6.2, 3.0, 2.9, 0.8, RED, "MANDATORY_REVIEW", "a human must look", tc="white", sc="#f6d5d5", fs=9.6, subfs=7.8)
    titled_box(ax, 6.2, 1.9, 2.9, 0.8, GREEN, "READY", "draft ready for a human to submit", tc="white", sc="#d7f0df", fs=10, subfs=7.6)
    titled_box(ax, 6.2, 0.8, 2.9, 0.8, "#64748b", "NOT_RECOMMENDED", "don't fight this one", tc="white", sc="#dbe2ea", fs=9.6, subfs=7.8)
    arrow(ax, 5.7, 3.4, 6.2, 3.4, color=RED)
    arrow(ax, 5.7, 2.3, 6.2, 2.3, color=GREEN)
    arrow(ax, 5.7, 1.2, 6.2, 1.2, color="#64748b")

    label(ax, 4.7, 0.28, "“READY” never means auto-submit — it means a compiled draft is ready for a human to review and send.",
          fs=8.2, color=MUTED, style="italic")
    return save(fig, "gate.png")


def _scenario(name, title, tint, edge, ev_items, checks, outcome_lines, outcome_color, verdict, gate):
    fig, ax = _canvas(9.6, 4.0, 9.6, 4.0)
    label(ax, 4.8, 3.78, title, fs=13, fw="bold", color=edge)

    # left: evidence
    box(ax, 0.35, 0.5, 2.7, 3.0, CANVAS, ec=HAIR, lw=1.2, r=0.08)
    label(ax, 1.7, 3.2, "Evidence in", fs=9.6, fw="bold", color=INK)
    for i, e in enumerate(ev_items):
        yy = 2.75 - i * 0.5
        box(ax, 0.55, yy - 0.18, 2.3, 0.38, "white", ec=HAIR, lw=1.0, r=0.08)
        label(ax, 1.7, yy, e, fs=7.9, color=INK_SOFT)

    # middle: engine checks
    box(ax, 3.35, 0.5, 3.0, 3.0, tint, ec=edge, lw=1.4, r=0.08)
    label(ax, 4.85, 3.2, "Deterministic checks", fs=9.6, fw="bold", color=edge)
    for i, ch in enumerate(checks):
        yy = 2.75 - i * 0.46
        mark, mc = ch[1], ch[2]
        label(ax, 3.55, yy, mark, fs=10.5, fw="bold", color=mc, ha="left")
        label(ax, 3.9, yy, ch[0], fs=7.9, color=INK_SOFT, ha="left")

    # right: outcome
    box(ax, 6.65, 0.5, 2.6, 3.0, "white", ec=outcome_color, lw=1.8, r=0.08)
    label(ax, 7.95, 3.2, "Outcome", fs=9.6, fw="bold", color=INK)
    pill(ax, 6.95, 2.55, 2.0, 0.42, verdict, outcome_color, fs=8.8)
    pill(ax, 6.95, 2.02, 2.0, 0.42, gate, "#334155", fs=7.8)
    for i, ln in enumerate(outcome_lines):
        label(ax, 7.95, 1.6 - i * 0.34, ln, fs=7.8, color=INK_SOFT)

    arrow(ax, 3.05, 2.0, 3.35, 2.0, color=INK_SOFT, ms=15)
    arrow(ax, 6.35, 2.0, 6.65, 2.0, color=INK_SOFT, ms=15)
    return save(fig, name)


def fig_scenario_a():
    return _scenario(
        "scenario_a.png", "Scenario 1 — the strong win  (Visa 10.4)", BRAND_SOFT, BRAND,
        ["payment.json", "access_log.csv", "3ds_auth.json"],
        [("Payment proof", "✓", GREEN), ("Access log — IP matches", "✓", GREEN),
         ("3-D Secure present", "✓", GREEN), ("No contradictions", "✓", GREEN),
         ("No injection", "✓", GREEN), ("3DS ⇒ auto-win", "★", BRAND)],
        ["Score in the 90s", "claims grounded", "draft compiled"], GREEN, "CONTEST", "READY")


def fig_scenario_b():
    return _scenario(
        "scenario_b.png", "Scenario 2 — the honest decline  (Mastercard 4837)", AMBER_SOFT, AMBER,
        ["invoice.txt (only)"],
        [("Payment proof", "✗", RED), ("Access / usage proof", "✗", RED),
         ("Authentication", "✗", RED), ("Nothing satisfied", "—", MUTED),
         ("No evidence to ground", "—", MUTED)],
        ["Refuses to invent", "support it lacks", "routes to a human"], AMBER, "ABSTAIN", "NOT_RECOMMENDED")


def fig_scenario_c():
    return _scenario(
        "scenario_c.png", "Scenario 3 — the contradiction catch  (Visa 10.4)", RED_SOFT, RED,
        ["access_log.csv → IP .50", "payment.json → IP .1", "chat.txt → “didn't buy”"],
        [("Access IP ≠ payment IP", "‼", RED), ("Cardholder denial vs log", "‼", RED),
         ("Contradiction detected", "‼", RED), ("Score is overridden", "→", INK_SOFT)],
        ["Even if score is high,", "a person must decide", "nothing auto-proceeds"], RED, "REVIEW", "MANDATORY_REVIEW")


def fig_scenario_d():
    return _scenario(
        "scenario_d.png", "Scenario 4 — the attack that fails  (Mastercard 4837)", "#f3e8ff", "#7c3aed",
        ["feedback.txt contains:", "“ignore previous", "instructions…”"],
        [("Injection pattern hit", "⚠", "#7c3aed"), ("Evidence NOT rewritten", "✓", GREEN),
         ("Zero score penalty", "0", INK_SOFT), ("Cannot flip verdict", "✓", GREEN),
         ("Forced to a human", "→", "#7c3aed")],
        ["Untrusted text can't", "steer the decision —", "it only diverts to review"], "#7c3aed", "REVIEW", "MANDATORY_REVIEW")


def fig_eval_beforeafter():
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    bars = ax.bar(["Prior engine\n(old dataset)", "Rebuilt engine\n(full)"], [22.5, 100.0],
                  color=[MUTED, GREEN], width=0.6, zorder=3)
    ax.axhline(42.5, color=AMBER, lw=1.4, ls="--", zorder=2)
    ax.text(1.48, 44, "majority baseline 42.5%", ha="right", fontsize=8, color=AMBER)
    ax.set_ylim(0, 108)
    ax.set_ylabel("Held-out test accuracy (%)", fontsize=9)
    ax.set_title("Before → after, same held-out split", fontsize=11, fontweight="bold")
    for b, v in zip(bars, [22.5, 100.0]):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:g}%", ha="center", fontsize=10, fontweight="bold")
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8.5)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=HAIR, lw=0.8)
    return save(fig, "eval_beforeafter.png")


def fig_eval_ablation():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.6, 3.4))
    # accuracy
    names = ["Full\nengine", "Ablation\n(safety off)", "Majority\nbaseline"]
    vals = [100.0, 82.5, 42.5]
    cols = [GREEN, AMBER, MUTED]
    b1 = ax1.bar(names, vals, color=cols, width=0.62, zorder=3)
    for b, v in zip(b1, vals):
        ax1.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:g}%", ha="center", fontsize=9.5, fontweight="bold")
    ax1.set_ylim(0, 110)
    ax1.set_title("Test accuracy", fontsize=10.5, fontweight="bold")
    ax1.set_ylabel("%", fontsize=9)
    # contradiction recall
    b2 = ax2.bar(["Full\nengine", "Ablation\n(safety off)"], [100.0, 0.0], color=[GREEN, RED], width=0.5, zorder=3)
    ax2.text(0, 102, "4 / 4 caught", ha="center", fontsize=9, fontweight="bold", color=GREEN)
    ax2.text(1, 4, "0 / 4 caught", ha="center", fontsize=9, fontweight="bold", color=RED)
    ax2.set_ylim(0, 110)
    ax2.set_title("Contradiction recall", fontsize=10.5, fontweight="bold")
    for ax in (ax1, ax2):
        for s in ["top", "right"]:
            ax.spines[s].set_visible(False)
        ax.tick_params(labelsize=8.3)
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color=HAIR, lw=0.8)
    fig.suptitle("Turning the safety layers off is what proves they work", fontsize=11.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    return save(fig, "eval_ablation.png")


def fig_architecture():
    fig, ax = _canvas(9.6, 4.7, 9.6, 4.7)
    label(ax, 4.8, 4.45, "System architecture at a glance", fs=13.5, fw="bold")

    titled_box(ax, 0.5, 3.3, 2.6, 0.9, BRAND, "Frontend", "React 19 · Vite · TS", tc="white", sc="#d3d8f6", fs=11, subfs=8)
    titled_box(ax, 3.5, 3.3, 2.6, 0.9, TEAL, "FastAPI", "REST API layer", tc="white", sc="#cfe8ec", fs=11, subfs=8)
    titled_box(ax, 6.5, 3.3, 2.6, 0.9, "#334155", "SQLite", "aiosqlite · WAL", tc="white", sc="#d5dbe4", fs=11, subfs=8)
    arrow(ax, 3.1, 3.75, 3.5, 3.75, color=INK_SOFT)
    arrow(ax, 6.1, 3.6, 6.5, 3.6, color=INK_SOFT)
    label(ax, 3.3, 3.95, "/api", fs=7.2, color=MUTED)

    # engine modules
    box(ax, 0.5, 0.5, 8.6, 2.45, CANVAS, ec=HAIR, lw=1.2, r=0.05)
    label(ax, 4.8, 2.7, "Backend engine  (backend/src)", fs=9.8, fw="bold", color=INK)
    mods = [("domain", "models · enums · rules"), ("ingestion", "CSV/JSON/PDF/TXT"),
            ("extraction", "LLM + mock + regex"), ("verification", "requirements · CE 3.0 · grounding"),
            ("scoring", "strength-weighted"), ("security", "injection · uploads"),
            ("orchestrator", "analyze · gate (pure)"), ("packaging", "draft-only mapper")]
    for i, (m, s) in enumerate(mods):
        col = i % 4
        row = i // 4
        x = 0.75 + col * 2.08
        y = 1.75 - row * 0.95
        box(ax, x, y, 1.9, 0.78, "white", ec=HAIR, lw=1.0, r=0.08)
        label(ax, x + 0.95, y + 0.5, m, fs=8.6, fw="bold", color=TEAL)
        label(ax, x + 0.95, y + 0.22, s, fs=6.7, color=MUTED)

    pill(ax, 6.95, 2.5, 2.05, 0.4, "LLM: Gemini / Mock", BRAND, fs=7.4)
    label(ax, 4.8, 0.18, "The LLM plugs into “extraction” behind a protocol; with no API key a deterministic mock runs the whole engine offline.",
          fs=7.9, color=MUTED)
    return save(fig, "architecture.png")


def fig_tabs():
    fig, ax = _canvas(9.6, 1.5, 9.6, 1.5)
    label(ax, 4.8, 1.28, "The workbench — seven tabs per case", fs=11.5, fw="bold")
    tabs = ["Overview", "Requirements", "Score", "Timeline", "Evidence", "Package", "Audit"]
    w = 1.24
    gap = 0.09
    total = len(tabs) * w + (len(tabs) - 1) * gap
    x = (9.6 - total) / 2
    for i, t in enumerate(tabs):
        c = BRAND if i == 0 else "white"
        tc = "white" if i == 0 else INK_SOFT
        box(ax, x, 0.35, w, 0.55, c, ec=HAIR if i else BRAND, lw=1.1, r=0.10)
        label(ax, x + w / 2, 0.625, t, fs=8.0, fw="bold", color=tc)
        x += w + gap
    return save(fig, "tabs.png")


ALL = [fig_ecosystem, fig_lifecycle, fig_naive_vs_shield, fig_pipeline, fig_grounding,
       fig_scoring, fig_gate, fig_scenario_a, fig_scenario_b, fig_scenario_c, fig_scenario_d,
       fig_eval_beforeafter, fig_eval_ablation, fig_architecture, fig_tabs]

if __name__ == "__main__":
    for fn in ALL:
        p = fn()
        print("wrote", os.path.basename(p))
    print(f"\n{len(ALL)} figures -> {ASSETS}")
