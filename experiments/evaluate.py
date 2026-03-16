import os
import json
import google.generativeai as genai
import time
import re
from PyPDF2 import PdfReader
from reportlab.lib import colors
import fitz
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from carescore_ai_constants import VIDEO_TRANSCRIPT_PROMPT, CHECKLIST_RETRIEVAL_PROMPT, CHECKLIST_EVALUATION_PROMPT, CHECKLIST_SAMPLE_JSON

# Configuration Constants
# NOTE: This experiment script is Gemini-only. Configure via env vars.
GEMINI_API_KEY = os.environ.get("GEMINI_AI_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
VIDEO_FOLDER = "D:\LOF\careScoreAI\Recordings\Carson Audio Recordings-20250216T035627Z-001\Carson Audio Recordings"
CHECKLIST_PDFS_FOLDER= "D:\LOF\careScoreAI\checklist results\Carson"
CASE_FILES_FOLDER = "D:\LOF\careScoreAI\casefiles\Carson_HTN_rev342024_PA1 CSE_AY2023-24 (3).pdf"

def remove_student_name(transcript: str, filename: str) -> str:
    """Remove the student name from the transcript using filename."""
    name_match = re.search(r' - ([A-Za-z]+)\.mp4', filename)
    if name_match:
        student_name = name_match.group(1)
        transcript = re.sub(rf'\b{student_name}\b', '[REDACTED]', transcript, flags=re.IGNORECASE)
    return transcript

def process_video(file_path: str) -> str:
    """Process a single video file using Gemini with proper state checking"""
    if not GEMINI_API_KEY:
        raise ValueError("Missing GEMINI_AI_KEY")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    filename = os.path.basename(file_path)

    try:
        # Upload the video file
        uploaded_file = genai.upload_file(file_path, mime_type="video/mp4")
        print(f"Uploaded file '{uploaded_file.display_name}' as: {uploaded_file.uri}")

        # Wait until it becomes ACTIVE
        while uploaded_file.state.name == "PROCESSING":
            print("Processing video...")
            time.sleep(5)
            uploaded_file = genai.get_file(uploaded_file.name)

        if uploaded_file.state.name != "ACTIVE":
            print("File processing failed or timed out.")
            return None

        # Generate transcript
        response = model.generate_content(
            [VIDEO_TRANSCRIPT_PROMPT, uploaded_file],
            generation_config={"temperature": 0.2}
        )

        # Delete the file after processing
        genai.delete_file(uploaded_file.name)

        transcript = response.text.strip()

        # Save transcript to file
        with open("transcript.txt", "w") as f:
            f.write(transcript)

        return transcript

    except Exception as e:
        print(f"Error processing video {file_path}: {str(e)}")
        if 'uploaded_file' in locals():
            genai.delete_file(uploaded_file.name)
        return None


def extract_checklist(transcript, case_file_path):
    """Retrieve checklist based on the generated transcript and case file."""
    if not GEMINI_API_KEY:
        raise ValueError("Missing GEMINI_AI_KEY")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    
    pdf_document = fitz.open(case_file_path)
    case_file_content = ""
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        case_file_content += page.get_text("text")
    
    try:
        prompt = "\n\n".join([
            "You are a clinician in a medical hospital. Extract the complete checklist from the case file.",
            CHECKLIST_RETRIEVAL_PROMPT,
            "Grading File:\n" + case_file_content,
            "CHECKLIST_SAMPLE_JSON:\n" + CHECKLIST_SAMPLE_JSON,
            "Return ONLY valid JSON (no markdown, no code fences).",
        ])
        response = model.generate_content(prompt, generation_config={"temperature": 0.3, "response_mime_type": "application/json"})
        checklist_content = (response.text or "").strip()
        checklist_content = checklist_content.strip("```json").strip("```")
        checklist = json.loads(checklist_content)
        # if not isinstance(checklist, list):
        #     raise ValueError("Checklist is not a valid list format.")
        
        return checklist
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error parsing checklist response: {str(e)}")
        print(f"Checklist Response: {checklist_content}")
        return []

def evaluate_checklist(transcript, checklist):
   

    """Evaluate a checklist against a transcript."""
    if not GEMINI_API_KEY:
        raise ValueError("Missing GEMINI_AI_KEY")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = "\n\n".join([
        "You are a clinician in a medical hospital. Evaluate the checklist against the transcript.",
        CHECKLIST_EVALUATION_PROMPT,
        "CheckList Evaluation:\n" + str(checklist),
        "Clinician-Patient Interview:\n" + transcript,
        "Return ONLY valid JSON (no markdown, no code fences).",
    ])
    response = model.generate_content(prompt, generation_config={"temperature": 0.3, "response_mime_type": "application/json"})
    out_text = (response.text or "").strip().strip("```json").strip("```")
    evaluated = json.loads(out_text)
    return evaluated["questions_and_answers"]

### Step 4: Generate PDF from Evaluated Checklist
def generate_checklist_pdf(checklist_json, name):
    yes_count = sum(1 for item in checklist_json if item.get('Evaluated', '').lower() == 'yes')
    no_count = len(checklist_json) - yes_count

    styles = getSampleStyleSheet()
    title_style = styles['Heading2']

    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
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

    logo = Image("logo.png")
    logo.drawHeight = .75 * inch
    logo.drawWidth = 2.5 * inch
    elements.append(logo)

    elements.append(
        Paragraph("CareScore AI", ParagraphStyle(name='Title', parent=styles['Heading1'], alignment=1)))

    elements.append(
        Paragraph("CareScore Evaluation Results", ParagraphStyle(name='Title', parent=styles['Heading4'], alignment=1)))

    # Add title
    elements.append(Paragraph("Evaluation Summary", title_style))
    score_data = [
        [Paragraph('Evaluated', styles['Heading5']), Paragraph('Not Evaluated', styles['Heading5'])],
        [Paragraph(str(yes_count), styles['Normal']),
         Paragraph(str(no_count), styles['Normal'])],
    ]
    score_col_widths = [1.2 * inch, 1.2 * inch]
    score_table = Table(score_data, colWidths=score_col_widths, repeatRows=1, hAlign='LEFT')
    score_table.setStyle(style)
    elements.append(score_table)

    elements.append(Paragraph("Evaluation Details", title_style))
    # # Prepare data for the table
    table_data = [
        [Paragraph('#', styles['Heading4']),
         Paragraph('Title', styles['Heading4']),
         Paragraph('Question', styles['Heading4']),
         Paragraph('Answer', styles['Heading4']),
         Paragraph('Evaluated', styles['Heading4']),
         Paragraph('Reasoning', styles['Heading4'])]
    ]

    for index, criterion in enumerate(checklist_json, start=1):
        table_data.append([
            Paragraph(str(index), styles['Normal']),
            Paragraph(criterion.get('Title', ''), styles['Normal']),
            Paragraph(criterion.get('Question', ''), styles['Normal']),
            Paragraph(criterion.get('Answer', ''), styles['Normal']),
            Paragraph(criterion.get('Evaluated', ''), styles['Normal']),
            Paragraph(criterion.get('Reasoning', ''), styles['Normal'])
        ])

    col_widths = [.5*inch,  1 * inch, 1 * inch, 1.7 * inch, 0.9 * inch, 2.2 * inch]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    table.setStyle(style)

    # Add the table to the elements
    elements.append(table)

    # Build the PDF
    doc.build(elements)

    print(f"Generated PDF for {name} successfully!")


### Helper: Extract JSON from AI Response
def parse_json_response(response_text):
    """Extracts valid JSON from Markdown-style AI responses."""
    try:
        # Remove Markdown-style JSON blocks
        match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
        json_content = match.group(1) if match else response_text

        return json.loads(json_content)
    except json.JSONDecodeError:
        print("Error parsing JSON response.")
        return None


### Main Execution
def main():
    for video_file in os.listdir(VIDEO_FOLDER):
        global i
        if i < 11 :
            i += 1
            continue
        # if video_file != "Beacher - Johnson.mp4":
        #     continue

         

        if video_file.endswith(".mp4"):
            # start from 5th file for testing

            print(f"\nProcessing: {video_file}")

            # Extract student name from filename
            student_name = video_file.split(" - ")[0]

            # Step 1: Transcribe the video
            transcript = process_video(os.path.join(VIDEO_FOLDER, video_file))

            # For testing purposes, we will use a sample transcript from file

            # with open("transcript.txt", "r") as file:
            #     transcript = file.read()

            if not transcript:
                print(f"Skipping {video_file}: Failed to generate transcript.")
                continue

            # Step 2: Extract checklist
            attempts = 0
            checklist = extract_checklist(transcript, case_file_path=CASE_FILES_FOLDER)
            while len(checklist["questions_and_answers"]) != 32 and attempts < 3:
                l = len(checklist["questions_and_answers"])
                print(f"Attempt {attempts + 1}: Checklist length is {l}. Retrying...")
                checklist = extract_checklist(transcript, case_file_path=CASE_FILES_FOLDER)
                attempts += 1
            
            if len(checklist["questions_and_answers"]) != 32:
                print(f"Skipping {video_file}: Failed to generate checklist with 18 items after {attempts} attempts.")
                continue

            # Step 3: Evaluate checklist
            evaluated_checklist = evaluate_checklist(transcript, checklist)
            if not evaluated_checklist:
                print(f"Skipping {video_file}: Failed to evaluate checklist.")
                continue

            # Step 4: Generate PDF only with student name
            output_pdf_path = os.path.join(CHECKLIST_PDFS_FOLDER, student_name + ".pdf")
            generate_checklist_pdf(evaluated_checklist, output_pdf_path)

            print(f"Checklist saved: {output_pdf_path}")

    print("\nAll checklists processed successfully!")


if __name__ == "__main__":
    i = 0
    main()
