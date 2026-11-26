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

_SCHOOL_MARKERS = [
    'school', 'vidyalaya', 'vidya', 'convent', 'academy', 'public school',
    'high school', 'english medium', 'kendriya', 'navodaya', 'pu college',
    'pre-university', 'pre university', 'composite', 'polytechnic',
    'college', 'institute', 'mahavidyalaya'
]

_EDUCATION_STOP_WORDS = {
    '10th', 'sslc', 's.s.l.c', 'class x', 'class 10', '12th', 'puc', 'p.u.c',
    'class xii', 'class 12', 'hsc', 'diploma', 'bca', 'bsc', 'b.sc', 'b.tech',
    'btech', 'b.e', 'bcom', 'b.com', 'bba', 'mca', 'mba', 'm.tech',
    'undergraduate', 'postgraduate', 'graduation', 'experience', 'projects',
    'skills', 'technical skills', 'certifications', 'achievements'
}


def extract_text_from_pdf(pdf_stream):
    """Safely extracts all text from a PDF file stream using PyPDF2."""
    try:
        if hasattr(pdf_stream, 'seek'):
            pdf_stream.seek(0)
        reader = PyPDF2.PdfReader(pdf_stream)
        text_parts = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)
        return "\n".join(text_parts)
    except Exception:
        return ""


def _extract_institution(window_lines):
    """Extract plausible school/college name from lines near an education entry."""
    for raw_line in window_lines:
        clean = re.sub(r'\([^)]*\)', '', raw_line).strip()
        segments = re.split(r'\s*[\|\-\–\—\•]\s*|,\s*', clean)
        for seg in segments:
            seg_clean = seg.strip()
            seg_low = seg_clean.lower()
            if len(seg_clean) < 4 or len(seg_clean) > 90:
                continue
            if any(marker in seg_low for marker in _SCHOOL_MARKERS):
                # Strip trailing score/year noise
                seg_clean = re.sub(r'\b(20\d\d|cgpa|score|percentage|marks)\b.*$', '', seg_clean, flags=re.I).strip(' :-,')
                if len(seg_clean) >= 4 and seg_low not in _EDUCATION_STOP_WORDS:
                    return seg_clean
    return None


def _build_section_window(lines, start_idx, stop_pattern, max_lookahead=3):
    """Gather up to max_lookahead lines for an education block without crossing into the next degree."""
    window = [lines[start_idx]]
    for offset in range(1, max_lookahead):
        if start_idx + offset >= len(lines):
            break
        nxt = lines[start_idx + offset].strip()
        if not nxt:
            continue
        if re.search(stop_pattern, nxt.lower()):
            break
        window.append(nxt)
    return window


