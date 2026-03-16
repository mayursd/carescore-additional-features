SOAP_ASSESSMENT_PLAN_SUGGESTION_PROMPT = """
                            You are a senior clinician. Based on the following transcript and current Assessment/Plan, provide any additional suggestions.

                            Suggest:
                            - Additional diagnoses (if any)
                            - Investigations
                            - Medications
                            - Patient education
                            - Follow-up plans
                            - Referrals

                            Do not remove existing items. Return in JSON like this:
                            {{
                                "Final_diagnosis": "Your suggestion or ''",
                                "Investigations": "Your suggestion or ''",
                                "Medications": "Your suggestion or ''",
                                "Education": "Your suggestion or ''",
                                "Follow_Up": "Your suggestion or ''",
                                "Referrals": "Your suggestion or ''",
                                "Other": "Your suggestion or ''"
                            }}

                            Transcript:
                            {transcript}

                            Case File:
                            {case_file_content}

                            Current Assessment/Plan:
                            {current_ap_data}
                            """

SOAP_PROMPT = """
    You are a clinician tasked with creating a SOAP note from a patient interview transcript and updating existing template text. 
    Use the transcript and current template texts to generate a structured JSON object containing updated data for the following 9 SOAP note fields. 
    Each field should have subfields as specified below, with data appended to existing content from the current template texts (if provided) or set to "Not mentioned" if no new information is available. 
    Preserve the structure and only provide the data (no headings or subheadings in the values unless explicitly part of the subfield structure). 
    Return the result as a JSON object with a single key "soap_data" containing the structured data.

    Fields and Subfields:
    1. "HPI": Single string covering onset, location, duration, character, aggravating/alleviating, radiation, timing, severity
    2. "PMHx": Single string covering childhood/adult illnesses, immunizations, hospitalizations, surgical history
    3. "FHx": Single string covering parents, siblings, children, dx and ages
    4. "SHx": Object with subfields:
       - "Tobacco": type, number of pack years
       - "ETOH": type, amount, frequency
       - "Drugs": type, amount, frequency
       - "Diet": description
       - "Exercise": description
       - "Sexual_activity": description
       - "Occupation": description
       - "Living_situation": description
       - "Safety": description
    5. "Medications": Single string covering dose, frequency, route, etc., including OTC
    6. "Allergies": Single string specifying type of reaction
    7. "Review_of_Systems": Object with subfields:
       - "General": description
       - "Eyes": description
       - "ENT": description
       - "Cardiovascular": description
       - "Respiratory": description
       - "Gastrointestinal": description
       - "Genitourinary": description
       - "Musculoskeletal": description
       - "Neurological": description
       - "Psychiatric": description
       - "Integument": description
       - "Endocrine": description
       - "Hematopoietic_Lymphatic": description
       - "Allergy_Immunology": description
     8. "Objective": Object containing both Vitals and Physical Exam findings. Return Vitals in a structured sub-object and Physical Exam findings under subfields:
       - "Vitals": Object with keys: "BP", "HR", "RR", "SPO2", "Temp", "Pain" (use empty string if not present)
       - "General_Appearance": description
       - "HEENT": description
       - "Neck": description
       - "Cardiovascular": description
       - "Pulmonary": description
       - "GI_Abdomen": description
       - "GU": description
       - "Musculoskeletal": description
       - "Neurological": description
       - "Psychiatric": description
       - "Integument": description
    9. "Assessment_Plan": Object with subfields:
       - "Final_diagnosis": description
       - "Investigations": labs, imaging, etc.
       - "Medications": specific medication, dose, route, frequency
       - "Consults": description
       - "Disposition": Admit, d/c, observe, follow up with, when?
       - "Pt_Education": description
       - "Other": description

    Transcript: \n{transcript}
    {current_text_str}

    IMPORTANT: Ensure the returned JSON under the top-level key "soap_data" includes an "Objective" object that contains a "Vitals" object (with keys BP, HR, RR, SPO2, Temp, Pain) and the Physical Exam subfields above. If a value is not present in the transcript, set it to an empty string or "Not mentioned" as appropriate. ONLY return the JSON object (no additional commentary).
    """
