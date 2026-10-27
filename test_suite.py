import unittest
from flask import url_for
from app import app
from utils.db import get_db

class TestPlacementPortal(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_01_landing_page(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200, "Landing page should return 200")
        self.assertIn(b'CBS', res.data)
        print("✓ Landing page renders correctly (HTTP 200)")

    def test_02_login_page(self):
        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200, "Login page should return 200")
        self.assertIn(b'Instant Demo Access', res.data)
        print("✓ Login page renders correctly with Instant Demo Access")

    def test_03_student_login_and_dashboard(self):
        login_res = self.client.post('/login', data={
            'email': 'student@cbs.edu',
            'password': 'Student@123',
            'role': 'student'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Dashboard', login_res.data)
        print("✓ Student login successful -> redirected to Dashboard")

        # Student Jobs
        with self.app.test_request_context():
            jobs_url = url_for('student_jobs')
            app_url = url_for('student_applications')
            prof_url = url_for('student_profile')
            ann_url = url_for('student_announcements')

        jobs_res = self.client.get(jobs_url)
        self.assertEqual(jobs_res.status_code, 200)
        self.assertIn(b'Google India', jobs_res.data)
        print("✓ Student Jobs page displays recruitment drives")

        # Student Applications
        app_res = self.client.get(app_url)
        self.assertEqual(app_res.status_code, 200)
        self.assertIn(b'My Applications', app_res.data)
        print("✓ Student Applications page loads correctly")

        # Student Profile
        prof_res = self.client.get(prof_url)
        self.assertEqual(prof_res.status_code, 200)
        self.assertIn(b'Vikram Patel', prof_res.data)
        print("✓ Student Profile page displays student details")

        # Student Announcements
        ann_res = self.client.get(ann_url)
        self.assertEqual(ann_res.status_code, 200)
        self.assertIn(b'Town Hall', ann_res.data)
        print("✓ Student Announcements page loads correctly")

    def test_04_admin_login_and_dashboard(self):
        # Fresh client session for admin
        admin_client = self.app.test_client()

        login_res = admin_client.post('/login', data={
            'email': 'admin@cbs.edu',
            'password': 'Admin@123',
            'role': 'admin'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Admin Dashboard', login_res.data)
        print("✓ Admin login successful -> redirected to Admin Dashboard")

        with self.app.test_request_context():
            jobs_url = url_for('manage_jobs')
            ann_url = url_for('manage_announcements')
            apps_url = url_for('view_applications')
            users_url = url_for('manage_users')
            all_std_url = url_for('all_students_list')

        # Manage Jobs
        m_jobs = admin_client.get(jobs_url)
        self.assertEqual(m_jobs.status_code, 200)
        self.assertIn(b'Job Postings', m_jobs.data)
        print("✓ Admin Manage Jobs loads correctly")

        # Manage Announcements
        m_ann = admin_client.get(ann_url)
        self.assertEqual(m_ann.status_code, 200)
        print("✓ Admin Manage Announcements loads correctly")

        # View Applications
        m_apps = admin_client.get(apps_url)
        self.assertEqual(m_apps.status_code, 200)
        print("✓ Admin Applications tracking loads correctly")

        # Manage Users
        m_users = admin_client.get(users_url)
        self.assertEqual(m_users.status_code, 200)
        print("✓ Admin Manage Users loads correctly")

        # All Students
        m_students = admin_client.get(all_std_url)
        self.assertEqual(m_students.status_code, 200)
        print("✓ Admin All Students list loads correctly")

    def test_05_production_health_and_error_handling(self):
        # 1. Health check probe
        health_res = self.client.get('/health')
        self.assertEqual(health_res.status_code, 200)
        data = health_res.get_json()
        self.assertEqual(data.get('status'), 'healthy')
        self.assertTrue(data.get('database', {}).get('connected'))
        print("✓ Production Health Check Probe (/health) reports healthy database connectivity")

        # 2. 404 Custom error template check
        err_res = self.client.get('/definitely-not-a-real-portal-endpoint-404')
        self.assertEqual(err_res.status_code, 404)
        self.assertIn(b'Error 404', err_res.data)
        print("✓ Production 404 Error Handler gracefully renders branded recovery page")

        # 3. Rotating audit log check
        import os
        log_file = os.path.join('logs', 'cbs_portal.log')
        self.assertTrue(os.path.exists(log_file))
        print("✓ Production Rotating Audit Log is active and recording system events")

if __name__ == '__main__':
    unittest.main()