def parse_resume(pdf_stream):
    """
    Parses resume text to extract candidate information for auto-filling profile forms.
    Returns a dict with extracted fields.
    """
    text = extract_text_from_pdf(pdf_stream)
    if not text or len(text.strip()) < 10:
        return {
            "success": False,
            "error": "Could not extract readable text from this PDF. If it is a scanned image PDF, it has been attached — please fill the fields manually below."
        }

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text_lower = text.lower()

    data = {}

    # 1. Email Extraction
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b', text)
    if email_match:
        data['email'] = email_match.group(0).lower()
        data['personal_email'] = email_match.group(0).lower()

    # 2. Phone Extraction (supports +91, 0, spaces/dashes within 10 digits)
    phone_match = re.search(r'(?:(?:\+91|91|0)[\s\-]?)?([6-9]\d{4}[\s\-]?\d{5})\b', text)
    if phone_match:
        data['phone'] = re.sub(r'\D', '', phone_match.group(1))[-10:]

    # 3. Name Extraction (Check first 8 non-header lines)
    ignore_words = {
        'resume', 'curriculum', 'vitae', 'cv', 'profile', 'contact', 'email',
        'phone', 'mobile', 'address', 'education', 'experience', 'skills',
        'page', 'objective', 'summary', 'github', 'linkedin', 'portfolio',
        'hubli', 'dharwad', 'bangalore', 'bengaluru', 'karnataka', 'india'
    }
    candidate_name = None
    for line in lines[:8]:
        if '@' in line or 'http' in line.lower() or re.search(r'\d{5,}', line):
            continue
        clean_line = re.sub(r'[^A-Za-z\s.]', ' ', line).strip()
        words = [w for w in clean_line.split() if len(w.strip('.')) >= 1]
        alpha_words = [w.strip('.') for w in words]
        if 1 <= len(alpha_words) <= 5:
            if not any(w.lower() in ignore_words for w in alpha_words):
                if len(alpha_words) >= 2 or (len(alpha_words[0]) >= 3 and '|' not in line):
                    candidate_name = " ".join(alpha_words).title()
                    break
    if candidate_name:
        data['name'] = candidate_name

    # 4. University Roll / USN (Matches P02DR25S126001, 22BCSE101, 1MS21MC001, etc.)
    usn_match = re.search(
        r'\b(P\d{2}[A-Z0-9]{8,14}|[1-4][A-Z]{2}\d{2}[A-Z]{2,3}\d{3,4}|\d{2}[A-Z]{3,4}\d{3,4})\b',
        text,
        re.IGNORECASE
    )
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

    # 6. Overall CGPA / Aggregate Score Extraction
    cgpa_match = re.search(r'(?:cgpa|gpa|aggregate|sgpa)[\s\:\-]+([0-9](?:\.[0-9]{1,2})?)', text, re.IGNORECASE)
    if not cgpa_match:
        cgpa_match = re.search(r'\b([0-9]\.[0-9]{1,2})\s*(?:/10|\s*cgpa|\s*gpa)', text, re.IGNORECASE)
    if cgpa_match:
        try:
            val = float(cgpa_match.group(1))
            if 0.0 < val <= 10.0:
                data['cgpa'] = str(val)
                data['ug_score'] = str(val)
        except ValueError:
            pass

    # 7. Multi-line Sliding Window Scanning for 10th, 12th, and UG Academics
    tenth_re = r'\b(?:10th|xth|10\s*th|sslc|s\.s\.l\.c|class\s*x|class\s*10|x\s*std|secondary(?:\s+school)?|matriculation)\b'
    twelfth_re = r'\b(?:12th|xiith|12\s*th|puc|p\.u\.c|class\s*xii|class\s*12|xii\s*std|hsc|higher\s+secondary|senior\s+secondary|diploma|intermediate)\b|\+2\b'
    ug_re = r'\b(?:bca|b\.sc|bsc|b\.tech|btech|b\.e\.|b\.com|bcom|bba|bachelor|undergraduate|graduation)\b'
    pg_re = r'\b(?:mca|mba|m\.tech|master|postgraduate|post\s+graduate)\b'

    for idx, line in enumerate(lines):
        l_str = line.strip()
        if not l_str:
            continue
        l_low = l_str.lower()

        # ── 10TH / SSC / SECONDARY SCAN ────────────────────────
        if re.search(tenth_re, l_low):
            win_lines = _build_section_window(lines, idx, f"(?:{twelfth_re}|{ug_re}|{pg_re})")
            win_str = " | ".join(win_lines)
            win_low = win_str.lower()

            if not data.get('tenth_score'):
                pct = re.search(r'([3-9]\d(?:\.\d{1,2})?|100(?:\.0{1,2})?)\s*%', win_str)
                if pct:
                    data['tenth_score'] = pct.group(1)
                else:
                    score_match = re.search(r'(?:score|percentage|marks|cgpa|aggregate)[\s\:\-]+([0-9]{1,2}(?:\.[0-9]{1,2})?)', win_str, re.I)
                    if score_match:
                        data['tenth_score'] = score_match.group(1)
                    else:
                        two_digits = re.findall(r'\b([4-9]\d(?:\.\d{1,2})?)\b', win_str)
                        for td in two_digits:
                            if not re.match(r'^(?:19|20)\d\d$', td):
                                data['tenth_score'] = td
                                break

            if not data.get('tenth_year'):
                yr = re.search(r'\b(200\d|201\d|202[0-4])\b', win_str)
                if yr:
                    data['tenth_year'] = yr.group(1)

            if not data.get('tenth_board'):
                if 'cbse' in win_low:
                    data['tenth_board'] = 'CBSE'
                elif 'icse' in win_low:
                    data['tenth_board'] = 'ICSE'
                elif any(b in win_low for b in ['kseeb', 'state board', 'karnataka state', 'ssc', 'sslc board']):
                    data['tenth_board'] = 'State Board'

            if not data.get('tenth_school'):
                sch = _extract_institution(win_lines)
                if sch:
                    data['tenth_school'] = sch

        # ── 12TH / PUC / HSC / DIPLOMA SCAN ────────────────────
        elif re.search(twelfth_re, l_low):
            win_lines = _build_section_window(lines, idx, f"(?:{tenth_re}|{ug_re}|{pg_re})")
            win_str = " | ".join(win_lines)
            win_low = win_str.lower()

            if not data.get('twelfth_score'):
                pct = re.search(r'([3-9]\d(?:\.\d{1,2})?|100(?:\.0{1,2})?)\s*%', win_str)
                if pct:
                    data['twelfth_score'] = pct.group(1)
                else:
                    score_match = re.search(r'(?:score|percentage|marks|cgpa|aggregate)[\s\:\-]+([0-9]{1,2}(?:\.[0-9]{1,2})?)', win_str, re.I)
                    if score_match:
                        data['twelfth_score'] = score_match.group(1)
                    else:
                        two_digits = re.findall(r'\b([4-9]\d(?:\.\d{1,2})?)\b', win_str)
                        for td in two_digits:
                            if not re.match(r'^(?:19|20)\d\d$', td):
                                data['twelfth_score'] = td
                                break

            if not data.get('twelfth_year'):
                yr = re.search(r'\b(201[2-9]|202[0-5])\b', win_str)
                if yr:
                    data['twelfth_year'] = yr.group(1)

            if not data.get('twelfth_board'):
                if any(b in win_low for b in ['pue', 'pu board', 'state pu', 'karnataka pu']):
                    data['twelfth_board'] = 'State PU Board'
                elif 'cbse' in win_low:
                    data['twelfth_board'] = 'CBSE'
                elif 'isc' in win_low:
                    data['twelfth_board'] = 'ISC'
                elif 'dte' in win_low or 'diploma' in win_low:
                    data['twelfth_board'] = 'DTE'

            if not data.get('twelfth_stream'):
                if any(s in win_low for s in ['pcm', 'pcmb', 'pcmc', 'science']):
                    data['twelfth_stream'] = 'Science (PCMB/PCMC)'
                elif any(s in win_low for s in ['commerce', 'bacs', 'ceba']):
                    data['twelfth_stream'] = 'Commerce'
                elif 'diploma' in win_low:
                    data['twelfth_stream'] = 'Diploma in CS/Engineering'

            if not data.get('twelfth_school'):
                col = _extract_institution(win_lines)
                if col:
                    data['twelfth_school'] = col

        # ── UNDERGRADUATE (UG) BLOCK SCAN ──────────────────────
        elif re.search(ug_re, l_low):
            win_lines = _build_section_window(lines, idx, f"(?:{tenth_re}|{twelfth_re}|{pg_re})")
            win_str = " | ".join(win_lines)

            if not data.get('ug_college'):
                col = _extract_institution(win_lines)
                if col:
                    data['ug_college'] = col

            ug_cgpa = re.search(r'(?:cgpa|gpa|aggregate|sgpa)[\s\:\-]+([0-9](?:\.[0-9]{1,2})?)', win_str, re.I)
            if not ug_cgpa:
                ug_cgpa = re.search(r'([4-9]\d(?:\.\d{1,2})?)\s*%', win_str)
            if ug_cgpa:
                data['ug_score'] = ug_cgpa.group(1)

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
    ug_year_match = re.search(r'(?:bca|bsc|b\.sc|b\.tech|btech|b\.e\.|bcom|bba|graduation|undergraduate)[\s\w\:\-\,\.]{0,35}\b(202[0-6]|201[89])\b', text, re.IGNORECASE)
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

    # 10. Skills Extraction (supports C++, C#, Node.js, CI/CD, etc.)
    found_skills = []
    for skill in SKILL_KEYWORDS:
        if skill == 'C':
            pattern = r'(?<![A-Za-z0-9_])C(?![A-Za-z0-9_+#])'
        else:
            pattern = r'(?<![A-Za-z0-9_])' + re.escape(skill) + r'(?![A-Za-z0-9_])'
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
