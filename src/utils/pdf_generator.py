from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.units import inch
from pathlib import Path


ASSETS_DIR = Path(__file__).resolve().parents[1] / "ui" / "assets"


def _get_existing_logo_path():
    for name in ("logo.png", "lof_logo.png", "rfu_logo.png"):
        candidate = ASSETS_DIR / name
        if candidate.exists():
            return str(candidate)
    return None


def get_empty_string_for_none(value):
    if value:
        return value
    return " "

# Helper function to add section with heading and content
def add_section(heading, content, elements, styles):
    h_style = ParagraphStyle(
        'Heading4',
        parent=styles['Heading4'],
        spaceAfter=12
    )
    sh_style = ParagraphStyle(
        'Heading5',
        parent=styles['Heading5'],
        spaceAfter=12
    )
    elements.append(Paragraph(heading, h_style))
    for key in content:
        elements.append(Paragraph(key, sh_style))
        elements.append(Paragraph(content[key], styles["Normal"]))
        # elements.append(Spacer(1, 12))

def generate_student_grade_pdf(student_grade_json, name):
    styles = getSampleStyleSheet()
    title_style = styles['Heading2']
    # Style the table
    score_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('WORDWRAP', (0, 0), (-1, -1)),
    ])

    # Create the PDF document
    doc = SimpleDocTemplate(name, pagesize=letter)
    elements = []

    logo_path = _get_existing_logo_path()
    if logo_path:
        logo = Image(logo_path)
        logo.drawHeight = .75 * inch
        logo.drawWidth = 2.5 * inch
        elements.append(logo)

    elements.append(
        Paragraph("CareScore AI", ParagraphStyle(name='Title', parent=styles['Heading1'], alignment=1)))

    elements.append(
        Paragraph("CareScore Evaluation Results", ParagraphStyle(name='Title', parent=styles['Heading4'], alignment=1)))

    score_data = [
        [Paragraph('Total CareScore', styles['Heading5']), Paragraph('Achieved CareScore', styles['Heading5'])],
        [Paragraph(str(student_grade_json['total_possible_score']), styles['Normal']),
         Paragraph(str(student_grade_json['achieved_score']), styles['Normal'])],
    ]
    score_col_widths = [1.2 * inch, 1.2 * inch]
    score_table = Table(score_data, colWidths=score_col_widths, repeatRows=1, hAlign='LEFT')
    score_table.setStyle(score_style)
    elements.append(Paragraph("Score", title_style))
    elements.append(score_table)

    elements.append(Spacer(width=1 * inch, height=0.1 * inch))

    summary_data = [
        [Paragraph('Summary', styles['Heading5'])],
        [Paragraph(str(student_grade_json['evaluation_summary']), styles['Normal'])],
    ]
    summary_col_widths = [5 * inch]
    summary_table = Table(summary_data, colWidths=summary_col_widths, repeatRows=1, hAlign='LEFT')
    summary_table.setStyle(score_style)
    elements.append(Paragraph("Evaluation Summary", title_style))
    elements.append(summary_table)

    # Add summary information
    # elements.append(Paragraph(f"Total Possible Score: {data['total_possible_score']}", styles['Normal']))
    # elements.append(Paragraph(f"Student Score: {data['achieved_score']}", styles['Normal']))
    # elements.append(Paragraph(f"Evaluation Summary: {data['evaluation_summary']}", styles['Normal']))

    # Add title
    elements.append(Paragraph("Evaluation Details", title_style))

    # Process each criteria section
    for criteria in student_grade_json['criteria']:
        # Section heading
        heading = f"Achieved Assessment Level: {criteria['Assessment']}"

        # Build content string
        content = {}
        content['Possible Score Range: ' +str(criteria['Possible CareScore'])] = ''
        content['Achieved CareScore: '+str(criteria['Achieved CareScore'])] = ''
        content['Objective:'] = criteria['Objective']
        content['Documented'] = criteria['Documented']
        content['Non-Documented'] = criteria['Non-Documented']
        content['Improvement'] = criteria['Improvement']

        # content.append(f"Possible Score Range: {criteria['Possible CareScore']}")
        #
        # if criteria['Achieved CareScore'] > 0:
        #     content.append(f"Achieved Score: {criteria['Achieved CareScore']}")

        # content.append(f"\nObjective:\n{criteria['Objective']}")
        #
        # if criteria['Documented']:
        #     content.append(f"\nDocumented Items:\n{criteria['Documented']}")
        #
        # if criteria['Non-Documented']:
        #     content.append(f"\nNon-Documented Items:\n{criteria['Non-Documented']}")
        #
        # if criteria['Improvement']:
        #     content.append(f"\nAreas for Improvement:\n{criteria['Improvement']}")

        if criteria['Achieved CareScore'] > 0:
            # Add section to document
            add_section(heading, content, elements, styles)

    elements.append(Spacer(width=1 * inch, height=0.1 * inch))

    summary_data = [
        [Paragraph('Reasoning', styles['Heading5'])],
        [Paragraph(str(student_grade_json['detailed_llm_reasoning']), styles['Normal'])],
    ]
    summary_col_widths = [5 * inch]
    summary_table = Table(summary_data, colWidths=summary_col_widths, repeatRows=1, hAlign='LEFT')
    summary_table.setStyle(score_style)
    elements.append(Paragraph("Evaluation Reasoning", title_style))
    elements.append(summary_table)

    # # Prepare data for the table
    # table_data = [
    #     [Paragraph('Assessment', styles['Heading5']),
    #      Paragraph('Objective', styles['Heading5']),
    #      # Paragraph('Max \nCareScore', styles['Heading5']),
    #      Paragraph('Care\nScore', styles['Heading5']),
    #      Paragraph('Documented', styles['Heading5']),
    #      Paragraph('Non-Documented', styles['Heading5']),
    #      Paragraph('Improvement', styles['Heading5'])]
    # ]
    # for criterion in student_grade_json['criteria']:
    #     table_data.append([
    #         Paragraph(get_empty_string_for_none(criterion['Assessment']), styles['Normal']),
    #         Paragraph(get_empty_string_for_none(criterion['Objective']), styles['Normal']),
    #         # str(criterion['Possible CareScore']),
    #         Paragraph(get_empty_string_for_none(str(criterion['Achieved CareScore'])), styles['Normal']),
    #         Paragraph(get_empty_string_for_none(criterion['Documented']), styles['Normal']),
    #         Paragraph(get_empty_string_for_none(criterion['Non-Documented']), styles['Normal']),
    #         Paragraph(get_empty_string_for_none(criterion['Improvement']), styles['Normal'])
    #     ])
    #
    # col_widths = [1.0 * inch, 1.2 * inch, 0.6 * inch, 1.7 * inch, 1.7 * inch, 1.7 * inch]
    # table = Table(table_data, colWidths=col_widths, repeatRows=1)
    #
    # style = TableStyle([
    #     ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    #     ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    #     ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    #     ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    #     ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    #     ('FONTSIZE', (0, 0), (-1, 0), 14),
    #     ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
    #     ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    #     ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
    #     ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
    #     ('FONTSIZE', (0, 1), (-1, -1), 12),
    #     ('TOPPADDING', (0, 1), (-1, -1), 4),
    #     ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
    #     ('GRID', (0, 0), (-1, -1), 1, colors.black),
    #     ('WORDWRAP', (0, 0), (-1, -1)),
    # ])
    # table.setStyle(style)
    #
    # # Add the table to the elements
    # elements.append(table)

    # Add a page break
    elements.append(PageBreak())

    # Build the PDF
    doc.build(elements)


