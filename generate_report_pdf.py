"""Generate a readable PDF report from results.json."""
import json
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable,
)
from reportlab.lib import colors

INPUT_FILE = "results.json"
OUTPUT_FILE = "results_report.pdf"

def build_pdf():
    with open(INPUT_FILE) as f:
        data = json.load(f)

    doc = SimpleDocTemplate(
        OUTPUT_FILE,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "SectionHead",
        parent=styles["Heading2"],
        textColor=HexColor("#1a3c5e"),
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "FieldLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=HexColor("#333333"),
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        "FieldValue",
        parent=styles["Normal"],
        fontSize=10,
        leftIndent=12,
        spaceAfter=8,
        leading=14,
    ))
    styles.add(ParagraphStyle(
        "EmailBody",
        parent=styles["Normal"],
        fontSize=9.5,
        leftIndent=12,
        rightIndent=12,
        spaceAfter=8,
        leading=13,
        backColor=HexColor("#f5f5f5"),
        borderPadding=8,
    ))
    styles.add(ParagraphStyle(
        "CriteriaItem",
        parent=styles["Normal"],
        fontSize=9.5,
        leftIndent=24,
        spaceAfter=3,
        leading=12,
    ))

    story = []

    # Title page
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("JCNB Eval Run v1", styles["Title"]))
    story.append(Paragraph("Gemini 2.5 Flash", styles["Heading2"]))
    story.append(Spacer(1, 24))
    story.append(Paragraph(f"Model: {data['model']}", styles["Normal"]))
    story.append(Paragraph(f"Timestamp: {data['timestamp']}", styles["Normal"]))
    story.append(Paragraph(f"Prompt version: {data['prompt_version']}", styles["Normal"]))
    story.append(Paragraph(f"Cases: {len(data['results'])}", styles["Normal"]))
    story.append(PageBreak())

    for case in data["results"]:
        resp = case.get("llm_response", {})
        has_error = "error" in resp

        # Case header
        type_color = {"normal": "#2e7d32", "edge": "#e65100", "failure-prone": "#c62828"}
        tc = type_color.get(case["type"], "#333333")
        story.append(Paragraph(
            f'Case {case["id"]}: {case["label"]}',
            styles["SectionHead"],
        ))
        story.append(Paragraph(
            f'<font color="{tc}"><b>[{case["type"].upper()}]</b></font>',
            styles["Normal"],
        ))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#cccccc")))
        story.append(Spacer(1, 8))

        if has_error:
            story.append(Paragraph("ERROR", styles["FieldLabel"]))
            story.append(Paragraph(
                f'<font color="red">{resp["error"]}</font>',
                styles["FieldValue"],
            ))
        else:
            # Subject line
            story.append(Paragraph("Subject Line", styles["FieldLabel"]))
            subj = resp.get("subject_line", "N/A")
            story.append(Paragraph(subj, styles["FieldValue"]))

            # Email body
            story.append(Paragraph("Email Body", styles["FieldLabel"]))
            body = resp.get("email_body", "N/A")
            # Convert newlines to <br/> for PDF rendering
            body_html = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            body_html = body_html.replace("\n", "<br/>")
            # Restore markdown bold that was escaped
            body_html = body_html.replace("**", "<b>", 1)
            for _ in range(body_html.count("**")):
                body_html = body_html.replace("**", "</b>", 1)
                if "**" in body_html:
                    body_html = body_html.replace("**", "<b>", 1)
            story.append(Paragraph(body_html, styles["EmailBody"]))

            # Review flag
            review = resp.get("needs_human_review", "N/A")
            flag_color = "#c62828" if review else "#2e7d32"
            story.append(Paragraph("Needs Human Review", styles["FieldLabel"]))
            story.append(Paragraph(
                f'<font color="{flag_color}"><b>{review}</b></font>',
                styles["FieldValue"],
            ))

            reason = resp.get("review_reason")
            if reason:
                story.append(Paragraph("Review Reason", styles["FieldLabel"]))
                story.append(Paragraph(str(reason), styles["FieldValue"]))

        # Criteria
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#dddddd")))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Criteria to Check", styles["FieldLabel"]))
        for i, c in enumerate(case.get("good_output_criteria", []), 1):
            # Escape any HTML-like chars in criteria
            c_safe = c.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(f"{i}. {c_safe}", styles["CriteriaItem"]))

        # Grading fields
        story.append(Spacer(1, 12))
        pass_val = case.get("pass")
        notes_val = case.get("notes", "")
        pass_display = "___________" if pass_val is None else str(pass_val)
        notes_display = "___________________________________________" if not notes_val else notes_val

        story.append(Paragraph(f"Pass: {pass_display}", styles["FieldLabel"]))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"Notes: {notes_display}", styles["FieldLabel"]))

        story.append(PageBreak())

    doc.build(story)
    print(f"PDF saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    build_pdf()
