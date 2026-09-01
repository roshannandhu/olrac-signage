"""The PDF a client receives as proof their advert ran.

Laid out to match the campaign report the client is expecting: a dark masthead, a row of
headline tiles, the creative beside a map of where it ran, a per-location table, and the
commercial detail (what was sold, what was extended, what is owed) side by side.

Built with ReportLab. The bands that bleed to the page edge are drawn on the canvas in
`_page_furniture`, because a Platypus flowable is confined to the text frame and would
leave white gutters down both sides.

Three things this deliberately does *not* do:

* It never fails because an image could not be drawn. Without a Google Maps key the map
  panel becomes a list of locations; without reachable object storage the creative panel
  becomes a caption. A client report that 500s is worse than one missing a picture.
* It never presents a total as final when it might not be. Screens that have not reported
  since the period ended are named on the page, because a client who is told 12,000 and
  later sees 12,400 loses confidence in every number you give them.
* It never quotes a plan's CURRENT price. Money comes from the booking, which copied its
  terms when it was sold; a tenant repricing a package must not restate an old invoice.
"""
import logging
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..maps import fetch_static_map

logger = logging.getLogger(__name__)

INK = colors.HexColor("#0b1437")        # masthead / footer band
NAVY = colors.HexColor("#1a2b5c")       # headings and table headers
MUTED = colors.HexColor("#64748b")
HAIRLINE = colors.HexColor("#e2e8f2")
TILE_BG = colors.HexColor("#f8fafc")
TOTAL_BG = colors.HexColor("#eaf1fb")
PLAN_BG = colors.HexColor("#f5f3ff")
PLAN_INK = colors.HexColor("#6d28d9")
OK_BG = colors.HexColor("#f0fdf4")
OK_INK = colors.HexColor("#16a34a")

PAGE_W, PAGE_H = A4
MARGIN = 14 * mm
BAND_H = 16 * mm
FOOTER_H = 16 * mm


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontSize=19, textColor=NAVY,
                                alignment=0, spaceAfter=2, leading=23),
        "sub": ParagraphStyle("s", parent=base["Normal"], fontSize=9, textColor=MUTED, leading=13),
        "h2": ParagraphStyle("h", parent=base["Normal"], fontSize=10.5, textColor=NAVY,
                             fontName="Helvetica-Bold", spaceBefore=2, spaceAfter=5),
        "body": ParagraphStyle("b", parent=base["Normal"], fontSize=8.5, leading=12.5),
        "note": ParagraphStyle("n", parent=base["Normal"], fontSize=7.5, textColor=MUTED, leading=10.5),
        "label": ParagraphStyle("l", parent=base["Normal"], fontSize=6.2, textColor=MUTED, leading=8.5),
        "value": ParagraphStyle("v", parent=base["Normal"], fontSize=12, textColor=NAVY,
                                fontName="Helvetica-Bold", leading=14.5),
        "value_sm": ParagraphStyle("vs", parent=base["Normal"], fontSize=8.5, textColor=NAVY,
                                   fontName="Helvetica-Bold", leading=11),
    }


def _date(value: datetime | None) -> str:
    return value.strftime("%d %b %Y") if value else "-"


def _money(paise: int | None) -> str:
    """Paise to rupees. Integer division throughout -- money never touches a float.

    "Rs." rather than the rupee sign deliberately. U+20B9 is in none of the fonts available
    here -- not the Type 1 standard set ReportLab defaults to, nor the Vera faces it
    bundles -- so it rendered as a black tofu box, on the amount-paid tile of an invoice. A
    box where the price should be is worse than a plainer prefix.

    To get the symbol back, ship a TTF that has it (Noto Sans) and register it with
    pdfmetrics; the whole document has to move to that face, since the tables and headings
    name Helvetica.
    """
    if not paise:
        return "Rs. 0"
    rupees, remainder = divmod(int(paise), 100)
    return f"Rs. {rupees:,}" if remainder == 0 else f"Rs. {rupees:,}.{remainder:02d}"


