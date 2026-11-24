import io
import re
import PyPDF2

SKILL_KEYWORDS = [
    # Programming Languages
    "Python", "Java", "C++", "C#", "C", "JavaScript", "TypeScript", "PHP", "Ruby", "Swift", "Kotlin", "Go", "Rust", "SQL",
    # Web & Frameworks
    "HTML", "CSS", "React", "Angular", "Vue.js", "Node.js", "Express", "Django", "Flask", "FastAPI", "Spring Boot", "ASP.NET", "Bootstrap", "Tailwind CSS",
    # Databases & Cloud
    "MySQL", "PostgreSQL", "MongoDB", "Oracle", "Redis", "SQLite", "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "Linux", "Git", "GitHub",
    # Data & AI/ML
    "Machine Learning", "Deep Learning", "Data Analysis", "Data Science", "Pandas", "NumPy", "Scikit-Learn", "TensorFlow", "PyTorch", "NLP", "Power BI", "Tableau",
    # Business & Management
    "Excel", "Advanced Excel", "Financial Modeling", "Business Analysis", "Project Management", "Agile", "Scrum", "Marketing", "SEO", "Accounting", "HR Management",
    # Core Engineering & CS
    "Data Structures", "Algorithms", "DBMS", "OOP", "Operating Systems", "Computer Networks", "REST API", "Microservices", "Problem Solving"
]

def extract_text_from_pdf(pdf_stream):
    """Safely extracts all text from a PDF file stream using PyPDF2."""
    try:
        reader = PyPDF2.PdfReader(pdf_stream)
        text_parts = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)
        return "\n".join(text_parts)
    except Exception as e:
        return ""

def parse_resume(pdf_stream):
    """
    Parses resume text to extract candidate information for auto-filling profile forms.
    Returns a dict with extracted fields.
    """
    text = extract_text_from_pdf(pdf_stream)
    if not text or len(text.strip()) < 10:
        return {"success": False, "error": "Could not extract readable text from this PDF."}

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    data = {}

    # 1. Email Extraction
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', text)
    if email_match:
        data['email'] = email_match.group(0).lower()
        data['personal_email'] = email_match.group(0).lower()

    # 2. Phone Extraction (Indian 10-digit formats with optional +91 or 0 prefix)
    phone_match = re.search(r'(?:(?:\+91|91|0)[\s\-]?)?([6-9]\d{9})\b', text)
    if phone_match:
        data['phone'] = phone_match.group(1)

    # 3. Name Extraction (Check first 5 non-header lines)
    ignore_words = {'resume', 'curriculum', 'vitae', 'cv', 'profile', 'contact', 'email', 'phone', 'address', 'education', 'experience', 'skills', 'page'}
    candidate_name = None
    for line in lines[:5]:
        clean_line = re.sub(r'[^A-Za-z\s]', '', line).strip()
        words = clean_line.split()
        if 1 <= len(words) <= 4:
            if not any(w.lower() in ignore_words for w in words):
                candidate_name = clean_line.title()
                break
    if candidate_name:
        data['name'] = candidate_name

    # 4. University Roll / USN (Matches P02DR25S126001, 22BCSE101, 1MS21MC001, etc.)
    usn_match = re.search(r'\b(P\d{2}[A-Z0-9]{8,14}|[1-4][A-Z]{2}\d{2}[A-Z]{2,3}\d{3,4}|\d{2}[A-Z]{3,4}\d{3,4})\b', text, re.IGNORECASE)
    if usn_match:
        data['student_id'] = usn_match.group(1).upper()

    # 5. Degree & Branch Extraction
    branch = None
    degree = None
    text_lower = text.lower()

    if 'mca' in text_lower or 'master of computer application' in text_lower:
        degree = 'MCA'
        branch = 'MCA'
    elif 'mba' in text_lower or 'master of business administration' in text_lower:
        degree = 'MBA'
        branch = 'MBA'
    elif 'bca' in text_lower or 'bachelor of computer application' in text_lower:
        degree = 'BCA'
        branch = 'BCA'
    elif 'b.tech' in text_lower or 'btech' in text_lower or 'b.e.' in text_lower or 'bachelor of engineering' in text_lower:
        degree = 'B.Tech / B.E.'
        if 'computer science' in text_lower or 'cse' in text_lower:
            branch = 'Computer Science & Engineering'
        elif 'information science' in text_lower or 'ise' in text_lower or 'it' in text_lower:
            branch = 'Information Science & Engineering'
        elif 'electronics' in text_lower or 'ece' in text_lower:
            branch = 'Electronics & Communication'
        else:
            branch = 'Engineering'
    elif 'b.com' in text_lower or 'bcom' in text_lower:
        degree = 'B.Com'
        branch = 'Commerce'
    elif 'b.sc' in text_lower or 'bsc' in text_lower:
        degree = 'B.Sc'
        branch = 'Computer Science / Science'
    
    if branch:
        data['branch'] = branch
    if degree:
        data['degree'] = degree

    # 6. CGPA Extraction (e.g. CGPA: 8.76, 8.5/10, GPA 9.1)
    cgpa_match = re.search(r'(?:cgpa|gpa|aggregate)[\s\:\-]+([0-9]\.[0-9]{1,2})', text, re.IGNORECASE)
    if not cgpa_match:
        cgpa_match = re.search(r'\b([0-9]\.[0-9]{1,2})\s*(?:/10|\s*cgpa)', text, re.IGNORECASE)
    if cgpa_match:
        try:
            val = float(cgpa_match.group(1))
            if 0.0 <= val <= 10.0:
                data['cgpa'] = str(val)
        except ValueError:
            pass

    # 7. 10th & 12th Percentage Extraction
    tenth_match = re.search(r'(?:10th|ssc|secondary|matriculation)[\s\w\:\-]*?(\d{2}(?:\.\d{1,2})?)\s*%', text, re.IGNORECASE)
    if tenth_match:
        data['tenth_score'] = tenth_match.group(1)

    twelfth_match = re.search(r'(?:12th|puc|hsc|higher secondary|senior secondary)[\s\w\:\-]*?(\d{2}(?:\.\d{1,2})?)\s*%', text, re.IGNORECASE)
    if twelfth_match:
        data['twelfth_score'] = twelfth_match.group(1)

    # 8. Skills Extraction
    found_skills = []
    for skill in SKILL_KEYWORDS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            found_skills.append(skill)
    if found_skills:
        data['skills'] = ", ".join(found_skills)

    # 9. Links (GitHub & LinkedIn)
    github_match = re.search(r'https?://(?:www\.)?github\.com/[A-Za-z0-9_-]+', text, re.IGNORECASE)
    if github_match:
        data['github_url'] = github_match.group(0)

    linkedin_match = re.search(r'https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+', text, re.IGNORECASE)
    if linkedin_match:
        data['linkedin_url'] = linkedin_match.group(0)

    return {
        "success": True,
        "data": data,
        "extracted_count": len(data),
        "found_skills_count": len(found_skills)
    }
