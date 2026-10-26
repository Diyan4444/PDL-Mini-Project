import os
from typing import Any, Dict, List
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)


def export_predictions_pdf(subject_name: str, predictions: List[Dict[str, Any]], filename: str = "study_sheet.pdf") -> str:
    """Generates a PDF study summary of predicted questions using ReportLab."""
    filepath = os.path.join(EXPORTS_DIR, filename)
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e7e34"),
        spaceAfter=10,
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#6c757d"),
        spaceAfter=15,
    )
    normal_style = styles["Normal"]
    
    story = [
        Paragraph(f"Exam Prediction & Revision Sheet: {subject_name}", title_style),
        Paragraph("Disclaimer: Predictions are generated purely via historical frequency, recency, and gap heuristics. They do not constitute a leaked or guaranteed examination paper.", disclaimer_style),
        Spacer(1, 10),
    ]

    table_data = [["No.", "Predicted Question", "Unit", "Likelihood", "Score"]]
    for idx, p in enumerate(predictions[:30]):
        table_data.append([
            str(idx + 1),
            Paragraph(p["question_text"][:140] + ("..." if len(p["question_text"]) > 140 else ""), normal_style),
            str(p["unit"]),
            p["likelihood"],
            f"{p['final_score']}%"
        ])

    table = Table(table_data, colWidths=[25, 330, 45, 75, 45])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#212529")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#ced4da")),
    ]))
    
    story.append(table)
    doc.build(story)
    return filepath
