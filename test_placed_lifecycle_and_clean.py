"""
Automated Comprehensive Verification Suite:
1. Pool Campus Complete Removal Verification
2. Placed Student 2-Day Auto-Exit Lifecycle Verification
3. Student Voluntary Placement Exit Verification
4. Super Admin / Admin Manual Exit and Reinstatement
5. Student Rejection Stage Tracking Continuity
"""
import unittest
import datetime
from bson import ObjectId
from app import (
    app, db, users_collection, students_collection, jobs_collection, 
    applications_collection, notifications_collection,
    check_and_process_placed_student_exits
)

class TestPlacedLifecycleAndClean(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

        # Find or create admin and student
        cls.admin_user = users_collection.find_one({'role': 'admin'})
        cls.student_user = users_collection.find_one({'email': 'student@cbs.edu'})
        if not cls.student_user:
            cls.student_user = users_collection.find_one({'role': 'student'})

        cls.student_id = cls.student_user['_id']
        cls.admin_id = cls.admin_user['_id']

        # Ensure student doc exists
        cls.student_doc = students_collection.find_one({'user_id': cls.student_id})
        if not cls.student_doc:
            students_collection.insert_one({
                'user_id': cls.student_id,
                'name': 'Test Student',
                'cgpa': 8.5,
                'branch': 'CSE',
                'placement_status': 'Active',
                'is_placed': False,
                'is_active_candidate': True
            })
            cls.student_doc = students_collection.find_one({'user_id': cls.student_id})

    def setUp(self):
        # Reset student state before each test
        students_collection.update_one(
            {'user_id': self.student_id},
            {'$set': {
                'placement_status': 'Active',
                'is_placed': False,
                'is_active_candidate': True,
                'auto_exited': False,
                'exit_completed_at': None,
                'exit_deadline': None,
                'exit_reason': None
            }}
        )

    def test_01_pool_campus_removed_from_job_creation(self):
        """Verify that jobs are created cleanly as regular drives with no pool campus fields."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.admin_id)
            sess['email'] = self.admin_user['email']
            sess['role'] = 'admin'
            sess['admin_level'] = 'super_admin'

        resp = self.client.post('/admin/jobs/add', data={
            'company': 'Google India',
            'role': 'Cloud Solutions Engineer',
            'description': 'Campus recruitment for Cloud Solutions role.',
            'package': '18.0 LPA',
            'location': 'Bengaluru',
            'employment_type': 'Full-time',
            'min_cgpa': '7.0',
            'drive_date': '2026-12-20',
            'expires_at': '2026-12-15',
            'action': 'publish'
        }, follow_redirects=True)

        self.assertEqual(resp.status_code, 200)
        job = jobs_collection.find_one({'company_name': 'Google India'})
        self.assertIsNotNone(job)
        self.assertNotIn('pool_security_code', job)
        self.assertNotIn('pool_host_college', job)
        print("\n[PASS] Test 1: Recruitment drive created cleanly without pool campus overhead.")

    def test_02_student_apply_clean_without_passcode(self):
        """Verify students can apply directly to eligible drives without requiring a passcode."""
        job = jobs_collection.find_one({'company_name': 'Google India'})
        self.assertIsNotNone(job)

        applications_collection.delete_many({'student_id': self.student_id, 'job_id': job['_id']})

        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.student_id)
            sess['email'] = self.student_user['email']
            sess['role'] = 'student'

        resp = self.client.post(f'/student/jobs/{job["_id"]}/apply', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        app_doc = applications_collection.find_one({'student_id': self.student_id, 'job_id': job['_id']})
        self.assertIsNotNone(app_doc)
        self.assertEqual(app_doc.get('status'), 'Applied')
        print("[PASS] Test 2: Student applied directly without passcode blocks or prompts.")

    def test_03_admin_marks_selected_initializes_48h_exit_window(self):
        """When an admin sets status to 'Selected', 48-hour exit deadline and Placed_Pending_Exit are initialized."""
        job = jobs_collection.find_one({'company_name': 'Google India'})
        app_doc = applications_collection.find_one({'student_id': self.student_id, 'job_id': job['_id']})
        self.assertIsNotNone(app_doc)

        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.admin_id)
            sess['email'] = self.admin_user['email']
            sess['role'] = 'admin'
            sess['admin_level'] = 'super_admin'

        resp = self.client.post(f'/admin/applications/update/{app_doc["_id"]}', data={
            'status': 'Selected'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Check updated application
        updated_app = applications_collection.find_one({'_id': app_doc['_id']})
        self.assertEqual(updated_app['status'], 'Selected')
        self.assertIsNotNone(updated_app.get('selected_at'))
        self.assertIsNotNone(updated_app.get('exit_deadline'))

        # Check student profile
        student = students_collection.find_one({'user_id': self.student_id})
        self.assertEqual(student.get('placement_status'), 'Placed_Pending_Exit')
        self.assertTrue(student.get('is_placed'))
        self.assertEqual(student.get('placed_company'), 'Google India')
        self.assertFalse(student.get('auto_exited'))

        # Check notification
        notif = notifications_collection.find_one({'user_id': self.student_id, 'type': 'placed_offer'})
        self.assertIsNotNone(notif)
        self.assertIn('Congratulations', notif.get('title', ''))
        print("[PASS] Test 3: Marked 'Selected' successfully initialized Placed_Pending_Exit and 48-hour window.")

    def test_04_student_voluntary_placement_exit(self):
        """Student acknowledges offer and voluntarily exits active portal."""
        # Setup student as Placed_Pending_Exit
        students_collection.update_one(
            {'user_id': self.student_id},
            {'$set': {
                'placement_status': 'Placed_Pending_Exit',
                'placed_company': 'Google India',
                'placed_role': 'Cloud Solutions Engineer'
            }}
        )

        # Create a dummy pending application to another company
        other_job = jobs_collection.insert_one({
            'company_name': 'Secondary Corp',
            'role': 'Developer',
            'package': '12 LPA',
            'status': 'published'
        })
        applications_collection.insert_one({
            'student_id': self.student_id,
            'job_id': other_job.inserted_id,
            'company_name': 'Secondary Corp',
            'status': 'Interview'
        })

        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.student_id)
            sess['email'] = self.student_user['email']
            sess['role'] = 'student'

        resp = self.client.post('/student/placement-exit', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        student = students_collection.find_one({'user_id': self.student_id})
        self.assertEqual(student.get('placement_status'), 'Placed_Archived')
        self.assertFalse(student.get('is_active_candidate'))
        self.assertFalse(student.get('auto_exited'))
        self.assertIsNotNone(student.get('exit_completed_at'))

        # Verify other application was automatically withdrawn
        other_app = applications_collection.find_one({'student_id': self.student_id, 'job_id': other_job.inserted_id})
        self.assertEqual(other_app.get('status'), 'Auto_Withdrawn')
        print("[PASS] Test 4: Student voluntary exit confirmed; profile archived and other applications withdrawn.")

    def test_05_automated_2day_exit_lifecycle(self):
        """Automated 48-hour background transition for candidate who did not manually exit."""
        past_time = datetime.datetime.now() - datetime.timedelta(days=2, hours=1)
        students_collection.update_one(
            {'user_id': self.student_id},
            {'$set': {
                'placement_status': 'Placed_Pending_Exit',
                'is_placed': True,
                'placed_company': 'Microsoft',
                'placed_role': 'Software Development Engineer',
                'placed_at': past_time,
                'exit_deadline': past_time + datetime.timedelta(days=2), # In the past
                'auto_exited': False,
                'is_active_candidate': True
            }}
        )

        # Add an active application to test auto-withdrawal
        dummy_job = jobs_collection.insert_one({
            'company_name': 'Tertiary Tech',
            'role': 'Analyst',
            'status': 'published'
        })
        applications_collection.insert_one({
            'student_id': self.student_id,
            'job_id': dummy_job.inserted_id,
            'company_name': 'Tertiary Tech',
            'status': 'Shortlisted'
        })

        # Run automated lifecycle helper
        processed = check_and_process_placed_student_exits()
        self.assertGreaterEqual(processed, 1)

        student = students_collection.find_one({'user_id': self.student_id})
        self.assertEqual(student.get('placement_status'), 'Placed_Archived')
        self.assertTrue(student.get('auto_exited'))
        self.assertFalse(student.get('is_active_candidate'))

        # Verify auto-withdrawn
        app_check = applications_collection.find_one({'student_id': self.student_id, 'job_id': dummy_job.inserted_id})
        self.assertEqual(app_check.get('status'), 'Auto_Withdrawn')
        print("[PASS] Test 5: Automated 2-day exit trigger transitioned expired student to Placed_Archived.")

    def test_06_admin_manual_exit_and_reinstatement(self):
        """Admin can manually trigger placement exit, and reinstate if needed."""
        # 1. Admin manual exit
        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.admin_id)
            sess['email'] = self.admin_user['email']
            sess['role'] = 'admin'
            sess['admin_level'] = 'super_admin'

        students_collection.update_one(
            {'user_id': self.student_id},
            {'$set': {'placement_status': 'Placed_Pending_Exit', 'placed_company': 'Oracle'}}
        )

        resp = self.client.post(f'/admin/students/{self.student_id}/placement-exit', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        student = students_collection.find_one({'user_id': self.student_id})
        self.assertEqual(student.get('placement_status'), 'Placed_Archived')
        self.assertFalse(student.get('is_active_candidate'))

        # 2. Admin reinstatement
        resp = self.client.post(f'/admin/students/{self.student_id}/placement-reinstate', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        student = students_collection.find_one({'user_id': self.student_id})
        self.assertEqual(student.get('placement_status'), 'Active')
        self.assertTrue(student.get('is_active_candidate'))
        self.assertFalse(student.get('is_placed'))
        print("[PASS] Test 6: Admin manual exit and reinstatement verified.")

    def test_07_placed_student_application_policy_block(self):
        """Archived placed student cannot apply to new jobs."""
        students_collection.update_one(
            {'user_id': self.student_id},
            {'$set': {'placement_status': 'Placed_Archived', 'is_active_candidate': False}}
        )

        new_job = jobs_collection.insert_one({
            'company_name': 'Test New Job Corp',
            'role': 'Engineer',
            'package': '9 LPA',
            'min_cgpa': '6.0',
            'status': 'published'
        })

        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.student_id)
            sess['email'] = self.student_user['email']
            sess['role'] = 'student'

        resp = self.client.post(f'/student/jobs/{new_job.inserted_id}/apply', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Ensure no application was created
        app_doc = applications_collection.find_one({'student_id': self.student_id, 'job_id': new_job.inserted_id})
        self.assertIsNone(app_doc)
        print("[PASS] Test 7: Placed & corporate transitioned student blocked from applying to new drives.")

    def test_08_rejection_stage_tracking_continuity(self):
        """Verify rejection stage tracking remains completely functional."""
        job = jobs_collection.find_one({'company_name': 'Google India'})
        # Create an application
        app_res = applications_collection.insert_one({
            'student_id': self.student_id,
            'job_id': job['_id'],
            'company_name': 'Google India',
            'status': 'Applied'
        })

        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.admin_id)
            sess['email'] = self.admin_user['email']
            sess['role'] = 'admin'
            sess['admin_level'] = 'super_admin'

        resp = self.client.post(f'/admin/applications/update/{app_res.inserted_id}', data={
            'status': 'Rejected',
            'rejection_stage': 'Technical Interview Round 1',
            'rejection_reason': 'Needs stronger grasp of system design patterns'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        app_doc = applications_collection.find_one({'_id': app_res.inserted_id})
        self.assertEqual(app_doc.get('status'), 'Rejected')
        self.assertEqual(app_doc.get('rejection_stage'), 'Technical Interview Round 1')
        self.assertEqual(app_doc.get('rejection_reason'), 'Needs stronger grasp of system design patterns')
        print("[PASS] Test 8: Rejection stage tracking verified intact and accurate.")

if __name__ == '__main__':
    unittest.main()