# Typographic characters that arrive from a word processor and have no glyph problem in
# theory but read badly at 8pt, plus the ones outside WinAnsi entirely. ReportLab does not
# RAISE on a character the font lacks -- it silently draws a box, which is how the rupee
# sign reached a client's amount-paid tile as a black square. Anything not handled here
# still risks that: the fix for non-Latin scripts (Devanagari, Malayalam) is to ship a TTF
# and register it, which changes the face of the whole document.
_TYPOGRAPHY = {
    "—": "-", "–": "-", "−": "-",
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", " ": " ", "₹": "Rs.",
}


def _safe(value) -> str:
    """Text with the punctuation a word processor inserts folded back to ASCII."""
    text = "" if value is None else str(value)
    for bad, good in _TYPOGRAPHY.items():
        text = text.replace(bad, good)
    return text


def _fetch_image(url: str | None) -> bytes | None:
    """The creative's bytes, or None. Never raises.

    Mirrors maps.fetch_static_map: an unreachable image degrades the page, it does not fail
    the report. Relevant in practice -- when object storage is unconfigured the uploads sit
    on an ephemeral disk and every thumbnail URL 404s after a redeploy.
    """
    if not url or not url.startswith(("http://", "https://")):
        return None
    try:
        import urllib.request

        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status != 200:
                logger.warning("Creative thumbnail request failed: HTTP %s", response.status)
                return None
            return response.read() or None
    except Exception as exc:  # noqa: BLE001 - a missing creative must not break the report
        logger.warning("Creative thumbnail could not be fetched: %s", exc)
        return None


def _card(rows, widths, extra=None, bg=colors.white, border=HAIRLINE, pad=7):
    """A rounded, hairline-bordered panel -- the repeated shape of this whole layout."""
    table = Table(rows, colWidths=widths)
    style = [
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.5, border),
        ("ROUNDEDCORNERS", [5, 5, 5, 5]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), pad),
        ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ("TOPPADDING", (0, 0), (-1, -1), pad - 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad - 2),
    ]
    table.setStyle(TableStyle(style + (extra or [])))
    return table


def _pill(style, text: str, ink, bg) -> Table:
    """A status chip. Its own one-cell table so the fill hugs the text, not the column."""
    chip = Table([[Paragraph(f'<font color="#{ink.hexval()[2:]}"><b>{text}</b></font>', style["body"])]])
    chip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return chip


def _tiles(style, cells: list[tuple[str, str, str]]) -> Table:
    """The headline strip: label, value, and a quiet sub-label under each."""
    tiles = []
    for label, value, sub in cells:
        inner = Table(
            [[Paragraph(label.upper(), style["label"])],
             [Paragraph(value, style["value"])],
             [Paragraph(sub, style["label"])]],
            colWidths=[(PAGE_W - 2 * MARGIN) / len(cells) - 4],
        )
        inner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), TILE_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, HAIRLINE),
            ("ROUNDEDCORNERS", [5, 5, 5, 5]),
            ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        tiles.append(inner)
    strip = Table([tiles], colWidths=[(PAGE_W - 2 * MARGIN) / len(cells)] * len(cells))
    strip.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return strip


def _grid(rows, widths, header=True) -> Table:
    """The data tables: navy header, zebra body, hairline grid."""
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, HAIRLINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TILE_BG]),
        ]
    table.setStyle(TableStyle(style))
    return table


def _band_color(value: str | None):
    """The tenant's brand colour, or the default ink. Never raises on a bad value.

    The column is pattern-validated on write, but a report must not 500 because a row
    predates that check or was set straight in the database.
    """
    if not value:
        return INK
    try:
        return colors.HexColor(value if value.startswith("#") else f"#{value}")
    except Exception:  # noqa: BLE001 - a bad colour is a cosmetic problem, not a failure
        logger.warning("Ignoring unusable brand colour %r", value)
        return INK


