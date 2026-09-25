import calendar
import io
from datetime import date
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from .classification import LEVEL_COLORS
from .nepali_date import to_bs_string, bs_month_range_label


def build_monthly_report_pdf(year, month, expenses, month_total, level):
    """
    Build a printable household expense report PDF covering all users'
    shared expenses for one month, and return it as a Django ContentFile.

    `expenses` should be an iterable of Expenses rows for that month,
    already sorted by date.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            topMargin=0.75 * inch,
                            bottomMargin = 0.75 * inch, 
                            leftMargin = 0.75 * inch,
                            rightMargin = 0.75 * inch,)

    styles = getSampleStyleSheet()
    story = []

    month_name = calendar.month_name[month]
    days_in_month = calendar.monthrange(year, month)[1]
    bs_range = bs_month_range_label(date(year, month, 1), date(year, month, days_in_month))
    level_color = colors.HexColor(LEVEL_COLORS.get(level, "#7f8c8d"))

    story.append(Paragraph("Household Expense Report", styles['Title']))
    story.append(Paragraph(f"{month_name} {year}", styles["Heading2"]))

    if bs_range:
        story.append(Paragraph(bs_range, styles["Normal"]))
    story.append(Spacer(1, 12))

    summary_table = Table(
        [
            ["Total for the Month", f"${month_total:,.2f}"],
            ["Spending Level", (level or "N/A").upper()],
        ],
        colWidths=[2.5*inch, 2.5*inch],
    )
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1, -1), 11),
        ("BOTTOMPADDING", (0,0), (-1, -1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BACKGROUND", (1,1), (1,1), level_color),
        ("TEXTCOLOR", (1,1), (1,1), colors.white),
        ("FONTNAME", (1,1), (1,1), "Helvetica-Bold"),
        ("GRID", (0,0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
    ]))

    story.append(summary_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("Daily Expenses",styles["Heading2"]))
    story.append(Spacer(1,8))

    table_data = [["Date", "Nepali Date", "Category", "Title", "Added By", "Amount"]]
    for e in expenses:
        table_data.append([
            e.date.strftime("%b %d, %Y"),
            to_bs_string(e.date, "%d %B %Y"),
            e.category,
            e.title,
            e.user.username,
            f"${e.amount:,.2f}",
        ])

    if len(table_data) == 1:
        story.append(Paragraph("No expenses recorded this month.", styles["Normal"]))
    else:
        detail_table = Table(table_data, colWidths=[1.0 * inch, 1.3 * inch, 1.0 * inch, 1.7 * inch, 0.9 * inch, 0.9 * inch], repeatRows=1)
        detail_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0,0), (-1, 0), colors.white),
            ("FONTNAME", (0,0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1, -1), 8),
            ("ALIGN", (5,0), (5, -1), "RIGHT"),
            ("GRID", (0,0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("ROWBACKGROUNDS", (0,1), (-1, -1), [colors.white, colors.HexColor("#f4f5f7")]),
            ("TOPPADDING", (0,0), (-1, -1), 5),
            ("BOTTOMPADDING", (0,0), (-1, -1), 5),
        ]))
        story.append(detail_table)


    doc.build(story)
    buffer.seek(0)
    filename = f"expense_report_{year}_{month:02d}.pdf"
    return ContentFile(buffer.read(), name=filename)