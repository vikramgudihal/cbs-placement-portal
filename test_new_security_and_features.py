import unittest
import io
import datetime
from bson import ObjectId
from app import (
    app, users_collection, students_collection, jobs_collection, 
    applications_collection, calculate_student_ats_score, validate_and_store_resume
)

class TestNewSecurityAndFeatures(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_01_weak_password_rejection_in_signup(self):
        """Weak passwords should be rejected on signup."""
        res = self.client.post('/signup', data={
            'role': 'student',
            'name': 'Test Weak Student',
            'email': 'weak.student.test@gmail.com',
            'roll_no': 'P02DR25S999001',
            'password': '123'  # Too short & weak
        }, follow_redirects=True)
        self.assertIn(b'Security Requirement: Password must be at least 8 characters long', res.data)
        
        # Another weak password (only letters, no numbers)
        res2 = self.client.post('/signup', data={
            'role': 'student',
            'name': 'Test Weak Student 2',
            'email': 'weak2.student.test@gmail.com',
            'roll_no': 'P02DR25S999002',
            'password': 'passwordonly'
        }, follow_redirects=True)
        self.assertIn(b'Security Requirement: Password is too weak', res2.data)
        print("[PASS] Weak password rejection verified on signup.")

    def test_02_student_signup_approval_gate(self):
        """New student signup should create an unapproved account and block login until approved."""
        email = 'gate.student.test@gmail.com'
        roll_no = 'P02DR25S999003'
        users_collection.delete_many({'email': email})
        students_collection.delete_many({'student_id': roll_no})

        # Sign up with strong password
        signup_res = self.client.post('/signup', data={
            'role': 'student',
            'name': 'Gate Student Test',
            'email': email,
            'roll_no': roll_no,
            'password': 'CBS#SecurePass9824!'
        }, follow_redirects=True)
        self.assertIn(b'Account registration submitted', signup_res.data)

        # Attempt to login without approval
        login_res = self.client.post('/login', data={
            'email': email,
            'password': 'CBS#SecurePass9824!',
            'role': 'student'
        }, follow_redirects=True)
        self.assertIn(b'Awaiting Main Super Admin Approval', login_res.data)
        print("[PASS] Student unapproved registration waiting gate verified.")

    def test_03_brute_force_5_attempts_lockout(self):
        """5 failed login attempts should trigger a 5-minute security lockout."""
        email = 'vikram.patel.mca@gmail.com'
        # Reset lockout if any
        users_collection.update_one({'email': email}, {'$unset': {'failed_login_attempts': '', 'lockout_until': ''}})

        # Fail 4 times
        for i in range(4):
            res = self.client.post('/login', data={'email': email, 'password': 'WrongPassword123'}, follow_redirects=True)
            self.assertIn(b'Invalid email or password', res.data)

        # 5th failure -> Lockout triggered
        res5 = self.client.post('/login', data={'email': email, 'password': 'WrongPassword123'}, follow_redirects=True)
        self.assertIn(b'Security Alert: 5 consecutive failed login attempts detected', res5.data)

        # 6th attempt (even with right password) must be blocked during the 5-minute window
        res6 = self.client.post('/login', data={'email': email, 'password': 'Student@123'}, follow_redirects=True)
        self.assertIn(b'Security Alert: Account temporarily locked', res6.data)

        # Clean up lockout
        users_collection.update_one({'email': email}, {'$unset': {'failed_login_attempts': '', 'lockout_until': ''}})
        print("[PASS] Brute force 5-attempt / 5-minute lockout verified.")

    def test_04_dynamic_ats_score_calculation(self):
        """Empty student profile should have 0 or low score; complete should have 80%+."""
        empty_student = {'name': 'New Student'}
        res_empty = calculate_student_ats_score(empty_student)
        self.assertLess(res_empty['score'], 50)
        self.assertEqual(res_empty['badge_class'], 'incomplete')

        complete_student = {
            'name': 'Vikram Patel',
            'student_id': 'P02DR25S126001',
            'phone': '9876543210',
            'personal_email': 'vikram.patel.mca@gmail.com',
            'cgpa': 8.85,
            'academic': {
                'tenth': {'score': 88.5},
                'twelfth': {'score': 86.0},
                'ug': {'score': 8.85}
            },
            'skills': ['Python', 'SQL', 'Flask', 'MongoDB'],
            'projects': 'Built Enterprise Campus Placement System with automated pipeline tracking.',
            'resume_file_id': ObjectId()
        }
        res_comp = calculate_student_ats_score(complete_student)
        self.assertGreaterEqual(res_comp['score'], 80)
        self.assertEqual(res_comp['badge_class'], 'optimized')
        print(f"[PASS] Dynamic ATS Score verified (Empty: {res_empty['score']}%, Complete: {res_comp['score']}%).")

    def test_05_secure_resume_validation(self):
        """Reject non-PDF or disguised files; accept genuine PDF <= 5MB."""
        test_uid = ObjectId()

        # Reject non-pdf extension
        fake_txt = io.BytesIO(b'plain text')
        fake_txt.filename = 'malicious.exe'
        ok, msg = validate_and_store_resume(fake_txt, test_uid)
        self.assertFalse(ok)
        self.assertIn('Only authentic PDF', msg)

        # Reject fake pdf header (extension .pdf but content is not PDF)
        fake_header = io.BytesIO(b'NOT A REAL PDF FILE HEADER')
        fake_header.filename = 'disguised.pdf'
        ok, msg = validate_and_store_resume(fake_header, test_uid)
        self.assertFalse(ok)
        self.assertIn('File integrity violation', msg)

        # Reject oversized > 5MB
        oversized = io.BytesIO(b'%PDF-1.4 ' + b'A' * (6 * 1024 * 1024))
        oversized.filename = 'large.pdf'
        ok, msg = validate_and_store_resume(oversized, test_uid)
        self.assertFalse(ok)
        self.assertIn('File size too large', msg)

        # Accept genuine small PDF
        valid_pdf = io.BytesIO(b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF')
        valid_pdf.filename = 'student_resume.pdf'
        ok, file_id = validate_and_store_resume(valid_pdf, test_uid)
        self.assertTrue(ok)
        self.assertIsInstance(file_id, ObjectId)
        print("[PASS] Secure resume upload validation (extension, magic bytes, size limit) verified.")

    def test_06_job_custom_requirements_and_auto_sync(self):
        """Jobs can require custom fields and applying auto-syncs them to student profile."""
        # 1. Create a drive with custom requirements
        job_doc = {
            'company_name': 'TestTech Global',
            'role': 'Full Stack Developer',
            'description': 'Campus recruitment drive requiring GitHub and preferred city.',
            'package': '9 LPA',
            'location': 'Bangalore',
            'min_cgpa': 7.0,
            'status': 'published',
            'custom_requirements': {
                'require_github': True,
                'require_preferred_city': True,
                'custom_question': 'What is your primary web framework?'
            },
            'created_at': datetime.datetime.now()
        }
        job_id = jobs_collection.insert_one(job_doc).inserted_id

        # 2. Get student user
        user = users_collection.find_one({'email': 'vikram.patel.mca@gmail.com'})
        student = students_collection.find_one({'user_id': user['_id']})

        # Remove any existing test application
        applications_collection.delete_many({'student_id': user['_id'], 'job_id': job_id})

        # Login as student
        with self.client.session_transaction() as sess:
            sess['user_id'] = str(user['_id'])
            sess['role'] = 'student'
            sess['email'] = user['email']

        # Apply without required question -> should reject
        res_fail = self.client.post(f'/student/jobs/{job_id}/apply', data={
            'github_url': 'https://github.com/vikram-test',
            'preferred_location': 'Bangalore'
            # custom_answer omitted
        }, follow_redirects=True)
        self.assertIn(b'Please answer the recruiter question', res_fail.data)

        # Apply with all required answers
        res_success = self.client.post(f'/student/jobs/{job_id}/apply', data={
            'github_url': 'https://github.com/vikram-cbs',
            'preferred_location': 'Bangalore DC',
            'custom_answer': 'Flask and React with MongoDB'
        }, follow_redirects=True)
        self.assertIn(b'Application submitted successfully', res_success.data)

        # Verify application record contains custom responses
        app_rec = applications_collection.find_one({'student_id': user['_id'], 'job_id': job_id})
        self.assertIsNotNone(app_rec)
        self.assertEqual(app_rec['custom_responses']['github_url'], 'https://github.com/vikram-cbs')
        self.assertEqual(app_rec['custom_responses']['preferred_location'], 'Bangalore DC')
        self.assertEqual(app_rec['custom_responses']['custom_answer'], 'Flask and React with MongoDB')

        # Verify student profile was automatically updated
        updated_student = students_collection.find_one({'user_id': user['_id']})
        self.assertEqual(updated_student.get('github_url'), 'https://github.com/vikram-cbs')
        self.assertEqual(updated_student.get('preferred_location'), 'Bangalore DC')
        print("[PASS] Drive custom requirements, applicant validation, and student profile auto-sync verified.")

        # Cleanup test drive
        jobs_collection.delete_one({'_id': job_id})
        applications_collection.delete_many({'job_id': job_id})

    def test_07_mandatory_student_onboarding_lockdown(self):
        """Approved student with profile_completed=False must be redirected to /student/complete-profile."""
        email = 'onboarding.student.test@gmail.com'
        users_collection.delete_many({'email': email})
        uid = users_collection.insert_one({
            'email': email,
            'role': 'student',
            'is_approved': True,
            'profile_completed': False
        }).inserted_id

        with self.client.session_transaction() as sess:
            sess['user_id'] = str(uid)
            sess['role'] = 'student'
            sess['profile_completed'] = False

        # Attempt to access student dashboard -> should redirect to complete-profile
        res = self.client.get('/student/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/student/complete-profile', res.headers.get('Location'))

        # Attempt to access student jobs -> should redirect to complete-profile
        res_jobs = self.client.get('/student/jobs', follow_redirects=False)
        self.assertEqual(res_jobs.status_code, 302)
        self.assertIn('/student/complete-profile', res_jobs.headers.get('Location'))

        # Accessing complete-profile is allowed (200)
        res_profile = self.client.get('/student/complete-profile')
        self.assertEqual(res_profile.status_code, 200)
        self.assertIn(b'Auto-Fill from Resume', res_profile.data)
        print("[PASS] Mandatory student onboarding lockdown verified (zero bypass).")

        users_collection.delete_one({'_id': uid})

    def test_08_resume_parser_api(self):
        """Resume parser endpoint should validate file type and parse PDF."""
        user = users_collection.find_one({'email': 'vikram.patel.mca@gmail.com'})
        with self.client.session_transaction() as sess:
            sess['user_id'] = str(user['_id'])
            sess['role'] = 'student'

        # Reject non-PDF
        res_txt = self.client.post('/api/student/parse-resume', data={
            'resume': (io.BytesIO(b'Some random text'), 'resume.txt')
        })
        self.assertEqual(res_txt.status_code, 400)
        self.assertIn('Only PDF', res_txt.get_json().get('error', ''))

        # Reject corrupted/fake PDF (no %PDF- header)
        res_fake = self.client.post('/api/student/parse-resume', data={
            'resume': (io.BytesIO(b'NOT_A_REAL_PDF_CONTENT'), 'resume.pdf')
        })
        self.assertEqual(res_fake.status_code, 400)
        self.assertIn('Corrupted or non-standard', res_fake.get_json().get('error', ''))
        print("[PASS] Resume parser API security validation verified.")

    def test_09_tailored_drive_resume_application(self):
        """Student can submit a tailored custom resume specifically for a job application."""
        user = users_collection.find_one({'email': 'vikram.patel.mca@gmail.com'})
        student = students_collection.find_one({'user_id': user['_id']})

        # Create dummy job
        job_id = jobs_collection.insert_one({
            'company_name': 'Custom CV Tech Corp',
            'role': 'Full Stack Developer',
            'package': '12 LPA',
            'status': 'published',
            'branch': ['MCA'],
            'cgpa_criteria': 6.0,
            'active_backlogs_allowed': 0
        }).inserted_id

        applications_collection.delete_many({'student_id': user['_id'], 'job_id': job_id})

        with self.client.session_transaction() as sess:
            sess['user_id'] = str(user['_id'])
            sess['role'] = 'student'
            sess['profile_completed'] = True

        custom_pdf = io.BytesIO(b'%PDF-1.4 Tailored Resume for Custom CV Tech Corp...')
        res = self.client.post(f'/student/jobs/{job_id}/apply', data={
            'resume_choice': 'custom',
            'custom_resume': (custom_pdf, 'tailored_google_cv.pdf')
        }, follow_redirects=True)

        self.assertIn(b'Application submitted successfully', res.data)

        app_rec = applications_collection.find_one({'student_id': user['_id'], 'job_id': job_id})
        self.assertIsNotNone(app_rec)
        self.assertTrue(app_rec.get('is_custom_resume'))
        self.assertEqual(app_rec.get('custom_resume_filename'), 'tailored_google_cv.pdf')
        self.assertIsNotNone(app_rec.get('resume_file_id'))
        print("[PASS] Tailored drive-specific resume upload and storage verified.")

        # Cleanup
        jobs_collection.delete_one({'_id': job_id})
        applications_collection.delete_many({'job_id': job_id})

if __name__ == '__main__':
    unittest.main()
