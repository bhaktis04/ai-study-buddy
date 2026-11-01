import re
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

TEAL = colors.HexColor("#0E7C86")

# The built-in PDF fonts only cover Latin characters, so swap common symbols
_REPLACEMENTS = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u2022": "-",
    "\u00a0": " ", "\u2192": "->", "\u2264": "<=", "\u2265": ">=",
}


def _clean(text):
    text = str(text or "")
    for bad, good in _REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


def _rich(text):
    """Escape the text, then turn **bold** and `code` into PDF markup."""
    text = escape(_clean(text))
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", text)
    return text


def _paragraphs(text, style):
    out = []
    for line in str(text or "").splitlines():
        line = re.sub(r"^\s*[*\-]\s+", "- ", line.strip())
        if line:
            out.append(Paragraph(_rich(line), style))
    return out or [Paragraph("-", style)]


def _stats(log):
    scores = [e["score"] for e in log if e.get("score") is not None]
    avg = sum(scores) / len(scores) if scores else None
    return len(log), avg


def _score_text(score):
    return f"{score:g}/10" if score is not None else "n/a"


def report_filename(topic, ext):
    slug = re.sub(r"[^a-z0-9]+", "_", str(topic).lower()).strip("_") or "interview"
    return f"interview_report_{slug}_{datetime.now():%Y%m%d}.{ext}"


def build_markdown(topic, level, log, when=None):
    """Return the interview report as a Markdown string."""
    when = when or datetime.now()
    answered, avg = _stats(log)
    avg_text = f"{avg:.1f}/10" if avg is not None else "n/a"

    lines = [
        f"# Interview report: {topic}",
        "",
        f"- **Level:** {level}",
        f"- **Date:** {when:%Y-%m-%d %H:%M}",
        f"- **Questions answered:** {answered}",
        f"- **Average score:** {avg_text}",
        "",
        "## Summary",
        "",
        "| # | Question | Score |",
        "|---|---|---|",
    ]
    for i, e in enumerate(log, 1):
        q = e["question"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {i} | {q} | {_score_text(e.get('score'))} |")

    lines += ["", "## Detailed feedback", ""]
    for i, e in enumerate(log, 1):
        quoted = "\n".join("> " + ln for ln in e["answer"].splitlines() or [""])
        lines += [
            f"### Question {i}",
            "",
            f"**{e['question']}**",
            "",
            "**Your answer:**",
            "",
            quoted,
            "",
            e["feedback"],
            "",
            "---",
            "",
        ]
    return "\n".join(lines)


def build_pdf(topic, level, log, when=None):
    """Return the interview report as PDF bytes."""
    when = when or datetime.now()
    answered, avg = _stats(log)
    avg_text = f"{avg:.1f}/10" if avg is not None else "n/a"

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=_clean(f"Interview report: {topic}"),
    )

    base = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=base["Title"], fontSize=20, alignment=0,
                           textColor=TEAL, spaceAfter=6)
    h2 = ParagraphStyle("H2", parent=base["Heading2"], fontSize=14, spaceBefore=14, spaceAfter=6)
    h3 = ParagraphStyle("H3", parent=base["Heading3"], fontSize=11.5, textColor=TEAL,
                        spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("B", parent=base["BodyText"], fontSize=10, leading=14, spaceAfter=4)
    quote = ParagraphStyle("Q", parent=body, leftIndent=10, fontName="Helvetica-Oblique",
                           textColor=colors.HexColor("#444444"))
    cell = ParagraphStyle("C", parent=body, fontSize=9.5, leading=12, spaceAfter=0)

    story = [
        Paragraph(_rich(f"Interview report: {topic}"), title),
        Paragraph(
            _rich(f"Level: {level}  |  Date: {when:%Y-%m-%d %H:%M}  |  "
                  f"Questions answered: {answered}  |  Average score: {avg_text}"),
            body,
        ),
        Paragraph("Summary", h2),
    ]

    rows = [["#", "Question", "Score"]]
    for i, e in enumerate(log, 1):
        rows.append([str(i), Paragraph(_rich(e["question"]), cell), _score_text(e.get("score"))])
    table = Table(rows, colWidths=[10 * mm, 135 * mm, 25 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D4DC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
    ]))
    story += [table, Paragraph("Detailed feedback", h2)]

    for i, e in enumerate(log, 1):
        story.append(Paragraph(f"Question {i}", h3))
        story.append(Paragraph(f"<b>{_rich(e['question'])}</b>", body))
        story.append(Paragraph("<b>Your answer</b>", body))
        story += _paragraphs(e["answer"], quote)
        story.append(Spacer(1, 4))
        story += _paragraphs(e["feedback"], body)

    doc.build(story)
    return buf.getvalue()


if __name__ == "__main__":
    from pathlib import Path

    sample = [
        {
            "question": "What is the difference between a list and a tuple in Python?",
            "answer": "A list is mutable and a tuple is immutable. Tuples use parentheses.",
            "feedback": (
                "**Score:** 8/10\n\n"
                "**What was good:** You nailed the core difference: mutability.\n\n"
                "**What to improve:** Mention hashability, so tuples can be dictionary keys.\n\n"
                "**Model answer:** Lists are mutable, tuples are immutable and hashable."
            ),
            "score": 8.0,
        },
        {
            "question": "What does the `@` symbol do above a function?",
            "answer": "I don't know.",
            "feedback": (
                "**Score:** 1/10\n\n"
                "**What was good:** Honesty.\n\n"
                "**What to improve:** Review decorators.\n\n"
                "**Model answer:** It applies a decorator that wraps the function."
            ),
            "score": 1.0,
        },
    ]
    Path("sample_report.md").write_text(build_markdown("Python", "fresher", sample), encoding="utf-8")
    Path("sample_report.pdf").write_bytes(build_pdf("Python", "fresher", sample))
    print("Wrote sample_report.md and sample_report.pdf")