def _page_furniture(canvas, doc, org_name: str, generated: str, contact: str | None,
                    logo: bytes | None = None, band=INK):
    """The masthead and footer bands, drawn edge to edge.

    On the canvas rather than as flowables: Platypus confines a flowable to the text frame,
    so a band built that way stops at the margins and leaves white gutters down both sides.
    """
    canvas.saveState()

    canvas.setFillColor(band)
    canvas.rect(0, PAGE_H - BAND_H, PAGE_W, BAND_H, stroke=0, fill=1)

    # The tenant's mark, if they set one and it could be fetched. Drawn first so the name
    # can sit beside it; a logo that failed to load simply leaves the name where it was.
    text_x = MARGIN
    if logo:
        try:
            from reportlab.lib.utils import ImageReader

            mark = ImageReader(BytesIO(logo))
            width, height = mark.getSize()
            # Fitted to the band height rather than a fixed box, so a wide wordmark and a
            # square icon both sit on the same baseline instead of one overflowing.
            drawn_h = BAND_H - 7 * mm
            drawn_w = min(drawn_h * (width / height if height else 1), 45 * mm)
            canvas.drawImage(mark, MARGIN, PAGE_H - BAND_H + 3.5 * mm,
                             width=drawn_w, height=drawn_h, mask="auto",
                             preserveAspectRatio=True, anchor="sw")
            text_x = MARGIN + drawn_w + 4 * mm
        except Exception as exc:  # noqa: BLE001 - a bad logo must not break the report
            logger.warning("Brand logo could not be drawn: %s", exc)

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(text_x, PAGE_H - BAND_H + 5.5 * mm, org_name[:48])
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - BAND_H + 6 * mm, f"Report generated on: {generated}")

    canvas.setFillColor(TILE_BG)
    canvas.rect(0, 0, PAGE_W, FOOTER_H, stroke=0, fill=1)
    canvas.setStrokeColor(HAIRLINE)
    canvas.line(0, FOOTER_H, PAGE_W, FOOTER_H)
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN, FOOTER_H - 6.5 * mm, f"Thank you for choosing {org_name[:40]}.")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    if contact:
        canvas.drawString(MARGIN, FOOTER_H - 10.5 * mm, f"For any queries, contact {contact}")
    canvas.drawRightString(PAGE_W - MARGIN, FOOTER_H - 6.5 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def build_pdf(report: dict) -> bytes:
    """Render a booking report dict (from build_booking_report) into PDF bytes."""
    style = _styles()
    buffer = BytesIO()
    # .get throughout for the commercial blocks: an older caller (or a test fixture) may
    # still build a report dict without them, and a missing plan must not raise here.
    org = report.get("organization") or {}
    org_name = _safe(org.get("name")) or "Signage network"
    client = report.get("client") or {"name": report["advertiser"]}
    ends_at = report.get("effective_ends_at") or report["ends_at"]
    totals = report["totals"]
    generated = report["generated_at"].strftime("%d %b %Y %H:%M UTC")

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=BAND_H + 6 * mm, bottomMargin=FOOTER_H + 5 * mm,
        title=f"Campaign report - {report['advertiser']}",
        author=org_name,
    )
    # Fetched once, not per page: this is a network call and the report can run to three
    # pages. Fails soft like the creative and the map -- see _fetch_image.
    logo = _fetch_image(org.get("logo"))
    band = _band_color(org.get("brand_color"))
    furniture = lambda canvas, d: _page_furniture(  # noqa: E731
        canvas, d, org_name, generated, org.get("email"), logo=logo, band=band)

    story = []
    content_w = PAGE_W - 2 * MARGIN

    # --- title, and who it is for -----------------------------------------------------
    who = [f"<b>{_safe(client.get('name')) or '-'}</b>"]
    if client.get("client_code"):
        who.append(f"Client ID: {_safe(client['client_code'])}")
    if client.get("email"):
        who.append(f"Email: {_safe(client['email'])}")
    if client.get("phone"):
        who.append(f"Phone: {_safe(client['phone'])}")

    story.append(Table(
        [[
            [Paragraph("SIGNAGE CAMPAIGN REPORT", style["title"]),
             Paragraph("Campaign performance summary for your digital signage ads.", style["sub"])],
            _card(
                [[Paragraph("REPORT FOR", style["label"])],
                 [Paragraph("<br/>".join(who), style["body"])]],
                [72 * mm], bg=TILE_BG,
            ),
        ]],
        colWidths=[content_w - 76 * mm, 76 * mm],
        style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                          ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]),
    ))
    story.append(Spacer(1, 6 * mm))

    # --- headline tiles ---------------------------------------------------------------
    story.append(_tiles(style, [
        ("Campaign period", f"{_date(report['starts_at'])}<br/>to {_date(ends_at)}", "Start to end"),
        ("Total locations", str(len(report["per_location"])), "Active locations"),
        ("Total ad plays", f"{totals['total_plays']:,}", "Total count"),
        ("Days remaining", f"{report.get('days_remaining', 0)} days", f"of {report.get('days_total', 0)} days"),
        ("Amount paid", _money(report.get("total_price_paise", report["price_paise"])),
         "Booking + extensions" if report.get("extensions") else "Booking total"),
    ]))
    story.append(Spacer(1, 6 * mm))

    # --- the creative, and where it ran -----------------------------------------------
    creative = _fetch_image(report.get("content_thumbnail"))
    located = [s for s in report["per_screen"] if s.get("latitude") and s.get("longitude")]
    map_bytes = fetch_static_map(located, width=760, height=420) if located else None

    left = (Image(BytesIO(creative), width=58 * mm, height=58 * mm, kind="proportional")
            if creative else Paragraph("Creative preview unavailable.", style["note"]))
    if map_bytes:
        right = Image(BytesIO(map_bytes), width=104 * mm, height=57 * mm)
    elif located:
        # A key is no longer what stands between a tenant and a map -- maps.py draws one
        # from OpenStreetMap tiles when Google is not configured. Reaching here means the
        # tiles could not be fetched at all, which is a network problem and temporary.
        right = Paragraph(
            "Map could not be drawn just now. The locations are listed below.", style["note"])
    else:
        # Nothing to draw: no screen on this booking has coordinates set.
        right = Paragraph(
            "No coordinates set for these screens, so no map can be drawn.", style["note"])

    story.append(Table(
        [[
            _card([[Paragraph("AD THUMBNAIL", style["label"])], [left]], [64 * mm]),
            _card([[Paragraph("LOCATIONS IN MAP", style["label"])], [right]], [112 * mm]),
        ]],
        colWidths=[66 * mm, content_w - 66 * mm],
        style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                          ("LEFTPADDING", (0, 0), (0, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]),
    ))
    story.append(Spacer(1, 6 * mm))

    # --- per-location performance -----------------------------------------------------
    story.append(Paragraph("PERFORMANCE SUMMARY", style["h2"]))
    if report["per_location"]:
        rows = [["#", "LOCATION NAME", "LOCATION ID", "AD PLAYS PER DAY (AVG.)", "TOTAL PLAYS (PERIOD)"]]
        for index, place in enumerate(report["per_location"], 1):
            rows.append([
                str(index),
                _safe(place["location"]),
                # Positional, not an identifier the operator set anywhere: a location here
                # is a grouping of screens by name, and there is no location table to carry
                # a stable code. It matches the row it sits on and nothing else.
                f"LOC{index:03d}",
                f"{place.get('plays_per_day_avg', 0):,}",
                f"{place['total_plays']:,}",
            ])
        avg_total = sum(p.get("plays_per_day_avg", 0) for p in report["per_location"])
        rows.append(["", "TOTAL", "-", f"{avg_total:,.1f} (avg.)", f"{totals['total_plays']:,}"])

        table = _grid(rows, [10 * mm, 58 * mm, 28 * mm, 46 * mm, content_w - 142 * mm])
        table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("BACKGROUND", (0, -1), (-1, -1), TOTAL_BG),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, -1), (-1, -1), NAVY),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No locations were booked for this period.", style["body"]))

    story.append(PageBreak())
    # Everything appended past here lands on page two; the screen table below measures
    # against it to decide whether it fits.
    page_two_from = len(story)

    # --- campaign details | plan and extension ----------------------------------------
    running = "Active"
    if report["starts_at"] > report["generated_at"]:
        running = "Scheduled"
    elif ends_at < report["generated_at"]:
        running = "Ended"

    extensions = report.get("extensions") or []

    details = _grid([
        ["Campaign name", _safe(report["content_name"])],
        ["Start date", _date(report["starts_at"])],
        # Labelled "as sold" only when an extension moved the finish line. Without that the
        # card showed an end date of 16 Sep beside "Total days 46", which reads as an error
        # to the one person most likely to check it.
        ["End date (as sold)" if extensions else "End date", _date(report["ends_at"])],
    ] + ([["Extended to", _date(ends_at)]] if extensions else []) + [
        ["Total days", f"{report.get('days_total', '-')} days"],
        ["Days remaining", f"{report.get('days_remaining', '-')} days"],
        ["Amount paid", _money(report["price_paise"])],
    ], [34 * mm, 46 * mm], header=False)
    details.setStyle(TableStyle([("ALIGN", (1, 0), (1, -1), "RIGHT")]))

    status = Table(
        [[Paragraph("Payment status", style["body"]),
          _pill(style, "Paid" if report["is_paid"] else "Unpaid",
                OK_INK if report["is_paid"] else PLAN_INK,
                OK_BG if report["is_paid"] else PLAN_BG)],
         [Paragraph("Campaign status", style["body"]),
          _pill(style, running, OK_INK if running == "Active" else MUTED,
                OK_BG if running == "Active" else TILE_BG)]],
        colWidths=[34 * mm, 46 * mm],
    )
    status.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, HAIRLINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    plan = report.get("plan")
    plan_card = _card(
        [[Paragraph('<font color="#6d28d9"><b>CURRENT PLAN</b></font>', style["label"])],
         [Table([[Paragraph(_safe(plan["name"]) if plan else "No plan", style["value_sm"]),
                  Paragraph(f'<para align="right">{_money(report["price_paise"])}'
                            f'<font size="7" color="#64748b"> / {plan["duration_days"] if plan else report.get("days_total", 0)} days</font></para>',
                            style["value_sm"])]],
                colWidths=[42 * mm, 42 * mm],
                style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                  ("TOPPADDING", (0, 0), (-1, -1), 0),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))],
         [Paragraph(
             (plan.get("description")
              or f"{plan['max_locations']} locations | {plan['ad_slots']} ad slot(s) | {plan['support_tier']}")
             if plan else "Sold without a plan.", style["note"])]]
        # The card above prints the plan's inclusions. When the booking outgrew them, say so
        # here rather than leaving the client to notice that the table lists more locations
        # than the plan they are reading about allows.
        + ([[Paragraph(
            f"Running in {len(report['per_location'])} locations, "
            f"above this plan's {report.get('plan_max_locations')}.", style["note"])]]
           if report.get("plan_locations_exceeded") else []),
        [86 * mm], bg=PLAN_BG, border=colors.HexColor("#ddd6fe"),
    )

    if extensions:
        ext_rows = [[Paragraph('<font color="#16a34a"><b>EXTENDED PLAN</b></font>', style["label"]),
                     Paragraph('<para align="right"><font color="#16a34a"><b>Yes</b></font></para>', style["label"])]]
        for extension in extensions:
            ext_rows.append([Paragraph("Extended from", style["body"]),
                             Paragraph(f'<para align="right">{_date(extension["extended_from"])}</para>', style["body"])])
            ext_rows.append([Paragraph("Extended to", style["body"]),
                             Paragraph(f'<para align="right">{_date(extension["extended_to"])}</para>', style["body"])])
            ext_rows.append([Paragraph("Additional amount", style["body"]),
                             Paragraph(f'<para align="right">{_money(extension["additional_price_paise"])}</para>', style["body"])])
        ext_rows.append([Paragraph("<b>Total (incl. extension)</b>", style["body"]),
                         Paragraph(f'<para align="right"><b>{_money(report.get("total_price_paise", report["price_paise"]))}</b></para>', style["body"])])
        ext_card = _card(ext_rows, [46 * mm, 40 * mm], bg=OK_BG, border=colors.HexColor("#bbf7d0"))
    else:
        ext_card = _card(
            [[Paragraph("EXTENDED PLAN", style["label"])],
             [Paragraph("No extension sold on this booking.", style["note"])]],
            [86 * mm], bg=TILE_BG,
        )

    story.append(Table(
        [[Paragraph("CAMPAIGN DETAILS", style["h2"]), Paragraph("PLAN &amp; EXTENSION DETAILS", style["h2"])],
         [details, plan_card],
         ["", Spacer(1, 4)],
         [status, ext_card]],
        colWidths=[80 * mm, content_w - 84 * mm],
        style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                          ("LEFTPADDING", (0, 0), (0, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                          ("TOPPADDING", (0, 1), (-1, -1), 4)]),
    ))

    # --- screen-level delivery, but only when page two has room for it ----------------
    #
    # A client asking "you said 50,000 plays across 5 locations -- which screens?" deserves
    # an answer, so the detail is kept for a normal campaign. A forty-screen booking dumped
    # in full turns a sales document into a technical log and runs to four pages.
    #
    # Measured rather than capped at a screen count: ReportLab's own wrap() reports what a
    # flowable will actually occupy, so a table of long screen names is judged on its real
    # height. A hard "<= 12 rows" rule both overflows on long names and drops a table that
    # had room.
    if report["per_screen"]:
        rows = [["SCREEN", "LOCATION", "PLAYS", "COMPLETED"]]
        for screen in report["per_screen"]:
            rows.append([
                _safe(screen["screen_name"]) + (" *" if screen["counts_may_be_incomplete"] else ""),
                _safe(screen["location"]) or "-",
                f"{screen['total_plays']:,}",
                f"{screen['completed_plays']:,}",
            ])
        screen_table = _grid(rows, [56 * mm, 56 * mm, 35 * mm, content_w - 147 * mm])
        screen_table.setStyle(TableStyle([("ALIGN", (2, 0), (-1, -1), "RIGHT")]))

        used = sum(flowable.wrap(doc.width, doc.height)[1] for flowable in story[page_two_from:])
        heading = Paragraph("SCREEN-LEVEL DELIVERY", style["h2"])
        # 14mm of slack for the heading's spacing, the spacer and the closing footnote, so
        # a table that only just fits does not push the footnote onto a third page.
        remaining = doc.height - used - heading.wrap(doc.width, doc.height)[1] - 14 * mm

        if screen_table.wrap(doc.width, doc.height)[1] <= remaining:
            story.append(Spacer(1, 7 * mm))
            story.append(heading)
            story.append(screen_table)
        else:
            locations = len(report["per_location"])
            story.append(Spacer(1, 7 * mm))
            story.append(heading)
            story.append(Paragraph(
                f"{len(report['per_screen'])} screens across {locations} "
                f"location{'' if locations == 1 else 's'}. "
                "Screen-level playback is available in the campaign dashboard.",
                style["body"],
            ))

    story.append(Spacer(1, 5 * mm))
    footnote = (
        "Figures come from playback records reported by each screen and deduplicated on arrival."
    )
    if report["stale_screens"]:
        footnote += (
            " <b>*</b> These screens had not reported in by the time this report was produced, "
            "so their totals may rise once they reconnect: " + ", ".join(report["stale_screens"]) + "."
        )
    story.append(Paragraph(footnote, style["note"]))

    doc.build(story, onFirstPage=furniture, onLaterPages=furniture)
    return buffer.getvalue()
