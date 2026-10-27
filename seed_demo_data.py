import datetime
from bson.objectid import ObjectId
from utils.db import get_db
from utils.auth import hash_password

def seed_all():
    db = get_db()
    print("Connecting to MongoDB...")

    # Clear existing demo data cleanly
    print("Clearing old collections...")
    for coll in ['users', 'students', 'jobs', 'applications', 'announcements', 
                 'notifications', 'login_logs', 'forms', 'form_responses', 'password_requests']:
        db[coll].delete_many({})

    now = datetime.datetime.now()
    month_later = now + datetime.timedelta(days=30)
    week_later = now + datetime.timedelta(days=7)

    # 1. ADMIN USERS
    print("Creating admin accounts...")
    admin_id = ObjectId()
    admin_user = {
        '_id': admin_id,
        'email': 'admin@cbs.edu',
        'password': hash_password('Admin@123'),
        'role': 'admin',
        'admin_level': 'super_admin',
        'name': 'Dr. Rajesh Sharma (Head - 3i-cell)',
        'full_name': 'Dr. Rajesh Sharma',
        'is_approved': True,
        'profile_completed': True,
        'created_at': now - datetime.timedelta(days=90),
        'last_login': now
    }

    faculty_id = ObjectId()
    faculty_user = {
        '_id': faculty_id,
        'email': 'faculty@cbs.edu',
        'password': hash_password('Faculty@123'),
        'role': 'admin',
        'admin_level': 'faculty',
        'name': 'Prof. Ananya Sen (Placement Officer)',
        'full_name': 'Prof. Ananya Sen',
        'is_approved': True,
        'profile_completed': True,
        'created_at': now - datetime.timedelta(days=60),
        'last_login': now - datetime.timedelta(hours=2)
    }

    db.users.insert_many([admin_user, faculty_user])

    # 2. STUDENT USERS & PROFILES
    print("Creating student accounts and detailed profiles...")
    students_data = [
        {
            'email': 'student@cbs.edu',
            'password': 'Student@123',
            'name': 'Vikram Patel',
            'roll_no': '22BCSE101',
            'branch': 'Computer Science & Engineering',
            'cgpa': 8.85,
            'phone': '9876543210',
            'gender': 'Male',
            'skills': ['Python', 'React', 'Node.js', 'MongoDB', 'Docker', 'FastAPI'],
            'projects': 'CBS Placement Portal Modern PWA; Distributed Rate Limiter in Go',
            'score_10th': 92.5,
            'score_12th': 91.0,
            'address': 'Flat 402, Green Glen Layout, Bellandur, Bangalore - 560103',
            'approved': True
        },
        {
            'email': 'sneha.gupta@cbs.edu',
            'password': 'Student@123',
            'name': 'Sneha Gupta',
            'roll_no': '22BIT102',
            'branch': 'Information Technology',
            'cgpa': 9.20,
            'phone': '9876543211',
            'gender': 'Female',
            'skills': ['Java', 'Spring Boot', 'AWS', 'PostgreSQL', 'Microservices', 'Kubernetes'],
            'projects': 'Cloud-native Banking API; Real-time Kafka Event Streaming Engine',
            'score_10th': 95.0,
            'score_12th': 93.5,
            'address': 'Plot 18, Sector 14, HSR Layout, Bangalore - 560102',
            'approved': True
        },
        {
            'email': 'arjun.nair@cbs.edu',
            'password': 'Student@123',
            'name': 'Arjun Nair',
            'roll_no': '22BECE103',
            'branch': 'Electronics & Communication',
            'cgpa': 7.80,
            'phone': '9876543212',
            'gender': 'Male',
            'skills': ['C++', 'Embedded Systems', 'IoT', 'Python', 'RTOS', 'Linux'],
            'projects': 'Smart Industrial IoT Monitoring Sensor Hub; Autonomous Rover Controller',
            'score_10th': 88.0,
            'score_12th': 85.0,
            'address': '224, 7th Main, Koramangala 4th Block, Bangalore - 560034',
            'approved': True
        },
        {
            'email': 'priya.sharma@cbs.edu',
            'password': 'Student@123',
            'name': 'Priya Sharma',
            'roll_no': '22BCSE104',
            'branch': 'Computer Science & Engineering',
            'cgpa': 8.45,
            'phone': '9876543213',
            'gender': 'Female',
            'skills': ['UI/UX Design', 'Figma', 'React', 'TypeScript', 'TailwindCSS', 'Next.js'],
            'projects': 'Design System for EdTech; Accessible Healthcare Web Application',
            'score_10th': 90.5,
            'score_12th': 89.0,
            'address': '45, Palm Meadows, Whitefield, Bangalore - 560066',
            'approved': True
        },
        {
            'email': 'rohit.kumar@cbs.edu',
            'password': 'Student@123',
            'name': 'Rohit Kumar',
            'roll_no': '22BME105',
            'branch': 'Mechanical Engineering',
            'cgpa': 7.35,
            'phone': '9876543214',
            'gender': 'Male',
            'skills': ['AutoCAD', 'SolidWorks', 'ANSYS', 'Python for Engineers', 'MATLAB'],
            'projects': 'Aerodynamic Drag Optimization in Electric Two-Wheelers',
            'score_10th': 84.0,
            'score_12th': 81.0,
            'address': '89, BTM Layout 2nd Stage, Bangalore - 560076',
            'approved': False  # Pending Approval demo!
        }
    ]

    student_records = []
    student_users = []

    for s in students_data:
        s_id = ObjectId()
        user_doc = {
            '_id': s_id,
            'email': s['email'],
            'password': hash_password(s['password']),
            'role': 'student',
            'name': s['name'],
            'profile_completed': True,
            'is_approved': s['approved'],
            'created_at': now - datetime.timedelta(days=45),
            'last_login': now - datetime.timedelta(minutes=15)
        }
        student_users.append(user_doc)

        student_doc = {
            'user_id': s_id,
            'student_id': s['roll_no'],
            'name': s['name'],
            'personal_email': s['email'],
            'phone': s['phone'],
            'alt_phone': '9123456789',
            'gender': s['gender'],
            'dob': '2004-03-15',
            'nationality': 'Indian',
            'marital_status': 'Single',
            'aadhaar': 'XXXX-XXXX-9876',
            'pan': 'ABCDE1234F',
            'address': {
                'permanent': s['address'],
                'current': 'CBS Campus Hostel Block, Room 204'
            },
            'academic': {
                'tenth': {
                    'school': 'National Public School',
                    'board': 'CBSE',
                    'year': 2020,
                    'score': s['score_10th']
                },
                'twelfth': {
                    'school': 'Delhi Public School',
                    'board': 'CBSE',
                    'year': 2022,
                    'score': s['score_12th'],
                    'stream': 'Science'
                },
                'ug': {
                    'college': 'Chetan Business School',
                    'university': 'VTU',
                    'degree': 'B.Tech',
                    'branch': s['branch'],
                    'year': 2026,
                    'score': s['cgpa'],
                    'backlogs': 0,
                    'backlog_status': 'No Backlogs'
                },
                'pg': {
                    'college': '',
                    'university': '',
                    'degree': '',
                    'branch': '',
                    'year': None,
                    'score': None,
                    'backlogs': 0,
                    'backlog_status': ''
                }
            },
            'branch': s['branch'],
            'cgpa': s['cgpa'],
            'skills': s['skills'],
            'projects': s['projects'],
            'is_active': True,
            'created_at': now - datetime.timedelta(days=45),
            'profile_updated_at': now - datetime.timedelta(days=2)
        }
        student_records.append(student_doc)

    db.users.insert_many(student_users)
    db.students.insert_many(student_records)

    # 3. JOBS / RECRUITMENT DRIVES
    print("Creating diverse recruitment opportunities...")
    jobs_data = [
        {
            'company_name': 'Google India',
            'role': 'Software Development Engineer (SDE-1)',
            'description': 'Work on large-scale distributed systems, Google Cloud platform components, and developer tooling. Requires high algorithmic problem solving, clean code architecture, and proficiency in Python, Java, or C++.',
            'package': '24.5 LPA',
            'location': 'Bangalore / Hyderabad',
            'employment_type': 'Full Time',
            'min_cgpa': 8.0,
            'drive_date': week_later,
            'expires_at': month_later,
            'status': 'published',
            'created_by': admin_user['email'],
            'created_by_id': admin_id,
            'author_role': 'super_admin',
            'created_at': now - datetime.timedelta(days=5),
            'updated_at': now - datetime.timedelta(days=5),
            'published_at': now - datetime.timedelta(days=5),
            'external_url': 'https://careers.google.com'
        },
        {
            'company_name': 'Microsoft',
            'role': 'Cloud Solutions Engineer',
            'description': 'Design, deploy, and optimize mission-critical cloud infrastructure on Microsoft Azure. Collaborate with enterprise customers on hybrid cloud architectures, container orchestration, and high-availability systems.',
            'package': '19.0 LPA',
            'location': 'Hyderabad / Bangalore',
            'employment_type': 'Full Time',
            'min_cgpa': 7.5,
            'drive_date': week_later + datetime.timedelta(days=3),
            'expires_at': month_later,
            'status': 'published',
            'created_by': admin_user['email'],
            'created_by_id': admin_id,
            'author_role': 'super_admin',
            'created_at': now - datetime.timedelta(days=6),
            'updated_at': now - datetime.timedelta(days=6),
            'published_at': now - datetime.timedelta(days=6),
            'external_url': 'https://careers.microsoft.com'
        },
        {
            'company_name': 'Amazon',
            'role': 'Frontend Engineer (SDE-1)',
            'description': 'Deliver intuitive, responsive, and ultra-fast web experiences for hundreds of millions of worldwide customers. Work deeply with TypeScript, React, state management, and web performance optimization.',
            'package': '16.8 LPA',
            'location': 'Bangalore',
            'employment_type': 'Full Time',
            'min_cgpa': 7.5,
            'drive_date': week_later + datetime.timedelta(days=5),
            'expires_at': month_later,
            'status': 'published',
            'created_by': faculty_user['email'],
            'created_by_id': faculty_id,
            'author_role': 'faculty',
            'created_at': now - datetime.timedelta(days=4),
            'updated_at': now - datetime.timedelta(days=4),
            'published_at': now - datetime.timedelta(days=4),
            'external_url': 'https://amazon.jobs'
        },
        {
            'company_name': 'Deloitte USI',
            'role': 'Analyst - Technology & Risk Advisory',
            'description': 'Perform enterprise cybersecurity reviews, cloud governance assessments, and secure code audits. Provide strategic tech consulting for Fortune 500 financial and healthcare organizations.',
            'package': '9.5 LPA',
            'location': 'Bangalore / Gurugram',
            'employment_type': 'Full Time',
            'min_cgpa': 7.0,
            'drive_date': week_later + datetime.timedelta(days=8),
            'expires_at': month_later,
            'status': 'published',
            'created_by': faculty_user['email'],
            'created_by_id': faculty_id,
            'author_role': 'faculty',
            'created_at': now - datetime.timedelta(days=3),
            'updated_at': now - datetime.timedelta(days=3),
            'published_at': now - datetime.timedelta(days=3),
            'external_url': 'https://www2.deloitte.com'
        },
        {
            'company_name': 'Tata Consultancy Services',
            'role': 'Digital Systems Engineer',
            'description': 'Development of modern enterprise applications across Banking, Retail, and Telecom verticals. Extensive training on Generative AI, cloud modernization, and full-stack software development.',
            'package': '7.5 LPA',
            'location': 'Pune / Mumbai / Bangalore',
            'employment_type': 'Full Time',
            'min_cgpa': 6.5,
            'drive_date': week_later + datetime.timedelta(days=12),
            'expires_at': month_later,
            'status': 'published',
            'created_by': faculty_user['email'],
            'created_by_id': faculty_id,
            'author_role': 'faculty',
            'created_at': now - datetime.timedelta(days=2),
            'updated_at': now - datetime.timedelta(days=2),
            'published_at': now - datetime.timedelta(days=2),
            'external_url': 'https://www.tcs.com'
        },
        {
            'company_name': 'Zomato',
            'role': 'Product Engineering Intern (PPO)',
            'description': 'High velocity feature development on consumer delivery apps and restaurant partner systems. 6 months internship with attractive stipend followed by full-time absorption based on performance.',
            'package': '₹65,000 / month (PPO 15 LPA)',
            'location': 'Gurgaon / Remote',
            'employment_type': 'Internship',
            'min_cgpa': 7.0,
            'drive_date': week_later + datetime.timedelta(days=6),
            'expires_at': month_later,
            'status': 'published',
            'created_by': admin_user['email'],
            'created_by_id': admin_id,
            'author_role': 'super_admin',
            'created_at': now - datetime.timedelta(days=1),
            'updated_at': now - datetime.timedelta(days=1),
            'published_at': now - datetime.timedelta(days=1),
            'external_url': 'https://www.zomato.com'
        }
    ]

    job_insert_res = db.jobs.insert_many(jobs_data)
    inserted_job_ids = job_insert_res.inserted_ids

    # 4. APPLICATIONS (Connect students to jobs with active stages)
    print("Creating realistic application pipelines...")
    vikram_uid = student_users[0]['_id']
    sneha_uid = student_users[1]['_id']
    arjun_uid = student_users[2]['_id']
    priya_uid = student_users[3]['_id']

    google_jid = inserted_job_ids[0]
    msft_jid = inserted_job_ids[1]
    amzn_jid = inserted_job_ids[2]
    deloitte_jid = inserted_job_ids[3]
    tcs_jid = inserted_job_ids[4]
    zomato_jid = inserted_job_ids[5]

    applications_data = [
        # Vikram Patel
        {
            'student_id': vikram_uid,
            'job_id': google_jid,
            'company_name': 'Google India',
            'job_role': 'Software Development Engineer (SDE-1)',
            'student_name': 'Vikram Patel',
            'student_email': 'student@cbs.edu',
            'student_phone': '9876543210',
            'cgpa': 8.85,
            'branch': 'Computer Science & Engineering',
            'status': 'Interview',
            'student_response': 'Attending',
            'response_at': now - datetime.timedelta(hours=6),
            'applied_at': now - datetime.timedelta(days=4),
            'is_multiple_applicant': True
        },
        {
            'student_id': vikram_uid,
            'job_id': msft_jid,
            'company_name': 'Microsoft',
            'job_role': 'Cloud Solutions Engineer',
            'student_name': 'Vikram Patel',
            'student_email': 'student@cbs.edu',
            'student_phone': '9876543210',
            'cgpa': 8.85,
            'branch': 'Computer Science & Engineering',
            'status': 'Shortlisted',
            'applied_at': now - datetime.timedelta(days=3),
            'is_multiple_applicant': True
        },
        {
            'student_id': vikram_uid,
            'job_id': amzn_jid,
            'company_name': 'Amazon',
            'job_role': 'Frontend Engineer (SDE-1)',
            'student_name': 'Vikram Patel',
            'student_email': 'student@cbs.edu',
            'student_phone': '9876543210',
            'cgpa': 8.85,
            'branch': 'Computer Science & Engineering',
            'status': 'Applied',
            'applied_at': now - datetime.timedelta(days=1),
            'is_multiple_applicant': True
        },
        # Sneha Gupta
        {
            'student_id': sneha_uid,
            'job_id': google_jid,
            'company_name': 'Google India',
            'job_role': 'Software Development Engineer (SDE-1)',
            'student_name': 'Sneha Gupta',
            'student_email': 'sneha.gupta@cbs.edu',
            'student_phone': '9876543211',
            'cgpa': 9.20,
            'branch': 'Information Technology',
            'status': 'Selected',
            'applied_at': now - datetime.timedelta(days=5),
            'is_multiple_applicant': False
        },
        {
            'student_id': sneha_uid,
            'job_id': msft_jid,
            'company_name': 'Microsoft',
            'job_role': 'Cloud Solutions Engineer',
            'student_name': 'Sneha Gupta',
            'student_email': 'sneha.gupta@cbs.edu',
            'student_phone': '9876543211',
            'cgpa': 9.20,
            'branch': 'Information Technology',
            'status': 'Shortlisted',
            'applied_at': now - datetime.timedelta(days=4),
            'is_multiple_applicant': False
        },
        # Arjun Nair
        {
            'student_id': arjun_uid,
            'job_id': tcs_jid,
            'company_name': 'Tata Consultancy Services',
            'job_role': 'Digital Systems Engineer',
            'student_name': 'Arjun Nair',
            'student_email': 'arjun.nair@cbs.edu',
            'student_phone': '9876543212',
            'cgpa': 7.80,
            'branch': 'Electronics & Communication',
            'status': 'Applied',
            'applied_at': now - datetime.timedelta(days=2),
            'is_multiple_applicant': False
        },
        # Priya Sharma
        {
            'student_id': priya_uid,
            'job_id': amzn_jid,
            'company_name': 'Amazon',
            'job_role': 'Frontend Engineer (SDE-1)',
            'student_name': 'Priya Sharma',
            'student_email': 'priya.sharma@cbs.edu',
            'student_phone': '9876543213',
            'cgpa': 8.45,
            'branch': 'Computer Science & Engineering',
            'status': 'Interview',
            'student_response': 'Attending',
            'response_at': now - datetime.timedelta(hours=4),
            'applied_at': now - datetime.timedelta(days=3),
            'is_multiple_applicant': True
        },
        {
            'student_id': priya_uid,
            'job_id': zomato_jid,
            'company_name': 'Zomato',
            'job_role': 'Product Engineering Intern (PPO)',
            'student_name': 'Priya Sharma',
            'student_email': 'priya.sharma@cbs.edu',
            'student_phone': '9876543213',
            'cgpa': 8.45,
            'branch': 'Computer Science & Engineering',
            'status': 'Selected',
            'applied_at': now - datetime.timedelta(days=1),
            'is_multiple_applicant': True
        }
    ]

    db.applications.insert_many(applications_data)

    # 5. ANNOUNCEMENTS
    print("Creating campus announcements...")
    announcements_data = [
        {
            'title': 'Campus Placement Season 2026-27 Inauguration',
            'content': 'Welcome final-year students! The Chetan Business School 3i-cell (Industry-Institute-Interaction) officially kicks off the 2026 campus recruitment drives. Please review your profiles, ensure all 10th, 12th, and UG marks are up to date, and keep your resumes refreshed. Premium tech giants including Google, Microsoft, and Amazon are scheduled to visit early this semester.',
            'category': 'General',
            'priority': 'high',
            'created_by': admin_user['email'],
            'created_by_id': admin_id,
            'author_role': 'super_admin',
            'status': 'published',
            'target_all_students': True,
            'attachment_id': None,
            'external_url': '',
            'created_at': now - datetime.timedelta(days=7),
            'updated_at': now - datetime.timedelta(days=7),
            'published_at': now - datetime.timedelta(days=7),
            'expires_at': now + datetime.timedelta(days=60)
        },
        {
            'title': 'Mandatory Mock Technical Interviews with FAANG Alumni',
            'content': 'In preparation for upcoming coding tests and system design rounds, the 3i-cell is hosting 1-on-1 mock interviews on Saturday and Sunday. Slots will be allocated on a first-come, first-served basis. Come prepared with 2 hard copies of your resume and a working laptop with webcam.',
            'category': 'Workshop',
            'priority': 'urgent',
            'created_by': faculty_user['email'],
            'created_by_id': faculty_id,
            'author_role': 'faculty',
            'status': 'published',
            'target_all_students': True,
            'attachment_id': None,
            'external_url': '',
            'created_at': now - datetime.timedelta(days=3),
            'updated_at': now - datetime.timedelta(days=3),
            'published_at': now - datetime.timedelta(days=3),
            'expires_at': now + datetime.timedelta(days=10)
        },
        {
            'title': 'Deloitte USI Tech Risk Drive Registration Closing Soon',
            'content': 'Eligible branches (CSE, IT, ECE) with CGPA >= 7.0 must confirm their application by Friday 5:00 PM. Late submissions will strictly not be entertained as student rosters will be finalized for the online proctored test.',
            'category': 'Drive Alert',
            'priority': 'normal',
            'created_by': faculty_user['email'],
            'created_by_id': faculty_id,
            'author_role': 'faculty',
            'status': 'published',
            'target_all_students': True,
            'attachment_id': None,
            'external_url': '',
            'created_at': now - datetime.timedelta(days=1),
            'updated_at': now - datetime.timedelta(days=1),
            'published_at': now - datetime.timedelta(days=1),
            'expires_at': now + datetime.timedelta(days=5)
        }
    ]

    db.announcements.insert_many(announcements_data)

    # 6. DYNAMIC FORMS & RESPONSES
    print("Creating survey forms and sample submissions...")
    form_id = ObjectId()
    sample_form = {
        '_id': form_id,
        'title': 'Placement Domain & Location Preference Survey 2026',
        'description': 'Please share your preferred job roles, target locations, and domain interests to help the 3i-cell curate tailored company invitations.',
        'fields': [
            {
                'name': 'preferred_domain',
                'label': 'Primary Domain Preference',
                'type': 'select',
                'required': True,
                'options': ['Software Development & Engineering', 'Cloud & DevOps', 'Data Analytics & AI', 'Cybersecurity', 'Core Engineering']
            },
            {
                'name': 'preferred_cities',
                'label': 'Preferred Work Cities',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g. Bangalore, Hyderabad, Pune'
            },
            {
                'name': 'higher_studies',
                'label': 'Do you plan to pursue Higher Studies (GATE / CAT / MS)?',
                'type': 'radio',
                'required': True,
                'options': ['No, immediate full-time job only', 'Yes, after 1-2 years of industry experience', 'Yes, immediate masters']
            },
            {
                'name': 'certifications',
                'label': 'Industry Certifications (AWS, GCP, Azure, Oracle, etc.)',
                'type': 'textarea',
                'required': False,
                'placeholder': 'List any active certifications or course credentials'
            }
        ],
        'created_by': admin_id,
        'created_at': now - datetime.timedelta(days=10),
        'is_active': True
    }
    db.forms.insert_one(sample_form)

    # Responses from students
    form_responses = [
        {
            'form_id': form_id,
            'student_id': vikram_uid,
            'student_name': 'Vikram Patel',
            'student_email': 'student@cbs.edu',
            'submitted_at': now - datetime.timedelta(days=8),
            'responses': {
                'preferred_domain': 'Software Development & Engineering',
                'preferred_cities': 'Bangalore, Hyderabad',
                'higher_studies': 'No, immediate full-time job only',
                'certifications': 'AWS Certified Cloud Practitioner, Meta Front-End Developer Professional'
            }
        },
        {
            'form_id': form_id,
            'student_id': sneha_uid,
            'student_name': 'Sneha Gupta',
            'student_email': 'sneha.gupta@cbs.edu',
            'submitted_at': now - datetime.timedelta(days=7),
            'responses': {
                'preferred_domain': 'Cloud & DevOps',
                'preferred_cities': 'Bangalore, Pune',
                'higher_studies': 'Yes, after 1-2 years of industry experience',
                'certifications': 'AWS Solutions Architect Associate, Certified Kubernetes Application Developer (CKAD)'
            }
        }
    ]
    db.form_responses.insert_many(form_responses)

    # 7. NOTIFICATIONS
    print("Creating student notifications...")
    notifications = [
        {
            'user_id': vikram_uid,
            'title': '🎉 Shortlisted for Google India',
            'message': 'Congratulations! You have been shortlisted for the technical interview round at Google India.',
            'link': '/student/applications',
            'is_read': False,
            'created_at': now - datetime.timedelta(hours=8),
            'type': 'application_status'
        },
        {
            'user_id': vikram_uid,
            'title': '🎯 New Job Posted: Microsoft',
            'message': 'Microsoft has posted Cloud Solutions Engineer. You meet all eligibility criteria!',
            'link': '/student/jobs',
            'is_read': False,
            'created_at': now - datetime.timedelta(days=1),
            'type': 'job_posting'
        },
        {
            'user_id': vikram_uid,
            'title': '🚨 Mandatory Mock Interview Session',
            'message': 'Mock interviews with alumni scheduled for this weekend. Check announcements for slot booking.',
            'link': '/student/announcements',
            'is_read': True,
            'created_at': now - datetime.timedelta(days=2),
            'type': 'announcement'
        },
        {
            'user_id': sneha_uid,
            'title': '🏆 Offer Received: Google India!',
            'message': 'Superb news! You have been Selected for Software Development Engineer at Google India!',
            'link': '/student/applications',
            'is_read': False,
            'created_at': now - datetime.timedelta(hours=3),
            'type': 'application_status'
        },
        {
            'user_id': priya_uid,
            'title': '🏆 Selected: Zomato Product Engineering',
            'message': 'Congratulations! You have been selected for the Product Engineering Internship at Zomato!',
            'link': '/student/applications',
            'is_read': False,
            'created_at': now - datetime.timedelta(hours=2),
            'type': 'application_status'
        }
    ]
    db.notifications.insert_many(notifications)

    # 8. LOGIN AUDIT LOGS
    print("Creating login history records...")
    login_logs = [
        {
            'user_id': admin_id,
            'email': 'admin@cbs.edu',
            'role': 'admin',
            'login_time': now - datetime.timedelta(hours=1),
            'ip_address': '127.0.0.1'
        },
        {
            'user_id': vikram_uid,
            'email': 'student@cbs.edu',
            'role': 'student',
            'login_time': now - datetime.timedelta(minutes=15),
            'ip_address': '127.0.0.1'
        },
        {
            'user_id': sneha_uid,
            'email': 'sneha.gupta@cbs.edu',
            'role': 'student',
            'login_time': now - datetime.timedelta(hours=3),
            'ip_address': '192.168.1.15'
        }
    ]
    db.login_logs.insert_many(login_logs)

    print("\n✅ SEEDING COMPLETE!")
    print("---------------------------------------------------------")
    print("Demo Admin Credentials:")
    print("   Super Admin: admin@cbs.edu  /  Admin@123")
    print("   Faculty:     faculty@cbs.edu /  Faculty@123")
    print("\nDemo Student Credentials:")
    print("   Student:     student@cbs.edu /  Student@123  (Vikram Patel, CGPA 8.85)")
    print("   Student:     sneha.gupta@cbs.edu / Student@123 (Sneha Gupta, CGPA 9.20)")
    print("   Student:     priya.sharma@cbs.edu / Student@123 (Priya Sharma, CGPA 8.45)")
    print("   Student:     arjun.nair@cbs.edu / Student@123 (Arjun Nair, CGPA 7.80)")
    print("   Pending:     rohit.kumar@cbs.edu / Student@123 (Pending approval demo)")
    print("---------------------------------------------------------")

if __name__ == '__main__':
    seed_all()
