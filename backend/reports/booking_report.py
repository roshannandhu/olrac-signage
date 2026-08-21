"""The PDF a client receives as proof their advert ran.

Built with ReportLab, following the export already in the analytics router. Every figure
comes from the deduplicated hourly rollups the players upload, scoped to the booking's own
window and screens by ``build_booking_report``.

Two things this deliberately does *not* do:

* It never fails because a map could not be drawn. Without a Google Maps key, or if the
  request fails, the map page becomes a list of locations.
* It never presents a total as final when it might not be. Screens that have not reported
  since the period ended are named on the page, because a client who is told 12,000 and
  later sees 12,400 loses confidence in every number you give them.
"""
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..maps import fetch_static_map, is_enabled as maps_enabled

NAVY = colors.HexColor("#14306b")
MUTED = colors.HexColor("#5a6a86")
HAIRLINE = colors.HexColor("#e2e8f2")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontSize=22, textColor=NAVY, spaceAfter=2),
        "sub": ParagraphStyle("s", parent=base["Normal"], fontSize=11, textColor=MUTED, spaceAfter=14),
        "h2": ParagraphStyle("h", parent=base["Heading2"], fontSize=13, textColor=NAVY, spaceBefore=10, spaceAfter=6),
        "body": ParagraphStyle("b", parent=base["Normal"], fontSize=9.5, leading=14),
        "note": ParagraphStyle("n", parent=base["Normal"], fontSize=8, textColor=MUTED, leading=11),
    }


def _date(value: datetime | None) -> str:
    return value.strftime("%d %b %Y") if value else "—"


def _table(rows: list[list[str]], widths: list[float]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, HAIRLINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def build_pdf(report: dict) -> bytes:
    """Render a booking report dict (from build_booking_report) into PDF bytes."""
    style = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Playback report — {report['advertiser']}",
        author="Olrac Signage",
    )
    story = []
    totals = report["totals"]

    story.append(Paragraph("Playback report", style["title"]))
    story.append(Paragraph(
        f"{report['advertiser']} &nbsp;·&nbsp; {report['content_name']}<br/>"
        f"{_date(report['starts_at'])} to {_date(report['ends_at'])}",
        style["sub"],
    ))

    headline = _table(
        [
            ["Total plays", "Completed", "Completion rate", "Screens"],
            [
                f"{totals['total_plays']:,}",
                f"{totals['completed_plays']:,}",
                f"{totals['success_percent']}%",
                str(len(report["per_screen"])),
            ],
        ],
        [42 * mm, 42 * mm, 42 * mm, 40 * mm],
    )
    headline.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTSIZE", (0, 1), (-1, 1), 15)]))
    story.append(headline)
    story.append(Spacer(1, 8 * mm))

    # Where it ran, as a map when one is available.
    story.append(Paragraph("Where it ran", style["h2"]))
    located = [s for s in report["per_screen"] if s.get("latitude") and s.get("longitude")]
    image_bytes = fetch_static_map(located) if located else None
    if image_bytes:
        story.append(Image(BytesIO(image_bytes), width=170 * mm, height=95 * mm))
        story.append(Spacer(1, 4 * mm))
    elif located and not maps_enabled():
        story.append(Paragraph(
            "Map unavailable — no maps key is configured. Locations are listed below.",
            style["note"],
        ))
        story.append(Spacer(1, 3 * mm))

    if report["per_location"]:
        story.append(_table(
            [["Location", "Screens", "Plays"]]
            + [[p["location"], str(p["screens"]), f"{p['total_plays']:,}"] for p in report["per_location"]],
            [96 * mm, 35 * mm, 35 * mm],
        ))

    story.append(PageBreak())

    story.append(Paragraph("Plays by screen", style["h2"]))
    if report["per_screen"]:
        rows = [["Screen", "Location", "Plays", "Completed"]]
        for screen in report["per_screen"]:
            name = screen["screen_name"] + (" *" if screen["counts_may_be_incomplete"] else "")
            rows.append([
                name,
                screen["location"] or "—",
                f"{screen['total_plays']:,}",
                f"{screen['completed_plays']:,}",
            ])
        story.append(_table(rows, [55 * mm, 55 * mm, 28 * mm, 28 * mm]))
    else:
        story.append(Paragraph("No screens were booked for this period.", style["body"]))

    if report["daily"]:
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("Plays per day", style["h2"]))
        story.append(_table(
            [["Date", "Plays"]] + [[d["date"], f"{d['total_plays']:,}"] for d in report["daily"]],
            [96 * mm, 70 * mm],
        ))

    story.append(Spacer(1, 8 * mm))
    footer = (
        "Figures come from playback records reported by each screen and deduplicated on "
        f"arrival. Report generated {report['generated_at'].strftime('%d %b %Y %H:%M UTC')}."
    )
    if report["stale_screens"]:
        footer += (
            " <b>*</b> These screens had not reported in by the time this report was produced, "
            "so their totals may rise once they reconnect: "
            + ", ".join(report["stale_screens"]) + "."
        )
    story.append(Paragraph(footer, style["note"]))

    doc.build(story)
    return buffer.getvalue()
