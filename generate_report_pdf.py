"""Generate a readable PDF report from results.json with explicit verdicts."""
import json
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable, KeepTogether,
)
from reportlab.lib import colors

INPUT_FILE = "results.json"
OUTPUT_FILE = "results_report.pdf"

# ── Hardcoded verdicts based on criteria analysis ──────────────────────
VERDICTS = {
    1: {
        "verdict": "PASS",
        "color": "#2e7d32",
        "notes": (
            "All 6 criteria met. Subject line references Argentina and oncology supply. "
            "Body mentions cisplatin/carboplatin and currency devaluation without inventing data. "
            "Service described accurately without overpromising. Formal tone. "
            "Clear 30-min call CTA. Review flag correctly set to false."
        ),
    },
    2: {
        "verdict": "PASS",
        "color": "#2e7d32",
        "notes": (
            "All 5 criteria met. References doxorubicin/epirubicin and budget/waste problem. "
            "Correctly positions hospital-level simulation (not country-level). "
            "Collegial but professional tone. CTA matches input (free data review). "
            "Review flag correctly set to false."
        ),
    },
    3: {
        "verdict": "PASS",
        "color": "#2e7d32",
        "notes": (
            "All 5 criteria met. Acknowledges humanitarian severity without sensationalism. "
            "Explicitly states 'design and advisory, not system implementation.' "
            "Warm, mission-aligned tone. No fabricated statistics. "
            "Review flag correctly set to false."
        ),
    },
    4: {
        "verdict": "PASS",
        "color": "#2e7d32",
        "notes": (
            "All 5 criteria met. Produced usable draft despite vague input. "
            "Defaulted to professional tone. Listed two real JCNB services rather than hallucinating. "
            "Used placeholders ([Contact Name]) instead of inventing details. "
            "Review flag correctly set to true with clear reason."
        ),
    },
    5: {
        "verdict": "PARTIAL FAIL",
        "color": "#e65100",
        "notes": (
            "4 of 5 criteria met. Two services summarized distinctly (risk assessment vs. traceability). "
            "Formal institutional tone. Spanish closing ('Esperamos tener la oportunidad de colaborar') "
            "is correct. HOWEVER: needs_human_review should be true for a multi-service pitch to an "
            "international body, but the model returned false. Prompt v2 should enforce stricter "
            "review-flag logic for multi-stakeholder or institutional targets."
        ),
    },
    6: {
        "verdict": "PASS",
        "color": "#2e7d32",
        "notes": (
            "All 6 criteria met. No fabricated statistics. No politically charged statements. "
            "Diplomatic framing ('complexities and challenges') without assigning blame. "
            "No overpromising — uses 'could potentially support.' "
            "Does not overstate JCNB track record. "
            "Review flag correctly set to true with appropriate reason citing political sensitivity."
        ),
    },
    7: {
        "verdict": "PASS",
        "color": "#2e7d32",
        "notes": (
            "All 4 criteria met. Explicitly states 'our expertise does not extend to direct pricing "
            "negotiation with manufacturers or government lobbying for tax exemptions.' "
            "Redirects to risk assessment service. Does not promise out-of-scope work. "
            "Review flag correctly set to true with clear scope-mismatch reason."
        ),
    },
}


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
        "SectionHead", parent=styles["Heading2"],
        textColor=HexColor("#1a3c5e"), spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "FieldLabel", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10,
        textColor=HexColor("#333333"), spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        "FieldValue", parent=styles["Normal"],
        fontSize=10, leftIndent=12, spaceAfter=8, leading=14,
    ))
    styles.add(ParagraphStyle(
        "EmailBody", parent=styles["Normal"],
        fontSize=9.5, leftIndent=12, rightIndent=12,
        spaceAfter=8, leading=13,
        backColor=HexColor("#f5f5f5"), borderPadding=8,
    ))
    styles.add(ParagraphStyle(
        "CriteriaItem", parent=styles["Normal"],
        fontSize=9.5, leftIndent=24, spaceAfter=3, leading=12,
    ))
    styles.add(ParagraphStyle(
        "VerdictPass", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=11,
        textColor=HexColor("#2e7d32"), spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "VerdictFail", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=11,
        textColor=HexColor("#c62828"), spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "VerdictPartial", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=11,
        textColor=HexColor("#e65100"), spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "TableCell", parent=styles["Normal"],
        fontSize=8.5, leading=11,
    ))

    story = []

    # ── Title page ─────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("JCNB Eval Run v1", styles["Title"]))
    story.append(Paragraph("Gemini 2.5 Flash", styles["Heading2"]))
    story.append(Spacer(1, 24))
    story.append(Paragraph(f"Model: {data['model']}", styles["Normal"]))
    story.append(Paragraph(f"Timestamp: {data['timestamp']}", styles["Normal"]))
    story.append(Paragraph(f"Prompt version: {data['prompt_version']}", styles["Normal"]))
    story.append(Paragraph(f"Total cases: {len(data['results'])}", styles["Normal"]))

    # Count verdicts
    passes = sum(1 for v in VERDICTS.values() if v["verdict"] == "PASS")
    fails = sum(1 for v in VERDICTS.values() if "FAIL" in v["verdict"])
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        f'<font color="#2e7d32"><b>{passes} PASS</b></font>'
        f' &nbsp; <font color="#e65100"><b>{fails} PARTIAL FAIL</b></font>',
        styles["Heading3"],
    ))
    story.append(PageBreak())

    # ── Summary table ──────────────────────────────────────────────────
    story.append(Paragraph("Evaluation Summary", styles["Heading1"]))
    story.append(Spacer(1, 12))

    header = ["Case", "Type", "Label", "Review Flag", "Verdict", "Key Finding"]
    table_data = [header]

    for case in data["results"]:
        cid = case["id"]
        v = VERDICTS[cid]
        resp = case.get("llm_response", {})
        review_flag = resp.get("needs_human_review", "N/A")
        if "error" in resp:
            review_flag = "ERROR"

        # Shorten notes for table
        short_note = v["notes"][:90] + "..." if len(v["notes"]) > 90 else v["notes"]

        table_data.append([
            str(cid),
            case["type"].upper(),
            Paragraph(case["label"], styles["TableCell"]),
            str(review_flag),
            v["verdict"],
            Paragraph(short_note, styles["TableCell"]),
        ])

    col_widths = [0.4*inch, 0.75*inch, 1.4*inch, 0.7*inch, 0.8*inch, 2.85*inch]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a3c5e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (4, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#f9f9f9")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(PageBreak())

    # ── Individual case pages ──────────────────────────────────────────
    for case in data["results"]:
        cid = case["id"]
        resp = case.get("llm_response", {})
        has_error = "error" in resp
        v = VERDICTS[cid]

        # Case header
        type_color = {"normal": "#2e7d32", "edge": "#e65100", "failure-prone": "#c62828"}
        tc = type_color.get(case["type"], "#333333")
        story.append(Paragraph(
            f'Case {cid}: {case["label"]}',
            styles["SectionHead"],
        ))
        story.append(Paragraph(
            f'<font color="{tc}"><b>[{case["type"].upper()}]</b></font>',
            styles["Normal"],
        ))

        # Verdict badge
        verdict_style = "VerdictPass" if v["verdict"] == "PASS" else (
            "VerdictFail" if v["verdict"] == "FAIL" else "VerdictPartial"
        )
        story.append(Paragraph(f'Verdict: {v["verdict"]}', styles[verdict_style]))
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
            body_html = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            body_html = body_html.replace("\n", "<br/>")
            # Handle markdown bold pairs
            while "**" in body_html:
                body_html = body_html.replace("**", "<b>", 1)
                if "**" in body_html:
                    body_html = body_html.replace("**", "</b>", 1)
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

        # Criteria with pass/fail per item
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#dddddd")))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Criteria Evaluation", styles["FieldLabel"]))
        for i, c in enumerate(case.get("good_output_criteria", []), 1):
            c_safe = c.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(f"{i}. {c_safe}", styles["CriteriaItem"]))

        # Verdict and notes
        story.append(Spacer(1, 12))
        story.append(Paragraph(
            f'Verdict: <font color="{v["color"]}"><b>{v["verdict"]}</b></font>',
            styles["FieldLabel"],
        ))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"Notes: {v['notes']}", styles["FieldValue"]))

        story.append(PageBreak())

    doc.build(story)
    print(f"PDF saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    build_pdf()
