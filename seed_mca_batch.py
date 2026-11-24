"""
Seed 36 MCA Students, Official CBS Placement Staff, Recruitment Drives, and Dynamic Forms.
Strict Requirements:
- Super Admin ONLY: Arunkumar Rajput (arunkumarrajput@gmail.com)
- Admin: Chaitra (chaitra.admin@gmail.com)
- Faculty ONLY: Shweta Lali, Bhargav, Ravikumar, Almas (@gmail.com)
- 36 MCA Students: UUCMS IDs P02DR25S126001 to P02DR25S126036
  College: Chetan Business School
  Branch/Degree: MCA
  Emails: fullname.mca@gmail.com
- All email domains: @gmail.com
"""

import datetime
from bson.objectid import ObjectId
from utils.db import get_db, get_fs
from utils.auth import hash_password

def generate_sample_resume_pdf(student_name, uucms_id):
    """Generate a clean minimal PDF for MCA candidate resume previews"""
    content = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>/Contents 4 0 R>>endobj
4 0 obj<</Length {120 + len(student_name) + len(uucms_id)}>>stream
BT
/F1 16 Tf
50 780 Td
({student_name} - {uucms_id}) Tj
0 -24 Td
(Master of Computer Applications - Chetan Business School) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000216 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
420
%%EOF"""
    return content.encode('latin1')

def seed_mca_portal():
    db = get_db()
    fs = get_fs()
    print("Connecting to MongoDB...")

    # 1. Clear existing collections completely
    collections_to_clear = [
        'users', 'students', 'jobs', 'applications', 'announcements', 
        'notifications', 'login_logs', 'forms', 'form_responses', 'password_requests',
        'fs.files', 'fs.chunks'
    ]
    print("Purging existing dummy collections...")
    for col in collections_to_clear:
        db[col].delete_many({})
    print("Purge complete.")

    now = datetime.datetime.now()
    month_later = now + datetime.timedelta(days=30)
    week_later = now + datetime.timedelta(days=7)

    # 2. SEED STAFF USERS
    print("Seeding authorized administrative & faculty team...")
    
    super_admin_id = ObjectId()
    super_admin = {
        '_id': super_admin_id,
        'email': 'arunkumarrajput@gmail.com',
        'password': hash_password('Admin@123'),
        'role': 'admin',
        'admin_level': 'super_admin',
        'name': 'Arunkumar Rajput (Director & Super Admin)',
        'full_name': 'Arunkumar Rajput',
        'is_approved': True,
        'profile_completed': True,
        'created_at': now - datetime.timedelta(days=120),
        'last_login': now
    }

    admin_chaitra_id = ObjectId()
    admin_chaitra = {
        '_id': admin_chaitra_id,
        'email': 'chaitra.admin@gmail.com',
        'password': hash_password('Admin@123'),
        'role': 'admin',
        'admin_level': 'admin',
        'name': 'Chaitra (Placement Officer - Admin)',
        'full_name': 'Chaitra',
        'is_approved': True,
        'profile_completed': True,
        'created_at': now - datetime.timedelta(days=90),
        'last_login': now - datetime.timedelta(hours=1)
    }

    faculty_shweta_id = ObjectId()
    faculty_shweta = {
        '_id': faculty_shweta_id,
        'email': 'shweta.lali@gmail.com',
        'password': hash_password('Faculty@123'),
        'role': 'admin',
        'admin_level': 'faculty',
        'name': 'Prof. Shweta Lali (Faculty Coordinator)',
        'full_name': 'Shweta Lali',
        'is_approved': True,
        'profile_completed': True,
        'created_at': now - datetime.timedelta(days=60),
        'last_login': now - datetime.timedelta(hours=3)
    }

    faculty_bhargav_id = ObjectId()
    faculty_bhargav = {
        '_id': faculty_bhargav_id,
        'email': 'bhargav.faculty@gmail.com',
        'password': hash_password('Faculty@123'),
        'role': 'admin',
        'admin_level': 'faculty',
        'name': 'Prof. Bhargav (Faculty Coordinator)',
        'full_name': 'Bhargav',
        'is_approved': True,
        'profile_completed': True,
        'created_at': now - datetime.timedelta(days=60),
        'last_login': now - datetime.timedelta(hours=4)
    }

    faculty_ravikumar_id = ObjectId()
    faculty_ravikumar = {
        '_id': faculty_ravikumar_id,
        'email': 'ravikumar.faculty@gmail.com',
        'password': hash_password('Faculty@123'),
        'role': 'admin',
        'admin_level': 'faculty',
        'name': 'Prof. Ravikumar (Faculty Coordinator)',
        'full_name': 'Ravikumar',
        'is_approved': True,
        'profile_completed': True,
        'created_at': now - datetime.timedelta(days=60),
        'last_login': now - datetime.timedelta(hours=5)
    }

    faculty_almas_id = ObjectId()
    faculty_almas = {
        '_id': faculty_almas_id,
        'email': 'almas.faculty@gmail.com',
        'password': hash_password('Faculty@123'),
        'role': 'admin',
        'admin_level': 'faculty',
        'name': 'Prof. Almas (Faculty Coordinator)',
        'full_name': 'Almas',
        'is_approved': True,
        'profile_completed': True,
        'created_at': now - datetime.timedelta(days=60),
        'last_login': now - datetime.timedelta(hours=6)
    }

    db.users.insert_many([
        super_admin, admin_chaitra, faculty_shweta, 
        faculty_bhargav, faculty_ravikumar, faculty_almas
    ])
    print("Admin & Faculty accounts seeded successfully.")

    # 3. 36 MCA STUDENTS (UUCMS format: P02DR25S126001 to P02DR25S126036)
    print("Seeding 36 MCA students for Chetan Business School...")
    mca_names = [
        "Vikram Patel", "Sneha Gupta", "Arjun Nair", "Priya Sharma",
        "Rohit Kumar", "Ananya Deshmukh", "Kiran Kulkarni", "Pooja Hegde",
        "Rahul Verma", "Megha Shetty", "Sachin Tendulkar", "Deepika Padukone",
        "Manoj Kumar", "Kavya Maran", "Aditya Birla", "Swati Reddy",
        "Pranav Joshi", "Rashmika Mandanna", "Varun Dhawan", "Divya Spandana",
        "Kartik Aaryan", "Neha Kakkar", "Darshan Thoogudeepa", "Aishwarya Rai",
        "Yash Gowda", "Ramya Krishna", "Sudeep Sanjeev", "Shraddha Kapoor",
        "Puneeth Rajkumar", "Radhika Pandit", "Ganesh Venkat", "Kriti Sanon",
        "Vijay Sethupathi", "Samantha Ruth", "Allu Arjun", "Anushka Shetty"
    ]

    student_users = []
    student_records = []
    default_pw_hash = hash_password('Student@123')

    skill_sets = [
        ['Python', 'Flask', 'SQL', 'MongoDB', 'Git'],
        ['Java', 'Spring Boot', 'MySQL', 'REST APIs', 'Docker'],
        ['JavaScript', 'React.js', 'Node.js', 'Tailwind CSS', 'Redux'],
        ['C++', 'Data Structures', 'Algorithms', 'DBMS', 'Linux'],
        ['Python', 'Data Analytics', 'Pandas', 'PowerBI', 'SQL'],
        ['Cloud Computing', 'AWS', 'Docker', 'Kubernetes', 'Python']
    ]

    for i, name in enumerate(mca_names):
        seq = i + 1
        uucms_id = f"P02DR25S126001" if seq == 1 else f"P02DR25S1260{seq:02d}"
        
        email_prefix = name.lower().replace(" ", ".")
        email = f"{email_prefix}.mca@gmail.com"
        user_id = ObjectId()

        # Approval: first 33 approved, last 3 pending approval
        is_approved = seq <= 33
        # Verification & lock: first 22 verified & locked, remainder unverified
        is_verified = seq <= 22

        cgpa = round(7.2 + ((seq * 7) % 25) * 0.08, 2)
        score_10th = round(80.0 + ((seq * 5) % 18) * 0.8, 1)
        score_12th = round(76.0 + ((seq * 9) % 20) * 0.9, 1)
        skills = skill_sets[seq % len(skill_sets)]

        u_doc = {
            '_id': user_id,
            'email': email,
            'password': default_pw_hash,
            'role': 'student',
            'name': name,
            'full_name': name,
            'is_approved': is_approved,
            'profile_completed': True,
            'created_at': now - datetime.timedelta(days=45 - seq),
            'last_login': now - datetime.timedelta(hours=(seq * 3) % 48) if is_approved else None
        }
        student_users.append(u_doc)

        pdf_bytes = generate_sample_resume_pdf(name, uucms_id)
        resume_id = fs.put(
            pdf_bytes,
            filename=f"Resume_{name.replace(' ', '_')}.pdf",
            content_type='application/pdf',
            metadata={'student_id': uucms_id, 'type': 'resume'}
        )

        st_doc = {
            'user_id': user_id,
            'student_id': uucms_id,
            'name': name,
            'college': 'Chetan Business School',
            'contact_email': email,
            'phone': f"98765{seq:05d}",
            'gender': 'Female' if seq % 2 == 0 else 'Male',
            'dob': '2002-05-15',
            'resume_file_id': resume_id,
            'is_verified': is_verified,
            'verified_by': 'Arunkumar Rajput' if is_verified else None,
            'verified_at': now - datetime.timedelta(days=20) if is_verified else None,
            'scores_frozen': is_verified,
            'score_10th': score_10th,
            'score_12th': score_12th,
            'education': {
                'tenth': {'score': score_10th, 'board': 'KSEEB', 'year': 2018},
                'twelfth': {'score': score_12th, 'board': 'Karnataka PU Board', 'year': 2020},
                'graduation': {
                    'college': 'Chetan Business School',
                    'university': 'Rani Channamma University',
                    'degree': 'BCA',
                    'branch': 'Computer Applications',
                    'score': round(cgpa - 0.2, 2),
                    'year': 2023,
                    'backlogs': 0
                },
                'post_graduation': {
                    'college': 'Chetan Business School',
                    'university': 'Rani Channamma University',
                    'degree': 'MCA',
                    'branch': 'Master of Computer Applications',
                    'score': cgpa,
                    'year': 2025,
                    'backlogs': 0
                }
            },
            'branch': 'MCA',
            'degree': 'MCA',
            'cgpa': cgpa,
            'skills': skills,
            'projects': f"CBS MCA Enterprise Placement System; AI-powered candidate tracker in Python",
            'is_active': True,
            'is_placed': False,
            'placement_status': 'Active_Candidate',
            'created_at': now - datetime.timedelta(days=45 - seq),
            'profile_updated_at': now - datetime.timedelta(days=2)
        }
        student_records.append(st_doc)

    db.users.insert_many(student_users)
    db.students.insert_many(student_records)
    print("36 MCA students successfully created.")

    # 4. ENTERPRISE RECRUITMENT DRIVES FOR MCA
    print("Creating realistic MCA recruitment drives...")
    jobs_data = [
        {
            'company_name': 'Google India',
            'role': 'Cloud Solutions Engineer',
            'description': 'Architect enterprise workloads on Google Cloud Platform (GCP). Involves Kubernetes, distributed database design, and cloud migrations. Seeking high analytical MCA candidates.',
            'package': '18.0 LPA',
            'location': 'Bangalore DC',
            'employment_type': 'Full Time',
            'min_cgpa': 7.5,
            'drive_date': week_later + datetime.timedelta(days=2),
            'expires_at': month_later,
            'status': 'published',
            'created_by': super_admin['email'],
            'created_by_id': super_admin_id,
            'author_role': 'super_admin',
            'created_at': now - datetime.timedelta(days=10),
            'published_at': now - datetime.timedelta(days=10),
            'external_url': 'https://careers.google.com'
        },
        {
            'company_name': 'Microsoft',
            'role': 'Software Development Engineer',
            'description': 'Develop scalable backend cloud APIs and developer tooling using C#, .NET Core, Azure, and distributed caching systems.',
            'package': '22.0 LPA',
            'location': 'Hyderabad / Bangalore',
            'employment_type': 'Full Time',
            'min_cgpa': 7.5,
            'drive_date': week_later + datetime.timedelta(days=5),
            'expires_at': month_later,
            'status': 'published',
            'created_by': super_admin['email'],
            'created_by_id': super_admin_id,
            'author_role': 'super_admin',
            'created_at': now - datetime.timedelta(days=8),
            'published_at': now - datetime.timedelta(days=8),
            'external_url': 'https://careers.microsoft.com'
        },
        {
            'company_name': 'Amazon',
            'role': 'Frontend Engineer (SDE-1)',
            'description': 'Deliver ultra-responsive web experiences for AWS console and Amazon retail using React, TypeScript, and high-performance Web APIs.',
            'package': '16.0 LPA',
            'location': 'Bangalore',
            'employment_type': 'Full Time',
            'min_cgpa': 7.2,
            'drive_date': week_later + datetime.timedelta(days=7),
            'expires_at': month_later,
            'status': 'published',
            'created_by': admin_chaitra['email'],
            'created_by_id': admin_chaitra_id,
            'author_role': 'admin',
            'created_at': now - datetime.timedelta(days=7),
            'published_at': now - datetime.timedelta(days=7),
            'external_url': 'https://amazon.jobs'
        },
        {
            'company_name': 'Infosys',
            'role': 'Specialist Programmer (Power Programmer)',
            'description': 'High-performance coding role focusing on modern full-stack architectures, algorithms, microservices, and AI workflow integration.',
            'package': '9.5 LPA',
            'location': 'Mysore / Bangalore',
            'employment_type': 'Full Time',
            'min_cgpa': 7.0,
            'drive_date': week_later + datetime.timedelta(days=10),
            'expires_at': month_later,
            'status': 'published',
            'created_by': faculty_shweta['email'],
            'created_by_id': faculty_shweta_id,
            'author_role': 'faculty',
            'created_at': now - datetime.timedelta(days=6),
            'published_at': now - datetime.timedelta(days=6),
            'external_url': 'https://www.infosys.com/careers.html'
        },
        {
            'company_name': 'Tata Consultancy Services',
            'role': 'Digital Innovator',
            'description': 'Work with TCS Digital engineering teams on modern cloud architectures, enterprise analytics, and Python/Java microservices.',
            'package': '7.5 LPA',
            'location': 'Bangalore / Pune',
            'employment_type': 'Full Time',
            'min_cgpa': 7.0,
            'drive_date': week_later + datetime.timedelta(days=12),
            'expires_at': month_later,
            'status': 'published',
            'created_by': faculty_bhargav['email'],
            'created_by_id': faculty_bhargav_id,
            'author_role': 'faculty',
            'created_at': now - datetime.timedelta(days=5),
            'published_at': now - datetime.timedelta(days=5),
            'external_url': 'https://www.tcs.com/careers'
        },
        {
            'company_name': 'Wipro',
            'role': 'Turbo Developer (Cloud & DevOps)',
            'description': 'Enterprise deployment, CI/CD pipelines, containerized environments, and cloud backend solutions for global clients.',
            'package': '6.5 LPA',
            'location': 'Bangalore',
            'employment_type': 'Full Time',
            'min_cgpa': 6.8,
            'drive_date': week_later + datetime.timedelta(days=14),
            'expires_at': month_later,
            'status': 'published',
            'created_by': faculty_ravikumar['email'],
            'created_by_id': faculty_ravikumar_id,
            'author_role': 'faculty',
            'created_at': now - datetime.timedelta(days=4),
            'published_at': now - datetime.timedelta(days=4),
            'external_url': 'https://careers.wipro.com'
        },
        {
            'company_name': 'Zomato',
            'role': 'Product Engineering Intern (PPO)',
            'description': 'Real-time order routing, consumer mobile app micro-frontends, high-throughput backend services handling millions of orders daily.',
            'package': '10.0 LPA',
            'location': 'Gurgaon / Bangalore',
            'employment_type': 'Full Time',
            'min_cgpa': 7.0,
            'drive_date': week_later + datetime.timedelta(days=16),
            'expires_at': month_later,
            'status': 'published',
            'created_by': faculty_almas['email'],
            'created_by_id': faculty_almas_id,
            'author_role': 'faculty',
            'created_at': now - datetime.timedelta(days=4),
            'published_at': now - datetime.timedelta(days=4),
            'external_url': 'https://www.zomato.com/careers'
        },
        {
            'company_name': 'Oracle',
            'role': 'Database & Cloud Associate',
            'description': 'Database performance tuning, Oracle Cloud Infrastructure (OCI) implementation, SQL query optimization, and enterprise database systems.',
            'package': '12.0 LPA',
            'location': 'Bangalore',
            'employment_type': 'Full Time',
            'min_cgpa': 7.0,
            'drive_date': week_later + datetime.timedelta(days=18),
            'expires_at': month_later,
            'status': 'published',
            'created_by': admin_chaitra['email'],
            'created_by_id': admin_chaitra_id,
            'author_role': 'admin',
            'created_at': now - datetime.timedelta(days=3),
            'published_at': now - datetime.timedelta(days=3),
            'external_url': 'https://www.oracle.com/corporate/careers/'
        },
        {
            'company_name': 'Cisco',
            'role': 'Software Engineer - Network Cloud',
            'description': 'Network virtualization, telemetry data pipelines, security protocols, and Python/Golang microservices for enterprise routing gear.',
            'package': '14.0 LPA',
            'location': 'Bangalore',
            'employment_type': 'Full Time',
            'min_cgpa': 7.2,
            'drive_date': week_later + datetime.timedelta(days=20),
            'expires_at': month_later,
            'status': 'published',
            'created_by': super_admin['email'],
            'created_by_id': super_admin_id,
            'author_role': 'super_admin',
            'created_at': now - datetime.timedelta(days=2),
            'published_at': now - datetime.timedelta(days=2),
            'external_url': 'https://www.cisco.com/c/en/us/about/careers.html'
        },
        {
            'company_name': 'Deloitte',
            'role': 'Analyst - Technology Consulting',
            'description': 'Transform client legacy enterprise applications into cloud-native architectures, business analytics, and automation suites.',
            'package': '8.0 LPA',
            'location': 'Hyderabad / Bangalore',
            'employment_type': 'Full Time',
            'min_cgpa': 6.8,
            'drive_date': week_later + datetime.timedelta(days=22),
            'expires_at': month_later,
            'status': 'published',
            'created_by': faculty_shweta['email'],
            'created_by_id': faculty_shweta_id,
            'author_role': 'faculty',
            'created_at': now - datetime.timedelta(days=2),
            'published_at': now - datetime.timedelta(days=2),
            'external_url': 'https://www2.deloitte.com/careers'
        }
    ]

    job_res = db.jobs.insert_many(jobs_data)
    job_ids = job_res.inserted_ids
    print(f"Inserted {len(job_ids)} recruitment drives.")

    # 5. APPLICATIONS WITH MULTI-APPLICATION WARNING & EXTENDED STAGES
    print("Generating candidate application records across drives...")
    google_j = jobs_data[0]
    google_jid = job_ids[0]

    msft_j = jobs_data[1]
    msft_jid = job_ids[1]

    amzn_j = jobs_data[2]
    amzn_jid = job_ids[2]

    infy_j = jobs_data[3]
    infy_jid = job_ids[3]

    tcs_j = jobs_data[4]
    tcs_jid = job_ids[4]

    wipro_j = jobs_data[5]
    wipro_jid = job_ids[5]

    zomato_j = jobs_data[6]
    zomato_jid = job_ids[6]

    oracle_j = jobs_data[7]
    oracle_jid = job_ids[7]

    student_resumes = {s['user_id']: s.get('resume_file_id') for s in student_records}
    student_uucms = {s['user_id']: s.get('student_id') for s in student_records}

    apps_data = []

    # Student 1: Vikram Patel (Applied to 3 drives -> Multiple Applicant ⚠️)
    v_u = student_users[0]
    apps_data.extend([
        {
            'student_id': v_u['_id'],
            'job_id': google_jid,
            'company_name': google_j['company_name'],
            'job_role': google_j['role'],
            'student_name': v_u['name'],
            'student_email': v_u['email'],
            'student_phone': '9876500001',
            'cgpa': 8.85,
            'branch': 'MCA',
            'status': 'Technical_R1',
            'resume_file_id': student_resumes.get(v_u['_id']),
            'uucms_id': student_uucms.get(v_u['_id']),
            'student_uucms_id': student_uucms.get(v_u['_id']),
            'student_response': 'Attending',
            'response_at': now - datetime.timedelta(hours=2),
            'applied_at': now - datetime.timedelta(hours=6)
        },
        {
            'student_id': v_u['_id'],
            'job_id': msft_jid,
            'company_name': msft_j['company_name'],
            'job_role': msft_j['role'],
            'student_name': v_u['name'],
            'student_email': v_u['email'],
            'student_phone': '9876500001',
            'cgpa': 8.85,
            'branch': 'MCA',
            'status': 'Shortlisted',
            'resume_file_id': student_resumes.get(v_u['_id']),
            'uucms_id': student_uucms.get(v_u['_id']),
            'student_uucms_id': student_uucms.get(v_u['_id']),
            'applied_at': now - datetime.timedelta(hours=14)
        },
        {
            'student_id': v_u['_id'],
            'job_id': amzn_jid,
            'company_name': amzn_j['company_name'],
            'job_role': amzn_j['role'],
            'student_name': v_u['name'],
            'student_email': v_u['email'],
            'student_phone': '9876500001',
            'cgpa': 8.85,
            'branch': 'MCA',
            'status': 'Rejected',
            'rejection_stage': 'Technical Interview Round 1',
            'rejection_reason': 'Demonstrated strong logic; advise improving binary search tree edge-case handling.',
            'resume_file_id': student_resumes.get(v_u['_id']),
            'uucms_id': student_uucms.get(v_u['_id']),
            'student_uucms_id': student_uucms.get(v_u['_id']),
            'applied_at': now - datetime.timedelta(days=1, hours=2)
        }
    ])

    # Student 2: Sneha Gupta (Selected / Placed at Google India!)
    s_u = student_users[1]
    apps_data.extend([
        {
            'student_id': s_u['_id'],
            'job_id': google_jid,
            'company_name': google_j['company_name'],
            'job_role': google_j['role'],
            'student_name': s_u['name'],
            'student_email': s_u['email'],
            'student_phone': '9876500002',
            'cgpa': 9.2,
            'branch': 'MCA',
            'status': 'Selected',
            'resume_file_id': student_resumes.get(s_u['_id']),
            'uucms_id': student_uucms.get(s_u['_id']),
            'student_uucms_id': student_uucms.get(s_u['_id']),
            'student_response': 'Attending',
            'response_at': now - datetime.timedelta(hours=4),
            'applied_at': now - datetime.timedelta(hours=8)
        },
        {
            'student_id': s_u['_id'],
            'job_id': msft_jid,
            'company_name': msft_j['company_name'],
            'job_role': msft_j['role'],
            'student_name': s_u['name'],
            'student_email': s_u['email'],
            'student_phone': '9876500002',
            'cgpa': 9.2,
            'branch': 'MCA',
            'status': 'AUTO_WITHDRAWN',
            'resume_file_id': student_resumes.get(s_u['_id']),
            'uucms_id': student_uucms.get(s_u['_id']),
            'student_uucms_id': student_uucms.get(s_u['_id']),
            'applied_at': now - datetime.timedelta(days=1, hours=5)
        }
    ])
    # Update Sneha's student profile with placed state
    db.students.update_one(
        {'user_id': s_u['_id']},
        {'$set': {
            'is_placed': True,
            'placement_status': 'Placed_Pending_Exit',
            'placed_company': 'Google India',
            'placed_role': 'Cloud Solutions Engineer',
            'placed_at': now - datetime.timedelta(days=1),
            'exit_deadline': now + datetime.timedelta(days=1),
            'auto_exited': False
        }}
    )

    # Student 3: Arjun Nair (Applied to 2 drives -> Multiple Applicant ⚠️)
    a_u = student_users[2]
    apps_data.extend([
        {
            'student_id': a_u['_id'],
            'job_id': tcs_jid,
            'company_name': tcs_j['company_name'],
            'job_role': tcs_j['role'],
            'student_name': a_u['name'],
            'student_email': a_u['email'],
            'student_phone': '9876500003',
            'cgpa': 7.8,
            'branch': 'MCA',
            'status': 'Aptitude',
            'resume_file_id': student_resumes.get(a_u['_id']),
            'uucms_id': student_uucms.get(a_u['_id']),
            'student_uucms_id': student_uucms.get(a_u['_id']),
            'applied_at': now - datetime.timedelta(hours=12)
        },
        {
            'student_id': a_u['_id'],
            'job_id': infy_jid,
            'company_name': infy_j['company_name'],
            'job_role': infy_j['role'],
            'student_name': a_u['name'],
            'student_email': a_u['email'],
            'student_phone': '9876500003',
            'cgpa': 7.8,
            'branch': 'MCA',
            'status': 'Shortlisted',
            'resume_file_id': student_resumes.get(a_u['_id']),
            'uucms_id': student_uucms.get(a_u['_id']),
            'student_uucms_id': student_uucms.get(a_u['_id']),
            'applied_at': now - datetime.timedelta(days=1, hours=3)
        }
    ])

    # Student 4: Priya Sharma (Selected at Zomato -> Multiple Applicant ⚠️)
    p_u = student_users[3]
    apps_data.extend([
        {
            'student_id': p_u['_id'],
            'job_id': zomato_jid,
            'company_name': zomato_j['company_name'],
            'job_role': zomato_j['role'],
            'student_name': p_u['name'],
            'student_email': p_u['email'],
            'student_phone': '9876500004',
            'cgpa': 8.45,
            'branch': 'MCA',
            'status': 'Selected',
            'resume_file_id': student_resumes.get(p_u['_id']),
            'uucms_id': student_uucms.get(p_u['_id']),
            'student_uucms_id': student_uucms.get(p_u['_id']),
            'applied_at': now - datetime.timedelta(hours=6)
        },
        {
            'student_id': p_u['_id'],
            'job_id': amzn_jid,
            'company_name': amzn_j['company_name'],
            'job_role': amzn_j['role'],
            'student_name': p_u['name'],
            'student_email': p_u['email'],
            'student_phone': '9876500004',
            'cgpa': 8.45,
            'branch': 'MCA',
            'status': 'HR_Interview',
            'resume_file_id': student_resumes.get(p_u['_id']),
            'uucms_id': student_uucms.get(p_u['_id']),
            'student_uucms_id': student_uucms.get(p_u['_id']),
            'applied_at': now - datetime.timedelta(days=1, hours=4)
        }
    ])
    # Update Priya's student profile
    db.students.update_one(
        {'user_id': p_u['_id']},
        {'$set': {
            'is_placed': True,
            'placement_status': 'Placed_Pending_Exit',
            'placed_company': 'Zomato',
            'placed_role': 'Product Engineering Intern (PPO)',
            'placed_at': now - datetime.timedelta(hours=18),
            'exit_deadline': now + datetime.timedelta(days=1, hours=6),
            'auto_exited': False
        }}
    )

    # Spread other students across drives with various stages
    drive_selection_pool = [
        (infy_jid, infy_j, 'Technical_R2'),
        (tcs_jid, tcs_j, 'GD'),
        (wipro_jid, wipro_j, 'Shortlisted'),
        (oracle_jid, oracle_j, 'Aptitude'),
        (google_jid, google_j, 'Applied'),
        (msft_jid, msft_j, 'HR_Interview'),
        (amzn_jid, amzn_j, 'Applied')
    ]

    for idx, u in enumerate(student_users[4:30]):
        pool_item = drive_selection_pool[idx % len(drive_selection_pool)]
        apps_data.append({
            'student_id': u['_id'],
            'job_id': pool_item[0],
            'company_name': pool_item[1]['company_name'],
            'job_role': pool_item[1]['role'],
            'student_name': u['name'],
            'student_email': u['email'],
            'student_phone': f"98765{idx+5:05d}",
            'cgpa': round(7.4 + ((idx * 7) % 20) * 0.08, 2),
            'branch': 'MCA',
            'status': pool_item[2],
            'resume_file_id': student_resumes.get(u['_id']),
            'uucms_id': student_uucms.get(u['_id']),
            'student_uucms_id': student_uucms.get(u['_id']),
            'applied_at': now - datetime.timedelta(hours=((idx * 3) % 40) + 2)
        })

    db.applications.insert_many(apps_data)
    print(f"Inserted {len(apps_data)} realistic application records.")

    # 6. DYNAMIC FORMS FOR MCA
    print("Seeding dynamic custom surveys...")
    form1 = {
        'title': 'MCA Placement Domain & Skill Track Preference 2026',
        'description': 'Please submit your specialized career tracks (Full Stack, Cloud & DevOps, Data Analytics, or Cybersecurity) and preferred work locations to help the CBS 3i-cell invite tailored recruiters.',
        'created_by': super_admin['email'],
        'created_by_id': super_admin_id,
        'is_active': True,
        'created_at': now - datetime.timedelta(days=12),
        'fields': [
            {'field_id': 'f1', 'label': 'Primary Technical Domain', 'type': 'select', 'required': True, 'options': ['Full-Stack Development', 'Cloud Architecture & DevOps', 'Data Engineering & AI', 'Enterprise Software Testing']},
            {'field_id': 'f2', 'label': 'Preferred Metro Placement Cities', 'type': 'checkbox', 'required': True, 'options': ['Bangalore', 'Hyderabad', 'Pune', 'Chennai', 'Mumbai']},
            {'field_id': 'f3', 'label': 'Certifications Completed (AWS, Azure, GCP, Oracle)', 'type': 'text', 'required': False}
        ]
    }

    form2 = {
        'title': 'Industry Internship & Higher Studies Undertaking',
        'description': 'Mandatory undertaking form for final-year MCA candidates opting for 6-month industry internships versus immediate full-time employment.',
        'created_by': admin_chaitra['email'],
        'created_by_id': admin_chaitra_id,
        'is_active': True,
        'created_at': now - datetime.timedelta(days=5),
        'fields': [
            {'field_id': 'f1', 'label': 'Do you intend to undertake an external 6-month MCA internship?', 'type': 'radio', 'required': True, 'options': ['Yes, looking for corporate internship', 'No, strictly full-time employment only']},
            {'field_id': 'f2', 'label': 'Passport Availability for Offshore Client Engagements', 'type': 'radio', 'required': True, 'options': ['Yes, Valid Passport Available', 'Applied / In Process', 'Not Yet Applied']}
        ]
    }
    db.forms.insert_many([form1, form2])
    print("Custom forms seeded.")

    # 7. TOWN HALL ANNOUNCEMENTS
    print("Seeding town hall notifications...")
    announcements = [
        {
            'title': '🚀 CBS MCA Placement Drive Season 2026 Officially Launched',
            'content': 'Welcome to the MCA 2026 placement season. Google Cloud, Microsoft, Amazon, Infosys, and TCS have confirmed on-campus and virtual hiring rounds. Ensure your academic records and resume PDFs are verified by the placement office.',
            'created_by': super_admin['email'],
            'created_by_name': 'Arunkumar Rajput (Super Admin)',
            'role': 'super_admin',
            'created_at': now - datetime.timedelta(days=14),
            'priority': 'high'
        },
        {
            'title': '📋 Strict Compliance: Single Offer & Corporate Exit Guidelines',
            'content': 'Per Chetan Business School placement policy, candidates receiving a confirmed offer must acknowledge within 48 hours. The portal automates placement records and transitions candidates to allow fellow classmates opportunities in subsequent drives.',
            'created_by': admin_chaitra['email'],
            'created_by_name': 'Chaitra (Placement Officer)',
            'role': 'admin',
            'created_at': now - datetime.timedelta(days=7),
            'priority': 'medium'
        },
        {
            'title': '💻 Coding & Aptitude Mock Assessment Schedule in Lab 3',
            'content': 'Prof. Shweta Lali, Prof. Bhargav, Prof. Ravikumar, and Prof. Almas will be hosting weekly technical grooming and mock interview sessions every Tuesday and Thursday at 3:30 PM.',
            'created_by': faculty_shweta['email'],
            'created_by_name': 'Prof. Shweta Lali (Faculty Coordinator)',
            'role': 'faculty',
            'created_at': now - datetime.timedelta(days=3),
            'priority': 'medium'
        }
    ]
    db.announcements.insert_many(announcements)
    print("Town hall announcements seeded.")

    print("\n=======================================================")
    print("SUCCESS: MCA PORTAL DATABASE RE-SEEDED SUCCESSFULLY!")
    print("=======================================================")
    print("Super Admin : Arunkumar Rajput (arunkumarrajput@gmail.com / Admin@123)")
    print("Admin       : Chaitra (chaitra.admin@gmail.com / Admin@123)")
    print("Faculty     : Shweta Lali (shweta.lali@gmail.com / Faculty@123)")
    print("Faculty     : Bhargav (bhargav.faculty@gmail.com / Faculty@123)")
    print("Faculty     : Ravikumar (ravikumar.faculty@gmail.com / Faculty@123)")
    print("Faculty     : Almas (almas.faculty@gmail.com / Faculty@123)")
    print("Students    : 36 MCA Students (P02DR25S126001 to P02DR25S126036 / Student@123)")
    print("College     : Chetan Business School | Degree: MCA")
    print("=======================================================\n")

if __name__ == '__main__':
    seed_mca_portal()
