"""Plain-English Role 3 + Role 4 flowchart for non-technical readers.

Writes output/pdf/Role3_Role4_Simple_Flowchart.pdf (A3 landscape, 2 pages).
Does not replace the team workflow PDF.
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf/Role3_Role4_Simple_Flowchart.pdf"

W, H = 1190.551, 841.8898  # A3 landscape

NAVY = colors.HexColor("#17324D")
INK = colors.HexColor("#17232F")
MUTED = colors.HexColor("#5C6975")
WHITE = colors.white
ORANGE = colors.HexColor("#E67E22")
ORANGE_PALE = colors.HexColor("#FFF2DC")
PURPLE = colors.HexColor("#6750A4")
PURPLE_PALE = colors.HexColor("#F0ECF8")
TEAL = colors.HexColor("#0F8B8D")
TEAL_PALE = colors.HexColor("#E4F4F4")
GREEN = colors.HexColor("#2E8B57")
GREEN_PALE = colors.HexColor("#E8F6EE")
RED = colors.HexColor("#C0392B")
RED_PALE = colors.HexColor("#FDECEA")
AMBER = colors.HexColor("#945511")
PAPER = colors.HexColor("#F7F4EE")
LINE = colors.HexColor("#D5DDE5")


def p(c, text, x, top, width, size=10.2, leading=None, color=INK, bold=False, align=0):
    sty = ParagraphStyle(
        "p",
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        leading=leading or size * 1.32,
        textColor=color,
        alignment=align,
    )
    a = Paragraph(text, sty)
    _, height = a.wrap(width, H)
    a.drawOn(c, x, H - top - height)
    return height


def rect(c, x, top, w, h, fill, r=8, stroke=None, sw=1):
    c.setFillColor(fill)
    c.setStrokeColor(stroke or fill)
    c.setLineWidth(sw)
    if r:
        c.roundRect(x, H - top - h, w, h, r, fill=1, stroke=int(stroke is not None))
    else:
        c.rect(x, H - top - h, w, h, fill=1, stroke=int(stroke is not None))


def header_bar(c, page, subtitle):
    rect(c, 0, 0, W, H, PAPER, r=0)
    rect(c, 0, 0, W, 58, NAVY, r=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(36, H - 28, "AI Emergency Intake")
    c.setFont("Helvetica", 11)
    c.drawString(230, H - 28, "Role 3 and Role 4  —  a simple picture")
    c.setFont("Helvetica", 9)
    c.drawRightString(W - 36, H - 28, f"Page {page} of 2")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9)
    c.drawString(36, 22, "For teammates who are not writing the code. Technical names are in the team workflow PDF.")
    c.drawRightString(W - 36, 22, subtitle)


def arrow_down(c, x, y_from_top, length=18, color=NAVY):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(1.6)
    y1 = H - y_from_top
    y2 = y1 - length
    c.line(x, y1, x, y2 + 5)
    path = c.beginPath()
    path.moveTo(x, y2)
    path.lineTo(x - 5, y2 + 8)
    path.lineTo(x + 5, y2 + 8)
    path.close()
    c.drawPath(path, fill=1, stroke=0)


def arrow_right(c, x, y_from_top, length=28, color=NAVY):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(1.6)
    y = H - y_from_top
    c.line(x, y, x + length - 6, y)
    path = c.beginPath()
    path.moveTo(x + length, y)
    path.lineTo(x + length - 8, y + 5)
    path.lineTo(x + length - 8, y - 5)
    path.close()
    c.drawPath(path, fill=1, stroke=0)


def pill(c, label, x, top, fill, text_color, w=None):
    width = w or (len(label) * 6.2 + 18)
    rect(c, x, top, width, 16, fill, r=8)
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x + width / 2, H - top - 12, label)
    return width


def step_box(c, n, title, body, x, top, w, h, accent, pale):
    rect(c, x, top, w, h, WHITE, r=10, stroke=LINE, sw=1)
    rect(c, x, top, 8, h, accent, r=0)
    # number circle
    c.setFillColor(accent)
    c.circle(x + 28, H - top - 22, 11, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(x + 28, H - top - 26, str(n))
    p(c, title, x + 46, top + 10, w - 58, size=11, color=INK, bold=True)
    p(c, body, x + 18, top + 32, w - 32, size=9.2, leading=12.2, color=MUTED)


def page1(c):
    header_bar(c, 1, "Who does what")

    p(
        c,
        "Think of the hospital: <b>Role 3 is the front desk</b>. <b>Role 4 is the locked records room</b>. "
        "Staff never walk into the records room themselves. Everything goes through the front desk.",
        36,
        76,
        W - 72,
        size=13,
        leading=18,
        color=INK,
    )

    # Two job cards
    left, right, gap = 36, 610, 24
    card_w, card_h = 564, 250
    rect(c, left, 118, card_w, card_h, WHITE, r=14, stroke=ORANGE, sw=2)
    rect(c, left, 118, card_w, 52, ORANGE, r=0)
    # cover bottom of header radius
    rect(c, left, 154, card_w, 16, ORANGE, r=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left + 20, H - 150, "Role 3  —  The front desk")
    c.setFont("Helvetica", 11)
    c.drawString(left + 320, H - 150, "Mozzam Shahid")

    jobs3 = [
        ("Checks the badge", "Is this person allowed to send or review this case? The computer does not trust a name typed on a form."),
        ("Checks the paperwork", "Is the draft complete and in the agreed shape? If not, it is sent back with a plain reason."),
        ("Keeps everyone in sync", "When a new draft arrives, the staff screen updates live. Staff do not need to refresh."),
        ("Hands work to records", "Looks up a patient, and later files an approved case — but Role 3 never stores the final record itself."),
    ]
    y = 182
    for title, body in jobs3:
        c.setFillColor(ORANGE)
        c.circle(left + 28, H - y - 8, 5, fill=1, stroke=0)
        p(c, f"<b>{title}.</b> {body}", left + 42, y, card_w - 62, size=9.6, leading=12.6, color=INK)
        y += 44

    rect(c, right, 118, card_w, card_h, WHITE, r=14, stroke=PURPLE, sw=2)
    rect(c, right, 118, card_w, 52, PURPLE, r=0)
    rect(c, right, 154, card_w, 16, PURPLE, r=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(right + 20, H - 150, "Role 4  —  The records room")
    c.setFont("Helvetica", 11)
    c.drawString(right + 330, H - 150, "Ishaan Sama")

    jobs4 = [
        ("Looks up the patient", "Have we seen this person before? Answers: found, not found, or the notes disagree."),
        ("Files the approved case once", "Only after a clinician approves. A second click with the same request does not create a second file."),
        ("Keeps a locked diary", "Who changed what, and when. That diary cannot be quietly edited or deleted."),
        ("Protects private details", "Sensitive words are locked. Dispatchers see less than clinicians. Old keys can be destroyed after the keep period."),
    ]
    y = 182
    for title, body in jobs4:
        c.setFillColor(PURPLE)
        c.circle(right + 28, H - y - 8, 5, fill=1, stroke=0)
        p(c, f"<b>{title}.</b> {body}", right + 42, y, card_w - 62, size=9.6, leading=12.6, color=INK)
        y += 44

    # Who talks to whom: 1 → 2 → 3 → 5, with Role 4 under Role 3
    p(c, "Who talks to whom", 36, 388, 400, size=14, color=NAVY, bold=True)
    p(
        c,
        "The staff screen never writes to the records room. The AI never writes there either. Only the front desk is allowed in.",
        36,
        410,
        W - 72,
        size=10.5,
        color=MUTED,
    )

    bw, bh = 190, 70
    row_top = 438
    # four main boxes, centred: 1 2 3 5
    main = [
        (80, "Role 1", "Voice call", "Soha", TEAL, TEAL_PALE),
        (340, "Role 2", "AI draft", "Fazwan", colors.HexColor("#1F6FEB"), colors.HexColor("#EAF2FF")),
        (600, "Role 3", "Front desk", "Mozzam", ORANGE, ORANGE_PALE),
        (860, "Role 5", "Staff screen", "Jonathan", GREEN, GREEN_PALE),
    ]
    for x, role, job, name, accent, pale in main:
        rect(c, x, row_top, bw, bh, pale, r=12, stroke=accent, sw=1.5)
        p(c, role, x + 8, row_top + 8, bw - 16, size=11, color=accent, bold=True, align=1)
        p(c, f"<b>{job}</b>  ·  {name}", x + 8, row_top + 32, bw - 16, size=10, color=INK, align=1)

    for x in (270, 530):
        arrow_right(c, x, row_top + 35, 70, NAVY)
    arrow_right(c, 790, row_top + 35, 70, GREEN)

    # Role 4 hangs off Role 3
    r4x, r4top = 600, 548
    arrow_down(c, 600 + bw / 2, row_top + bh, 28, PURPLE)
    rect(c, r4x, r4top, bw, bh, PURPLE_PALE, r=12, stroke=PURPLE, sw=1.5)
    p(c, "Role 4", r4x + 8, r4top + 8, bw - 16, size=11, color=PURPLE, bold=True, align=1)
    p(c, "<b>Records room</b>  ·  Ishaan", r4x + 8, r4top + 32, bw - 16, size=10, color=INK, align=1)
    p(
        c,
        "Look up a patient, then file the approved case. Answers: found / not found / notes disagree / already filed.",
        800,
        560,
        340,
        size=10,
        leading=13.5,
        color=PURPLE,
    )

    # Three golden rules
    p(c, "Three things everyone should remember", 36, 638, 500, size=14, color=NAVY, bold=True)
    rules = [
        (ORANGE, "The computer does not decide.", "The AI draft is a helper. A qualified human still checks, corrects, and approves. There is no automatic diagnosis or final triage."),
        (PURPLE, "One door into the records.", "The staff screen and the AI never write to the database. Role 3 checks the person, then Role 4 files the record."),
        (TEAL, "Practice data only for now.", "Names look like TEST-PATIENT. Notes start with SYN:. Real patient details, recordings, and passwords stay out of GitHub."),
    ]
    rx = 36
    rw = 362
    for accent, title, body in rules:
        rect(c, rx, 662, rw, 92, WHITE, r=12, stroke=accent, sw=1.6)
        rect(c, rx, 662, rw, 8, accent, r=0)
        p(c, title, rx + 16, 676, rw - 32, size=11.5, color=accent, bold=True)
        p(c, body, rx + 16, 698, rw - 32, size=9.4, leading=12.6, color=INK)
        rx += rw + 16


def page2(c):
    header_bar(c, 2, "The story, start to finish")
    p(
        c,
        "Follow the numbered steps. Orange boxes are the front desk (Role 3). Purple boxes are the records room (Role 4). Green is the staff member.",
        36,
        74,
        W - 72,
        size=11.5,
        leading=15,
        color=MUTED,
    )

    # Left column: intake + lookup
    col1, col2 = 36, 610
    w = 544

    p(c, "Getting the case in", col1, 96, w, size=11.5, color=NAVY, bold=True)
    p(c, "Human review and filing", col2, 96, w, size=11.5, color=NAVY, bold=True)

    step_box(
        c, 1, "A draft case arrives",
        "The voice call becomes text. The AI turns that into a structured draft: what hurts, what is missing, what disagrees, and what staff should notice. That draft is sent to the front desk.",
        col1, 114, w, 80, colors.HexColor("#1F6FEB"), colors.HexColor("#EAF2FF"),
    )
    arrow_down(c, col1 + w / 2, 194, 14)

    step_box(
        c, 2, "Front desk checks three things (Role 3)",
        "<b>Who</b> is sending this? <b>Is the form complete?</b> <b>Is this a newer version</b> than the one we already have? A repeat of the same request is treated as “we already have this,” not as a second case.",
        col1, 212, w, 90, ORANGE, ORANGE_PALE,
    )

    # reject / accept split
    arrow_down(c, col1 + 140, 302, 14)
    arrow_down(c, col1 + 400, 302, 14)
    step_box(
        c, "×", "Sent back",
        "Wrong person, incomplete form, or an older version. Staff see a clear message, not a crash.",
        col1, 320, 250, 74, RED, RED_PALE,
    )
    step_box(
        c, 3, "Accepted — staff screen updates",
        "The live staff screen shows the draft, gaps, conflicts, and confidence. No refresh needed.",
        col1 + 274, 320, 270, 74, GREEN, GREEN_PALE,
    )
    arrow_down(c, col1 + 400, 394, 14)

    step_box(
        c, 4, "Need history? Front desk asks records (Role 3 → Role 4)",
        "“Do we already know this patient?” Role 3 asks. Role 5 (the screen) is not allowed to ask the records room directly.",
        col1, 412, w, 78, ORANGE, ORANGE_PALE,
    )
    arrow_down(c, col1 + w / 2, 490, 14)

    step_box(
        c, 5, "Records room answers (Role 4)",
        "<b>Found</b> — send the notes (clinicians see more; dispatchers see less). <b>Not found</b> — say so clearly. <b>Notes disagree</b> — flag the conflict so a human can sort it out. The answer goes back through Role 3, then the AI can update the draft.",
        col1, 508, w, 96, PURPLE, PURPLE_PALE,
    )

    # Right column: review + save
    step_box(
        c, 6, "Staff review the draft (Role 5)",
        "A clinician can save a draft, ask for more information, or approve. They can correct fields. Those corrections are protected so a later AI update does not wipe them.",
        col2, 114, w, 80, GREEN, GREEN_PALE,
    )
    arrow_down(c, col2 + w / 2, 194, 14)

    step_box(
        c, 7, "Front desk checks the reviewer (Role 3)",
        "Identity comes from the signed-in badge, not from a name in the message. If the case changed while they were reading, they get “please look at the latest version” instead of overwriting someone else’s work.",
        col2, 212, w, 90, ORANGE, ORANGE_PALE,
    )
    arrow_down(c, col2 + w / 2, 302, 14)

    step_box(
        c, 8, "If they approve — hand to records (Role 3 → Role 4)",
        "Only then does Role 3 ask Role 4 to file the finished case, the triage the human chose, and the list of corrections.",
        col2, 320, w, 74, ORANGE, ORANGE_PALE,
    )
    arrow_down(c, col2 + w / 2, 394, 14)

    step_box(
        c, 9, "Filed once, with a locked diary (Role 4)",
        "The approved record is stored. Sensitive details are locked. The diary records who approved, what changed, and when. The same request again returns the original file — it does not create a duplicate.",
        col2, 412, w, 78, PURPLE, PURPLE_PALE,
    )
    arrow_down(c, col2 + w / 2, 490, 14)

    step_box(
        c, 10, "Staff screen is told “saved” (Role 3 → Role 5)",
        "The front desk publishes the result. The reviewer sees that the case is approved and filed. The loop is closed.",
        col2, 508, w, 96, GREEN, GREEN_PALE,
    )

    # Bottom banner
    rect(c, 36, 622, W - 72, 88, NAVY, r=12)
    p(
        c,
        "If you remember only one picture",
        56,
        634,
        W - 110,
        size=13,
        color=WHITE,
        bold=True,
    )
    p(
        c,
        "Call → AI draft → <b>Role 3 checks it and shows it live</b> → staff review → <b>Role 3 checks the reviewer</b> → "
        "<b>Role 4 files it once and writes the diary</b> → staff see “saved”. "
        "Role 3 is the door. Role 4 is the vault. A human still makes the final call.",
        56,
        658,
        W - 110,
        size=11,
        leading=15,
        color=colors.HexColor("#D6E4F0"),
    )


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=(W, H))
    page1(c)
    c.showPage()
    page2(c)
    c.save()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