EVALUATION_CRITERIA = """ 
{
  "criteria": [
   {
      "assessment": "Excellent",
      "objective": "Ensure thorough evaluation and diagnostic focus by emphasizing key diagnoses such as CHF, including all critical diagnostic tests (CXR, 12-lead EKG, CBC, Chem panel, TSH, BNP, Echo).",
      "possible_score": "90 - 100",
      "achieved_score": 0,
      "documented": "",
      "non_documented": "",
      "improvement": "",
      "achieved_score_reason":""
    },
    {
      "assessment": "Good",
      "objective": "Capture all relevant findings in SOAP notes, identifying potential diagnoses like CHF and incorporating a broad range of diagnostic tests, even if not exhaustive.",
      "possible_score": "80 - 90",
      "achieved_score": 0,
      "documented": "",
      "non_documented": "",
      "improvement": "",
      "achieved_score_reason":""
    },
    {
      "assessment": "Satisfactory",
      "objective": "Accurately document abnormal findings such as dyspnea on exertion, edema, rales, S3, and LVH on EKG.",
      "possible_score": "75-80",
      "achieved_score": 0,
      "documented": "",
      "non_documented": "",
      "improvement": "",
      "achieved_score_reason":""
    },
    {
      "assessment": "Needs Improvement",
      "objective": "Recognize and document potential cardiac issues, even if not specific to CHF.",
      "possible_score": "< 75",
      "achieved_score": 0,
      "documented": "",
      "non_documented": "",
      "improvement": "",
      "achieved_score_reason":""
    }
  ]
}
"""

# PROMPT = """
# Grade the CareProvider against the case file and the encounter notes by the CareProvider.
# Use the criteria provided in the Evaluation Criteria JSON.
# For each criteria update achieved_score, documented, non_documented and improvement fields.
# Also update the final achieved_score and evaluation_summary.
# Provide the output JSON in the same format as Evaluation Criteria JSON.
# Be consistent on the score with a reason so that repeated runs give the same score.
# """

PROMPT = """
Grade the CareProvider against the case file and the encounter notes by the CareProvider. 
Use the criteria provided in the Evaluation Criteria JSON. 
Grade the student into one assessment group based on the highest score achieved. Update achieved_score. 
Indicate with full details on what is documented, non_documented and improvement required. 
Also update the final achieved_score and evaluation_summary.
Provide the output JSON in the same format as Evaluation Criteria JSON.
Be consistent on the score with a reason so that repeated runs give the same score.
Verify the achieved score and category by filling in detailed_llm_reasoning.
"""

SAMPLE_LLM_RESPONSE = """
{"criteria": [{"objective": "Collect a reliable focused history from a patient.", "possible_score": 5, "achieved_score": 4, "documented": "Collected detailed history including timeline and symptoms (cough with yellowish phlegm, fever, fatigue, lack of sleep, sinus pain, and plugged ears). Covered personal medical history, family history, allergies, and medication use.", "non_documented": "Missed inquiring about possible occupational hazards or exposures related to his cough.", "improvement": "Include questions regarding potential environmental or occupational factors that may contribute to the patient’s symptoms, especially considering his job as a cashier where exposure to elements may be relevant."}, {"objective": "Demonstrate a reliable focused physical exam on a patient.", "possible_score": 5, "achieved_score": 3, "documented": "Performed focused physical exam of throat, nose, lungs, heart, and lymph nodes.", "non_documented": "Omitted potentially relevant examinations such as an abdominal exam (to rule out other sources of symptoms like generalized infection) and ear exam (given the patient's complaint of plugged ears).", "improvement": "Ensure a more comprehensive physical exam, covering any additional regions like ears and abdomen that could provide clues to the diagnosis."}, {"objective": "Formulate differential diagnoses for the patient’s presenting problem.", "possible_score": 5, "achieved_score": 4, "documented": "Identified potential differential diagnoses: Upper respiratory infection (URI), pneumonia, influenza, sinusitis, bronchitis.", "non_documented": "Did not provide a ranked differential or discuss the likelihood of each diagnosis.", "improvement": "Provide a ranked list of differentials and briefly discuss the reasoning behind the ranking, considering the likelihood and severity of each condition."}, {"objective": "Construct appropriate diagnostic and therapeutic strategies for the patient’s presenting problem.", "possible_score": 5, "achieved_score": 3, "documented": "Documented initial therapeutic interventions like Robitussin and ibuprofen.", "non_documented": "Did not outline follow-up steps or specify when to seek further medical attention. Missing a comprehensive diagnostic plan like potential tests (e.g., chest X-ray, CBC).", "improvement": "Detail a clear diagnostic strategy including potential imaging and lab tests, and provide specific follow-up or red flag conditions that would necessitate more urgent care."}, {"objective": "Document history and physical exam findings in an organized, accurate note.", "possible_score": 5, "achieved_score": 4, "documented": "History and physical exam findings were well-organized and accurately documented.", "non_documented": "Some sections could have been more comprehensive (e.g., more detail in the physical exam findings and relevant negative findings).", "improvement": "Ensure thorough and comprehensive documentation, including relevant negative findings (e.g., absence of wheezing or rales in the lung exam)."}, {"objective": "Document differential diagnoses and diagnostic and therapeutic strategies.", "possible_score": 5, "achieved_score": 3, "documented": "Differential diagnosis and initial therapeutic strategies were documented.", "non_documented": "Detailed diagnostic plan and follow-up strategies were not well articulated.", "improvement": "Include a detailed diagnostic plan and specify the criteria for follow-up or further diagnostic steps."}, {"objective": "Demonstrate effective communication with a patient regarding possible diagnoses and diagnostic and therapeutic strategies and respond to performance feedback.", "possible_score": 5, "achieved_score": 4, "documented": "Communicated the possible diagnoses and initial therapeutic strategies.", "non_documented": "There was no documentation on how feedback was incorporated or how the patient’s understanding was checked.", "improvement": "Document patient education on the diagnosis and treatment plan and verify the patient’s understanding. Incorporate specific feedback points into future encounters if provided."}, {"objective": "Demonstrate respect, dignity, compassion, and integrity during interactions with patients.", "possible_score": 5, "achieved_score": 5, "documented": "Demonstrated respect and compassion while taking the patient’s history and conducting the physical exam.", "non_documented": "None", "improvement": "Continue to show high levels of respect and empathy in patient interactions."}], "achieved_score": 30, "evaluation_summary": "The student performed well overall with a clear and organized history and physical exam documentation. Key areas for improvement include expanding on the diagnostic and follow-up plans, ensuring comprehensive physical examinations, ranking differential diagnoses with rationales, and enhancing patient education and feedback incorporation. Continued demonstration of respect and empathy during patient interactions was noted and commendable.", "total_possible_score": 40}
"""

