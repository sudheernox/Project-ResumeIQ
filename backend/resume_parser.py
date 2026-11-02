"""
Resume Parser — extracts text from PDF and DOCX files
"""
import os
import re


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using pdfplumber (primary) or PyMuPDF (fallback)."""
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        if text.strip():
            return text
    except Exception:
        pass

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        if text.strip():
            return text
    except Exception:
        pass

    raise ValueError("Could not extract text from PDF. File may be scanned or corrupted.")


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(file_path)
        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text)
        # Also extract from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        paragraphs.append(cell.text)
        return "\n".join(paragraphs)
    except Exception as e:
        raise ValueError(f"Could not extract text from DOCX: {str(e)}")


def parse_resume(file_path: str) -> dict:
    """
    Main entry point for resume parsing.
    Returns structured data extracted from the resume.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        raw_text = extract_text_from_pdf(file_path)
    elif ext == '.docx':
        raw_text = extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    if not raw_text or len(raw_text.strip()) < 50:
        raise ValueError("Resume appears to be empty or too short to analyze.")

    # Parse sections
    sections = extract_sections(raw_text)
    contact = extract_contact_info(raw_text)
    name = extract_name(raw_text)

    return {
        'raw_text': raw_text,
        'name': name,
        'contact': contact,
        'sections': sections,
        'word_count': len(raw_text.split()),
        'char_count': len(raw_text),
    }


def extract_name(text: str) -> str:
    """Attempt to extract the candidate's name from the top of the resume."""
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    for line in lines[:8]:
        cleaned = re.sub(r'[|•\-\*–▪].*', '', line).strip()
        words = cleaned.split()
        if 2 <= len(words) <= 4 and all(re.match(r'^[A-Za-z\.]+$', w) for w in words):
            if not any(kw in cleaned.lower() for kw in ['resume', 'cv', 'curriculum', 'objective', 'summary', 'email', 'phone', 'profile', 'engineer', 'developer', 'experience']):
                return cleaned
    return "Candidate"


def extract_contact_info(text: str) -> dict:
    """Extract email, phone, LinkedIn, GitHub from resume text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    phone_pattern = r'(\+?\d{1,3}[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}'
    linkedin_pattern = r'linkedin\.com/in/[\w\-]+'
    github_pattern = r'github\.com/[\w\-]+'

    return {
        'email': re.findall(email_pattern, text),
        'phone': re.findall(phone_pattern, text),
        'linkedin': re.findall(linkedin_pattern, text, re.IGNORECASE),
        'github': re.findall(github_pattern, text, re.IGNORECASE),
    }


def extract_sections(text: str) -> dict:
    """Extract resume sections using heading detection."""
    section_patterns = {
        'objective': r'(objective|summary|profile|about me|career objective)',
        'education': r'(education|academic|qualification|degree)',
        'experience': r'(experience|work experience|employment|professional experience|internship)',
        'skills': r'(skills|technical skills|core competencies|technologies|expertise)',
        'projects': r'(projects|personal projects|academic projects|portfolio)',
        'certifications': r'(certifications?|certificates?|courses?|training)',
        'achievements': r'(achievements?|awards?|honors?|accomplishments?)',
        'languages': r'(languages?)',
        'hobbies': r'(hobbies|interests|activities)',
        'references': r'(references?)',
    }

    lines = text.split('\n')
    sections = {}
    current_section = 'header'
    current_content = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        matched_section = None
        for section_name, pattern in section_patterns.items():
            if re.match(r'^\s*' + pattern + r'\s*:?\s*$', stripped, re.IGNORECASE):
                matched_section = section_name
                break

        if matched_section:
            if current_content:
                sections[current_section] = '\n'.join(current_content)
            current_section = matched_section
            current_content = []
        else:
            current_content.append(stripped)

    if current_content:
        sections[current_section] = '\n'.join(current_content)

    return sections
