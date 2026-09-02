"""The commercial half of a booking: what was sold, what it cost, what was paid.

Split out of booking_report.py, which had grown into both documents at once -- proof of
delivery with the price, the paid/unpaid pill and the extension charges threaded through
its performance layout. That meant a tenant could not send a client evidence their advert
ran without also restating the terms, and there was no document that was actually an
invoice: the report was being forwarded in place of one.

Everything visual is imported from booking_report rather than restated. Two files drawing
the same letterhead would drift, and the one thing a client must never see is two documents
from the same tenant that do not look like the same company.
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .booking_report import (
    BAND_H,
    FOOTER_H,
    HAIRLINE,
    MARGIN,
    OK_BG,
    OK_INK,
    PAGE_H,
    PAGE_W,
    PLAN_BG,
    PLAN_INK,
    TILE_BG,
    TOTAL_BG,
    _band_color,
    _card,
    _date,
    _fetch_image,
    _money,
    _page_furniture,
    _pill,
    _safe,
    _styles,
)

# How a stored method code reads on paper. Anything unrecognised falls back to the code
# itself rather than to "Other", so a method added in the schema and forgotten here still
# prints something true.
METHOD_LABELS = {
    "cash": "Cash",
    "upi": "UPI",
    "bank_transfer": "Bank transfer",
    "cheque": "Cheque",
    "card": "Card",
    "other": "Other",
}


def invoice_number(report: dict) -> str:
    """A stable, human-quotable reference, derived rather than stored.

    Derived from ids that already exist, so there is no counter to keep and no way for two
    invoices to collide. It is NOT gapless -- a deleted booking leaves a hole -- which is
    fine for a reference a client quotes over the phone and would not be if an auditor
    needed a sequence. That is the upgrade path if it is ever required.
    """
    return f"INV-{report.get('organization_id', 0)}-{report['placement_id']:05d}"


def build_pdf(report: dict) -> bytes:
    """Render a booking report dict (from build_booking_report) as an invoice."""
    style = _styles()
    buffer = BytesIO()

    org = report.get("organization") or {}
    org_name = _safe(org.get("name")) or "Signage network"
    client = report.get("client") or {"name": report["advertiser"]}
    ends_at = report.get("effective_ends_at") or report["ends_at"]
    generated = report["generated_at"].strftime("%d %b %Y %H:%M UTC")
    number = invoice_number(report)

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=BAND_H + 5 * mm, bottomMargin=FOOTER_H + 4 * mm,
        title=f"Invoice {number} - {report['advertiser']}",
        author=org_name,
    )

    logo = _fetch_image(org.get("logo"))
    band = _band_color(org.get("brand_color"))
    furniture = lambda canvas, d: _page_furniture(  # noqa: E731
        canvas, d, org_name, generated, org.get("email"), logo=logo, band=band,
        label="Invoice issued")

    story = []
    content_w = PAGE_W - 2 * MARGIN

    # --- Title and who it is for --------------------------------------------------------
    who = [f"<b>{_safe(client.get('name')) or '-'}</b>"]
    if client.get("client_code"):
        who.append(f"Client ID: {_safe(client['client_code'])}")
    if client.get("email"):
        who.append(_safe(client["email"]))
    if client.get("phone"):
        who.append(_safe(client["phone"]))

    story.append(Table(
        [[Paragraph("INVOICE", style["title"]),
          _card([[Paragraph('<font color="#64748b"><b>BILL TO</b></font>', style["label"])],
                 [Paragraph("<br/>".join(who), style["body"])]],
                [72 * mm], bg=TILE_BG)]],
        colWidths=[content_w - 76 * mm, 76 * mm],
        style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                          ("LEFTPADDING", (0, 0), (-1, -1), 0),
                          ("RIGHTPADDING", (0, 0), (-1, -1), 0)]),
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        f"Invoice <b>{number}</b> &nbsp;|&nbsp; Issued {_date(report['generated_at'])}", style["note"]))
    story.append(Spacer(1, 5 * mm))

    # --- What was sold ------------------------------------------------------------------
    plan = report.get("plan")
    extensions = report.get("extensions") or []
    booking_price = report["price_paise"]

    # One row per thing charged. The booking, then each extension -- which is where an
    # upgrade's price difference lands, so an upgraded campaign reads as what it is: the
    # original deal plus what was added, on one invoice for one client.
    rows = [[Paragraph("<b>DESCRIPTION</b>", style["label"]),
             Paragraph('<para align="center"><b>PERIOD</b></para>', style["label"]),
             Paragraph('<para align="right"><b>AMOUNT</b></para>', style["label"])]]

    plan_line = _safe(plan["name"]) if plan else "Advertising campaign"
    rows.append([
        Paragraph(f"{plan_line}<br/><font size='7' color='#64748b'>"
                  f"{_safe(report['content_name'])} &middot; "
                  f"{len(report.get('per_location') or [])} location(s)</font>", style["body"]),
        Paragraph(f'<para align="center">{_date(report["starts_at"])}<br/>to {_date(report["ends_at"])}</para>',
                  style["body"]),
        Paragraph(f'<para align="right">{_money(booking_price)}</para>', style["body"]),
    ])
    for extension in extensions:
        rows.append([
            Paragraph(f"Extension<br/><font size='7' color='#64748b'>"
                      f"{_safe(extension.get('notes') or 'Additional airtime')}</font>", style["body"]),
            Paragraph(f'<para align="center">{_date(extension["extended_from"])}<br/>'
                      f'to {_date(extension["extended_to"])}</para>', style["body"]),
            Paragraph(f'<para align="right">{_money(extension["additional_price_paise"])}</para>', style["body"]),
        ])

    total = report.get("total_price_paise", booking_price)
    rows.append([
        Paragraph("<b>TOTAL</b>", style["body"]),
        Paragraph("", style["body"]),
        Paragraph(f'<para align="right"><b>{_money(total)}</b></para>', style["body"]),
    ])

    line_items = Table(rows, colWidths=[content_w - 76 * mm, 40 * mm, 36 * mm])
    line_items.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, HAIRLINE),
        ("BACKGROUND", (0, 0), (-1, 0), TILE_BG),
        ("BACKGROUND", (0, -1), (-1, -1), TOTAL_BG),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(line_items)
    story.append(Spacer(1, 5 * mm))

    # --- What was paid ------------------------------------------------------------------
    payment = report.get("payment")
    is_paid = bool(report.get("is_paid"))
    received = (payment or {}).get("amount_paise") or 0
    outstanding = (total or 0) - received if payment else 0
    # "Part paid" when the money received does not cover the total -- which is exactly what
    # an upgrade or an extension does until it is settled. Printing "Paid" above a line
    # reading "Outstanding 5,000" is the kind of contradiction a client rings up about.
    if payment and outstanding > 0:
        status_label, status_ink, status_bg = "Part paid", PLAN_INK, PLAN_BG
    elif is_paid:
        status_label, status_ink, status_bg = "Paid", OK_INK, OK_BG
    else:
        status_label, status_ink, status_bg = "Unpaid", PLAN_INK, PLAN_BG

    settled_rows = [[Paragraph("Status", style["body"]),
                     _pill(style, status_label, status_ink, status_bg)]]
    if payment:
        method = METHOD_LABELS.get(payment.get("method"), _safe(payment.get("method")))
        settled_rows.append([Paragraph("Method", style["body"]),
                             Paragraph(f'<para align="right">{method}</para>', style["body"])])
        settled_rows.append([Paragraph("Amount received", style["body"]),
                             Paragraph(f'<para align="right">{_money(payment.get("amount_paise"))}</para>', style["body"])])
        settled_rows.append([Paragraph("Received on", style["body"]),
                             Paragraph(f'<para align="right">{_date(payment.get("paid_at"))}</para>', style["body"])])
        if payment.get("reference"):
            settled_rows.append([Paragraph("Reference", style["body"]),
                                 Paragraph(f'<para align="right">{_safe(payment["reference"])}</para>', style["body"])])
        # An amount received that does not match the total is the single most useful thing
        # this document can point at, so it is stated rather than left to be worked out.
        if outstanding > 0:
            settled_rows.append([Paragraph("<b>Outstanding</b>", style["body"]),
                                 Paragraph(f'<para align="right"><b>{_money(outstanding)}</b></para>', style["body"])])

    settled = Table(settled_rows, colWidths=[36 * mm, 48 * mm])
    settled.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, HAIRLINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    terms = [[Paragraph('<font color="#6d28d9"><b>CAMPAIGN</b></font>', style["label"])],
             [Paragraph(f"Runs {_date(report['starts_at'])} to {_date(ends_at)}", style["body"])]]
    if plan:
        terms.append([Paragraph(
            f"{_safe(plan['name'])} &middot; {plan['duration_days']} days &middot; "
            f"up to {plan['max_locations']} location(s)", style["note"])])
    if extensions:
        terms.append([Paragraph(f"{len(extensions)} extension(s) sold against this booking.", style["note"])])

    story.append(Table(
        [[settled, _card(terms, [content_w - 92 * mm], bg=PLAN_BG,
                         border=colors.HexColor("#ddd6fe"))]],
        colWidths=[88 * mm, content_w - 88 * mm],
        style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                          ("LEFTPADDING", (0, 0), (-1, -1), 0),
                          ("RIGHTPADDING", (0, 0), (-1, -1), 0)]),
    ))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "This invoice covers the airtime sold for this campaign. Proof of delivery -- where "
        "the advert ran and how many times it played -- is issued separately as the "
        "playback report.", style["note"]))

    doc.build(story, onFirstPage=furniture, onLaterPages=furniture)
    return buffer.getvalue()