SAMPLE_LLM_RESPONSE_NEW = """
{"criteria": {"assessment": "Good", 
"objective": "Capture all relevant findings in SOAP notes, identifying potential diagnoses like CHF and incorporating a broad range of diagnostic tests, even if not exhaustive.", 
"possible_score": "90 - 100", "achieved_score": 88, 
"documented": "The SOAP note captured fatigue, SOB, pedal edema, HTN, and documented essential investigations and management plans.", 
"non_documented": "The note lacks documentation on certain detailed history elements and specific plans for ruling out all differential diagnoses like asthma through PFTs.", 
"improvement": "Integrate a more comprehensive plan that mentions breathing tests for asthma to rule out alternate diagnoses."}, "achieved_score": 88, 
"evaluation_summary": "The encounter documentation was thorough in suspected diagnosis of heart failure and necessary investigations were ordered. The student addressed the chief complaints well; however, detailed mention of all possible differential diagnostic tests, explicit abnormal findings, and a broader cardiac assessment were areas for improvement. Refining documentation to include a complete impact and risks, as well as covering all potential diagnoses, will strengthen future assessments.", 
"total_possible_score": 100}
"""

AUDIO_TRANSCRIPT_PROMPT = """
Generate the complete transcript for the given audio file with conversation between the clinician and patient. Follow the Transcript Output Sample given below:

Transcript Output Sample:  "
[00:00 - 00:05] Clinician: Hi  
[00:05 - 00:10] Patient: Hello  
[00:20 - 00:59] Clinician: How are you doing today  
[01:00 - 01:20] Patient: Not good. Having headache.. "


The transcript should:  
1. Include time stamps for the beginning and end of each speaker's dialogue.  
2. Clearly identify the speaker (Clinician or Patient).  
3. Capture the exact words spoken, ensuring clarity and accuracy.  
4. Use a clean and professional format without adding extra annotations or interpretations.
5. IMPORTANT: Replace any student names or doctor names mentioned in the conversation with [REDACTED] to protect privacy. This includes names used in greetings, introductions, or any other context.
6. If you detect no speech or the audio is otherwise empty/unintelligible, respond exactly with "[No transcript available - audio was empty or unintelligible]" and do not invent dialogue or speakers.

Please analyze the audio file and provide the complete transcript adhering to the format.

"""

# VIDEO_TRANSCRIPT_PROMPT = """
# Generate the complete transcript for the given video file with conversation between the clinician and patient. Follow the Transcript Output Sample given below:
# Transcript Output Sample: "
# Clinician: Hi
# Patient: Hello
# Clinician: How are you doing today
# Patient: Not good. Having headache.."
# """

VIDEO_TRANSCRIPT_PROMPT = """
I have a video file containing a conversation between a clinician and a patient. I need a transcript of the dialogue with precise time stamps, following the format provided below:

Transcript Output Sample:  "
[00:00 - 00:05] Clinician: Hi  
[00:05 - 00:10] Patient: Hello  
[00:20 - 00:59] Clinician: How are you doing today  
[01:00 - 01:20] Patient: Not good. Having headache.. "


The transcript should:  
1. Include time stamps for the beginning and end of each speaker's dialogue.  
2. Clearly identify the speaker (Clinician or Patient).  
3. Capture the exact words spoken, ensuring clarity and accuracy.  
4. Use a clean and professional format without adding extra annotations or interpretations.
5. IMPORTANT: Replace any student names or doctor names mentioned in the conversation with [REDACTED] to protect privacy. This includes names used in greetings, introductions, or any other context.
6. If you detect no speech or the video contains no intelligible audio, respond exactly with "[No transcript available - audio was empty or unintelligible]" and do not invent dialogue or speakers.

Please analyze the video file and provide the complete transcript adhering to the format.

---

This prompt ensures the model understands the output format, the key requirements, and the need for accuracy.
"""