def create_soap_note_pdf(soap_note_content, patient_name="Unknown Patient"):
    """
    Create a PDF from SOAP note content
    
    Args:
        soap_note_content: String or dict containing SOAP note content
        patient_name: Name of the patient for the header
        
    Returns:
        bytes: PDF content as bytes
    """
    from io import BytesIO
    
    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Add logo if available
    try:
        logo_path = _get_existing_logo_path()
        if logo_path:
            logo = Image(logo_path)
            logo.drawHeight = .75 * inch
            logo.drawWidth = 2.5 * inch
            elements.append(logo)
    except:
        pass  # Logo not found, continue without it
    
    # Title
    elements.append(
        Paragraph("CareScore AI - SOAP Note", 
                 ParagraphStyle(name='Title', parent=styles['Heading1'], alignment=1))
    )
    
    # Patient name
    elements.append(
        Paragraph(f"Patient: {patient_name}", 
                 ParagraphStyle(name='Patient', parent=styles['Heading3'], alignment=1))
    )
    
    elements.append(Spacer(1, 20))
    
    # Process SOAP content
    if isinstance(soap_note_content, dict):
        # If it's a dictionary, process each section
        for section, content in soap_note_content.items():
            elements.append(Paragraph(section.upper(), styles['Heading2']))
            elements.append(Paragraph(str(content), styles['Normal']))
            elements.append(Spacer(1, 12))
    else:
        # If it's a string, try to parse sections or display as-is
        soap_text = str(soap_note_content)
        
        # Try to identify SOAP sections
        sections = {}
        current_section = None
        current_content = []
        
        for line in soap_text.split('\n'):
            line = line.strip()
            if line.upper().startswith(('SUBJECTIVE:', 'OBJECTIVE:', 'ASSESSMENT:', 'PLAN:')):
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                # Start new section
                current_section = line.split(':')[0].upper()
                current_content = [line[len(current_section)+1:].strip()] if ':' in line else []
            elif current_section and line:
                current_content.append(line)
        
        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content)
        
        # Add sections to PDF
        if sections:
            for section, content in sections.items():
                elements.append(Paragraph(section, styles['Heading2']))
                elements.append(Paragraph(content, styles['Normal']))
                elements.append(Spacer(1, 12))
        else:
            # No sections found, add as single block
            elements.append(Paragraph("SOAP Note", styles['Heading2']))
            elements.append(Paragraph(soap_text, styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


def create_checklist_pdf(checklist_json):
    from io import BytesIO

    checklist_json = checklist_json or []
    yes_count = sum(1 for item in checklist_json if str(item.get('Evaluated', '')).strip().lower() == 'yes')
    partial_count = sum(1 for item in checklist_json if str(item.get('Evaluated', '')).strip().lower() == 'partial')
    no_count = max(len(checklist_json) - yes_count - partial_count, 0)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    logo_path = _get_existing_logo_path()
    if logo_path:
        logo = Image(logo_path)
        logo.drawHeight = .75 * inch
        logo.drawWidth = 2.5 * inch
        elements.append(logo)

    elements.append(Paragraph("CareScore AI", ParagraphStyle(name='Title', parent=styles['Heading1'], alignment=1)))
    elements.append(Paragraph("Checklist Evaluation", ParagraphStyle(name='Subtitle', parent=styles['Heading4'], alignment=1)))
    elements.append(Spacer(1, 12))

    summary_table = Table([
        ["Yes", "Partial", "No", "Total"],
        [str(yes_count), str(partial_count), str(no_count), str(len(checklist_json))],
    ], colWidths=[1.2 * inch] * 4, hAlign='LEFT')
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 12))

    table_data = [[
        Paragraph("Question", styles['Heading5']),
        Paragraph("Expected", styles['Heading5']),
        Paragraph("Status", styles['Heading5']),
        Paragraph("Evidence", styles['Heading5']),
    ]]

    for item in checklist_json:
        table_data.append([
            Paragraph(str(item.get("Question", "")), styles['Normal']),
            Paragraph(str(item.get("ExpectedAnswer", "")), styles['Normal']),
            Paragraph(str(item.get("Evaluated", "")), styles['Normal']),
            Paragraph(str(item.get("Evidence", "")), styles['Normal']),
        ])

    checklist_table = Table(
        table_data,
        colWidths=[2.1 * inch, 2.1 * inch, 0.8 * inch, 2.0 * inch],
        repeatRows=1,
        hAlign='LEFT',
    )
    checklist_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(checklist_table)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def create_student_grade_pdf(student_grade_json):
    from io import BytesIO

    student_grade_json = student_grade_json or {}
    criteria = student_grade_json.get("criteria") or []
    if isinstance(criteria, dict):
        criteria = [criteria]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    logo_path = _get_existing_logo_path()
    if logo_path:
        logo = Image(logo_path)
        logo.drawHeight = .75 * inch
        logo.drawWidth = 2.5 * inch
        elements.append(logo)

    elements.append(Paragraph("CareScore AI", ParagraphStyle(name='Title', parent=styles['Heading1'], alignment=1)))
    elements.append(Paragraph("SOAP Note Grading", ParagraphStyle(name='Subtitle', parent=styles['Heading4'], alignment=1)))
    elements.append(Spacer(1, 12))

    score_table = Table([
        ["Assessment", "Achieved Score", "Total Possible"],
        [
            str(student_grade_json.get("assessment", "")),
            str(student_grade_json.get("achieved_score", "")),
            str(student_grade_json.get("total_possible_score", "")),
        ],
    ], colWidths=[2.2 * inch, 1.4 * inch, 1.6 * inch], hAlign='LEFT')
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Evaluation Summary", styles['Heading3']))
    elements.append(Paragraph(str(student_grade_json.get("evaluation_summary", "")), styles['Normal']))
    elements.append(Spacer(1, 12))

    if student_grade_json.get("detailed_llm_reasoning"):
        elements.append(Paragraph("Detailed Reasoning", styles['Heading3']))
        elements.append(Paragraph(str(student_grade_json.get("detailed_llm_reasoning", "")), styles['Normal']))
        elements.append(Spacer(1, 12))

    detail_rows = [[
        Paragraph("Assessment", styles['Heading5']),
        Paragraph("Objective", styles['Heading5']),
        Paragraph("Score", styles['Heading5']),
        Paragraph("Documented", styles['Heading5']),
        Paragraph("Missing", styles['Heading5']),
        Paragraph("Improvement", styles['Heading5']),
    ]]

    for item in criteria:
        detail_rows.append([
            Paragraph(str(item.get("Assessment", "")), styles['Normal']),
            Paragraph(str(item.get("Objective", "")), styles['Normal']),
            Paragraph(str(item.get("Achieved CareScore", "")), styles['Normal']),
            Paragraph(str(item.get("Documented", "")), styles['Normal']),
            Paragraph(str(item.get("Non-Documented", "")), styles['Normal']),
            Paragraph(str(item.get("Improvement", "")), styles['Normal']),
        ])

    if len(detail_rows) > 1:
        detail_table = Table(
            detail_rows,
            colWidths=[1.0 * inch, 1.6 * inch, 0.7 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch],
            repeatRows=1,
            hAlign='LEFT',
        )
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(detail_table)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
