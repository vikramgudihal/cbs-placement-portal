import io
import re
import PyPDF2

SKILL_KEYWORDS = [
    # Programming Languages
    "Python", "Java", "C++", "C#", "C", "JavaScript", "TypeScript", "PHP", "Ruby", "Swift", "Kotlin", "Go", "Rust", "SQL",
    # Web & Frameworks
    "HTML", "CSS", "HTML5", "CSS3", "React", "React.js", "Angular", "Vue.js", "Node.js", "Express", "Django", "Flask", 
    "FastAPI", "Spring Boot", "ASP.NET", "Bootstrap", "Tailwind CSS", "jQuery", "REST API", "GraphQL",
    # Databases & Cloud
    "MySQL", "PostgreSQL", "MongoDB", "Oracle", "Redis", "SQLite", "AWS", "Azure", "Google Cloud", "GCP", 
    "Docker", "Kubernetes", "Linux", "Unix", "Git", "GitHub", "GitLab", "CI/CD",
    # Data & AI/ML
    "Machine Learning", "Deep Learning", "Data Analysis", "Data Analytics", "Data Science", "Pandas", "NumPy", 
    "Scikit-Learn", "TensorFlow", "PyTorch", "NLP", "Power BI", "Tableau", "Data Visualization", "Big Data",
    # Business, Finance & Management
    "Excel", "Advanced Excel", "Financial Modeling", "Business Analysis", "Project Management", "Agile", "Scrum", 
    "Digital Marketing", "SEO", "Accounting", "HR Management", "Corporate Communication", "Operations Management",
    # Core Engineering & CS Fundamentals
    "Data Structures", "Algorithms", "DBMS", "OOP", "Object Oriented Programming", "Operating Systems", 
    "Computer Networks", "Software Engineering", "Problem Solving", "System Design"
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
    text_lower = text.lower()

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

    # 3. Name Extraction (Check first 6 non-header lines)
    ignore_words = {'resume', 'curriculum', 'vitae', 'cv', 'profile', 'contact', 'email', 'phone', 'address', 'education', 'experience', 'skills', 'page', 'objective', 'summary'}
    candidate_name = None
    for line in lines[:6]:
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

    # 6. Overall CGPA / Aggregate Score Extraction (e.g. CGPA: 8.76, 7.77, 8.5/10, GPA 9.1)
    cgpa_match = re.search(r'(?:cgpa|gpa|aggregate|sgpa)[\s\:\-]+([0-9]\.[0-9]{1,2})', text, re.IGNORECASE)
    if not cgpa_match:
        cgpa_match = re.search(r'\b([0-9]\.[0-9]{1,2})\s*(?:/10|\s*cgpa|\s*gpa)', text, re.IGNORECASE)
    if cgpa_match:
        try:
            val = float(cgpa_match.group(1))
            if 0.0 <= val <= 10.0:
                data['cgpa'] = str(val)
                data['ug_score'] = str(val)
        except ValueError:
            pass

    # 7. Line-by-Line Structured Scanning for 10th & 12th Academics
    for line in lines:
        l_str = line.strip()
        if not l_str:
            continue
        l_low = l_str.lower()

        # ── 10TH / SSC / SECONDARY SCAN ────────────────────────
        if re.search(r'\b(?:10th|sslc|class\s*x|secondary|matriculation)\b', l_low):
            # Score
            pct = re.search(r'([3-9]\d(?:\.\d{1,2})?)\s*%', l_str)
            if pct:
                data['tenth_score'] = pct.group(1)
            else:
                score_match = re.search(r'(?:score|percentage|marks|cgpa|aggregate)[\s\:\-]+([0-9]{1,2}(?:\.[0-9]{1,2})?)', l_str, re.I)
                if score_match:
                    data['tenth_score'] = score_match.group(1)
                else:
                    two_digits = re.findall(r'\b([4-9]\d(?:\.\d{1,2})?)\b', l_str)
                    for td in two_digits:
                        if not re.match(r'^(?:19|20)\d\d$', td): # Not a year
                            data['tenth_score'] = td
                            break

            # Year
            yr = re.search(r'\b(201[0-9]|202[0-3])\b', l_str)
            if yr:
                data['tenth_year'] = yr.group(1)

            # Board
            if 'cbse' in l_low:
                data['tenth_board'] = 'CBSE'
            elif 'icse' in l_low:
                data['tenth_board'] = 'ICSE'
            elif any(b in l_low for b in ['kseeb', 'state board', 'karnataka state', 'ssc']):
                data['tenth_board'] = 'State Board'

        # ── 12TH / PUC / HSC / DIPLOMA SCAN ────────────────────
        elif re.search(r'\b(?:12th|puc|class\s*xii|hsc|diploma|higher secondary)\b', l_low):
            # Score
            pct = re.search(r'([3-9]\d(?:\.\d{1,2})?)\s*%', l_str)
            if pct:
                data['twelfth_score'] = pct.group(1)
            else:
                score_match = re.search(r'(?:score|percentage|marks|cgpa|aggregate)[\s\:\-]+([0-9]{1,2}(?:\.[0-9]{1,2})?)', l_str, re.I)
                if score_match:
                    data['twelfth_score'] = score_match.group(1)
                else:
                    two_digits = re.findall(r'\b([4-9]\d(?:\.\d{1,2})?)\b', l_str)
                    for td in two_digits:
                        if not re.match(r'^(?:19|20)\d\d$', td):
                            data['twelfth_score'] = td
                            break

            # Year
            yr = re.search(r'\b(201[5-9]|202[0-5])\b', l_str)
            if yr:
                data['twelfth_year'] = yr.group(1)

            # Board
            if any(b in l_low for b in ['pue', 'pu board', 'state pu', 'karnataka pu']):
                data['twelfth_board'] = 'State PU Board'
            elif 'cbse' in l_low:
                data['twelfth_board'] = 'CBSE'
            elif 'dte' in l_low or 'diploma' in l_low:
                data['twelfth_board'] = 'DTE'

            # Stream
            if any(s in l_low for s in ['pcm', 'pcmb', 'pcmc', 'science']):
                data['twelfth_stream'] = 'Science (PCMB/PCMC)'
            elif any(s in l_low for s in ['commerce', 'bacs', 'ceba']):
                data['twelfth_stream'] = 'Commerce'
            elif 'diploma' in l_low:
                data['twelfth_stream'] = 'Diploma in CS/Engineering'

    # Fallbacks for 10th and 12th boards if not yet set
    if not data.get('tenth_board'):
        if 'cbse' in text_lower:
            data['tenth_board'] = 'CBSE'
        elif 'icse' in text_lower:
            data['tenth_board'] = 'ICSE'
        else:
            data['tenth_board'] = 'State Board'

    if not data.get('twelfth_board'):
        if 'cbse' in text_lower:
            data['twelfth_board'] = 'CBSE'
        elif 'dte' in text_lower:
            data['twelfth_board'] = 'DTE'
        else:
            data['twelfth_board'] = 'State PU Board'

    if not data.get('twelfth_stream'):
        if any(k in text_lower for k in ['commerce', 'b.com', 'bcom', 'bba']):
            data['twelfth_stream'] = 'Commerce'
        else:
            data['twelfth_stream'] = 'Science (PCMB/PCMC)'

    # 8. Undergraduate (UG) Degree & Details
    if 'bca' in text_lower:
        data['ug_degree'] = 'BCA'
        data['ug_branch'] = 'Computer Applications'
    elif 'b.sc' in text_lower or 'bsc' in text_lower:
        data['ug_degree'] = 'B.Sc'
        data['ug_branch'] = 'Computer Science'
    elif 'b.tech' in text_lower or 'btech' in text_lower or 'b.e.' in text_lower:
        data['ug_degree'] = 'B.Tech / B.E.'
        data['ug_branch'] = 'Computer Science & Engineering'
    elif 'b.com' in text_lower or 'bcom' in text_lower:
        data['ug_degree'] = 'B.Com'
        data['ug_branch'] = 'Commerce & Finance'
    elif 'bba' in text_lower:
        data['ug_degree'] = 'BBA'
        data['ug_branch'] = 'Business Administration'
    else:
        data['ug_degree'] = 'BCA'
        data['ug_branch'] = 'Computer Science'

    # UG Year
    ug_year_match = re.search(r'(?:bca|bsc|b\.sc|b\.tech|btech|b\.e\.|bcom|bba|graduation|undergraduate)[\s\w\:\-\,\.]{0,35}\b(202[1-6])\b', text, re.IGNORECASE)
    if ug_year_match:
        data['ug_year'] = ug_year_match.group(1)
    else:
        data['ug_year'] = '2024'

    # UG University
    if re.search(r'\b(kud|karnatak university)\b', text_lower):
        data['ug_university'] = 'Karnatak University, Dharwad'
    elif re.search(r'\b(vtu|visvesvaraya)\b', text_lower):
        data['ug_university'] = 'VTU, Belagavi'
    elif re.search(r'\b(bangalore university|bu)\b', text_lower):
        data['ug_university'] = 'Bangalore University'

    # 9. Postgraduate (PG) Details for MCA / MBA Batch
    if degree in ['MCA', 'MBA'] or branch in ['MCA', 'MBA']:
        data['pg_college'] = 'Chetan Business School'
        data['pg_university'] = 'Karnatak University, Dharwad'
        data['pg_degree'] = degree or 'MCA'
        data['pg_branch'] = branch or 'MCA'
        data['pg_year'] = '2026'
        if 'cgpa' in data:
            data['pg_score'] = data['cgpa']

    # 10. Skills Extraction
    found_skills = []
    for skill in SKILL_KEYWORDS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            found_skills.append(skill)
    unique_skills = []
    for s in found_skills:
        if s not in unique_skills:
            unique_skills.append(s)
    if unique_skills:
        data['skills'] = ", ".join(unique_skills)

    # 11. Projects Snippet
    project_match = re.search(r'(?:projects?|academic projects?|key projects?)[\s\:\-]+([^\n\r]+(?:\n[^\n\r]+){1,3})', text, re.IGNORECASE)
    if project_match:
        clean_proj = project_match.group(1).strip()
        if len(clean_proj) > 10:
            data['projects'] = clean_proj[:250]

    # 12. Links (GitHub & LinkedIn)
    github_match = re.search(r'https?://(?:www\.)?github\.com/[A-Za-z0-9_-]+', text, re.IGNORECASE)
    if github_match:
        data['github_url'] = github_match.group(0)

    linkedin_match = re.search(r'https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+', text, re.IGNORECASE)
    if linkedin_match:
        data['linkedin_url'] = linkedin_match.group(0)

    # 13. Location / City Detection
    cities = ["Hubli", "Dharwad", "Bangalore", "Bengaluru", "Belagavi", "Belgaum", "Hyderabad", "Pune", "Mumbai", "Mysore", "Mangalore", "Goa"]
    for city in cities:
        if re.search(r'\b' + city + r'\b', text, re.IGNORECASE):
            data['preferred_location'] = city
            data['city'] = city
            break

    return {
        "success": True,
        "data": data,
        "extracted_count": len(data),
        "found_skills_count": len(unique_skills)
    }