TRANSCRIPT_NOTE_PROMPT = """
From the given patient interview generate a patient note capturing History of Present Illness
Patient Medical History
Family Medical History
Allergies
Medications with associated problem
Review of Systems
Physical Exam
Social History
"""

CHECKLIST_SAMPLE_JSON = """
{
  "questions_and_answers": [
    {
      "Question": "Introduces self and confirms patient identity",
      "ExpectedAnswer": "The clinician introduces themselves and confirms patient identity using two identifiers.",
      "Evaluated": "No",
      "Evidence": ""
    },
    {
      "Question": "Asks about chief complaint",
      "ExpectedAnswer": "The clinician asks why the patient is seeking care today.",
      "Evaluated": "No",
      "Evidence": ""
    }
  ]
}
"""

CHECKLIST_RETRIEVAL_PROMPT = """
Extract the complete grading checklist from the uploaded case file.

Rules:
- Return every checklist item or observable objective you can identify.
- Preserve the original intent of each item, but rewrite for clarity when needed.
- If the file contains grouped categories, flatten them into one list.
- If a rubric item includes expected behavior, include that in `ExpectedAnswer`.
- Return ONLY valid JSON matching the sample structure.
"""

CHECKLIST_EVALUATION_PROMPT = """
Evaluate each checklist item against the clinician-patient interview transcript.

Rules:
- For each checklist item, set `Evaluated` to one of: "Yes", "No", or "Partial".
- Add concise transcript-backed support in `Evidence`.
- Do not invent evidence that is not present in the transcript.
- Preserve the original `Question` and `ExpectedAnswer`.
- Return ONLY valid JSON with a top-level `questions_and_answers` array.
"""

TRANSCRIPT_CHECKLIST_PROMPT = """
Create a concise clinical encounter checklist directly from the clinician-patient interview transcript.

Rules:
- Build a practical checklist from what should have happened in the encounter.
- Each checklist item must include:
  - `Question`
  - `ExpectedAnswer`
  - `Evaluated` with one of: "Yes", "No", or "Partial"
  - `Evidence`
- Use transcript evidence only.
- Do not require any uploaded case file or SOAP note.
- Prefer 8 to 15 meaningful checklist items.
- Cover core encounter behaviors such as introduction, history gathering, symptoms, medications, allergies, assessment, plan, education, and follow-up when supported by the transcript.
- Return ONLY valid JSON with a top-level `questions_and_answers` array.
"""

CARE_OBJECTIVES_SAMPLE_JSON = """
[
  {
    "PossibleScore": "91-100",
    "Assessment": "Excellent",
    "Objective": ""
  },
  {
    "PossibleScore": "81-90",
    "Assessment": "Good",
    "Objective": ""
  },
  {
    "PossibleScore": "71-80",
    "Assessment": "Satisfactory",
    "Objective": ""
  },
  {
    "PossibleScore": "<70",
    "Assessment": "Poor",
    "Objective": ""
  }
]
"""

CARE_OBJECTIVES_PROMPT = """
From the given grade file, considering the indicators and faculty comments, capture all the Objectives for the given category into CARE_OBJECTIVES_JSON. Generate the JSON output according to the CARE_OBJECTIVES_JSON structure.
"""

SOAP_SUGGESTION_PROMPT = """
Based on the provided SOAP note data, generate concise, actionable suggestions for improvement across all sections (HPI, PMHx, FHx, SHx, Medications, Allergies, Review of Systems, Objective, Assessment_Plan). Focus on enhancing completeness, clarity, and clinical relevance. Provide suggestions in a structured JSON format, with each key representing a SOAP note section and its value being a list of suggested improvements for that section. If a section is comprehensive, state "No suggestions for improvement."

Example Output:
{
  "HPI": [
    "Elaborate on the character of the pain (e.g., sharp, dull, throbbing).",
    "Specify the exact duration of symptoms (e.g., 'for 3 days' instead of 'recently')."
  ],
  "PMHx": [
    "Include dates of diagnoses for chronic conditions."
  ],
  "SHx": [
    "Quantify alcohol consumption (e.g., '2 drinks/day' instead of 'moderate')."
  ],
  "Assessment_Plan": [
    "Add a differential diagnosis for the patient's chief complaint.",
    "Specify the dosage and frequency for new medications."
  ]
}
"""
