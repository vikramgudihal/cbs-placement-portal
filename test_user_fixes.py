import io
import unittest
import PyPDF2
from utils.resume_parser import parse_resume

def create_sample_resume_pdf(text_content):
    """Helper to generate a minimal in-memory PDF for parser testing"""
    writer = PyPDF2.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    stream = io.BytesIO()
    writer.write(stream)
    stream.seek(0)
    return stream

class TestUserFixes(unittest.TestCase):
    def test_resume_parser_academics_and_skills(self):
        """Verify enhanced regex parsing extracts 10th, 12th, UG, PG, and skills"""
        sample_text = """
        VIKRAM GUDIHAL
        Email: vikram.gudihal@gmail.com | Phone: 9876543210 | USN: P02DR25S126001
        Chetan Business School, Hubli
        
        EDUCATION:
        Master of Computer Applications (MCA) - Chetan Business School, Karnatak University (2024 - 2026), CGPA: 7.77
        Bachelor of Computer Applications (BCA) - KUD (2021 - 2024), Aggregate: 8.2 CGPA
        Class XII / PUC (Science PCMB) - State PU Board (2021), Score: 84.5%
        Class X / SSLC - State Board (2019), Score: 88.0%
        
        TECHNICAL SKILLS:
        Python, Flask, JavaScript, SQL, MongoDB, React, HTML5, CSS3, Docker, Git, GitHub
        
        PROJECTS:
        Placement Cell Management System with Flask and MongoDB Atlas
        """
        
        from unittest.mock import patch
        with patch('utils.resume_parser.extract_text_from_pdf', return_value=sample_text):
            fake_stream = io.BytesIO(b"%PDF-1.4 dummy content")
            result = parse_resume(fake_stream)
            
            self.assertTrue(result['success'])
            data = result['data']
            
            self.assertEqual(data.get('email'), 'vikram.gudihal@gmail.com')
            self.assertEqual(data.get('phone'), '9876543210')
            self.assertEqual(data.get('student_id'), 'P02DR25S126001')
            self.assertEqual(data.get('degree'), 'MCA')
            self.assertEqual(data.get('branch'), 'MCA')
            
            # Academics Check
            self.assertIn('88', data.get('tenth_score', ''))
            self.assertEqual(data.get('tenth_board'), 'State Board')
            self.assertEqual(data.get('tenth_year'), '2019')
            
            self.assertIn('84.5', data.get('twelfth_score', ''))
            self.assertEqual(data.get('twelfth_board'), 'State PU Board')
            self.assertEqual(data.get('twelfth_year'), '2021')
            self.assertIn('Science', data.get('twelfth_stream', ''))
            
            self.assertEqual(data.get('ug_degree'), 'BCA')
            self.assertIn('7.77', data.get('cgpa', ''))
            self.assertEqual(data.get('pg_college'), 'Chetan Business School')
            
            # Skills Check
            self.assertIn('Python', data.get('skills', ''))
            self.assertIn('Flask', data.get('skills', ''))
            self.assertIn('SQL', data.get('skills', ''))
            self.assertIn('MongoDB', data.get('skills', ''))
            print("[PASS] Resume parser accurately extracts 10th, 12th, UG, PG, and skills.")

    def test_jobs_template_structure(self):
        """Verify jobs.html contains both Grid and List views and no broken unclosed scripts"""
        with open('templates/student/jobs.html', encoding='utf-8') as f:
            content = f.read()
            
        self.assertIn('id="drivesGridView"', content)
        self.assertIn('id="drivesListView"', content)
        self.assertIn('id="btnViewGrid"', content)
        self.assertIn('id="btnViewList"', content)
        self.assertIn('switchDrivesView', content)
        self.assertIn('id="applyCustomModal"', content)
        self.assertIn('Candidate Profile Linked', content)
        
        # Verify modal is NOT inside a <script> block
        parts = content.split('<div id="applyCustomModal"')
        self.assertEqual(len(parts), 2, "Modal should appear exactly once in HTML")
        before_modal = parts[0]
        # Count opened vs closed script tags before the modal
        open_scripts = before_modal.count('<script')
        close_scripts = before_modal.count('</script>')
        self.assertEqual(open_scripts, close_scripts, "All <script> tags before modal must be closed!")
        print("[PASS] jobs.html syntax verified: clean Grid/List views and proper modal DOM tree.")

    def test_offline_catchup_notification_markup(self):
        """Verify base.html contains offline-to-online catchup logic"""
        with open('templates/base.html', encoding='utf-8') as f:
            content = f.read()
            
        self.assertIn('offline-catchup-card', content)
        self.assertIn('triggerOfflineCatchupBanner', content)
        self.assertIn('While You Were Offline', content)
        self.assertIn('Processing...', content)
        print("[PASS] base.html offline-to-online notification catchup and instant button feedback verified.")

    def test_complete_profile_template_syntax_and_wizard(self):
        """Verify complete_profile.html has balanced script syntax, novalidate multi-step guard, and proper file bindings"""
        with open('templates/student/complete_profile.html', encoding='utf-8') as f:
            content = f.read()
            
        self.assertIn('novalidate', content, "Multi-step form must use novalidate so hidden steps do not block submission")
        self.assertIn('handleFormFinalSubmit', content)
        self.assertIn('handleResumeAutoFill', content)
        self.assertIn('proceedToStep', content)
        self.assertIn('jumpToStep', content)
        self.assertIn('applySmartAcademicSuggestions', content)
        
        # Check script block in complete_profile.html
        import re
        script_matches = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
        self.assertTrue(len(script_matches) > 0, "Script tag must exist in complete_profile.html")
        
        js_code = script_matches[-1]
        # Check matching braces in JS code (excluding strings/comments)
        open_curly = js_code.count('{')
        close_curly = js_code.count('}')
        self.assertEqual(open_curly, close_curly, f"JavaScript braces must be strictly balanced! Open: {open_curly}, Close: {close_curly}")
        print("[PASS] complete_profile.html script syntax and multi-step validation verified.")

    def test_back_navigation_across_portal(self):
        """Verify universal and page-level back buttons are present and correctly wired across all views"""
        # 1. Base template topbar & auth nav
        with open('templates/base.html', encoding='utf-8') as f:
            base_html = f.read()
        self.assertIn('universalTopbarBackBtn', base_html)
        self.assertIn('handleUniversalBack', base_html)
        self.assertIn('topbar-back-btn', base_html)

        # 2. Notifications page
        with open('templates/notifications.html', encoding='utf-8') as f:
            notif_html = f.read()
        self.assertIn('handleUniversalBack', notif_html)
        self.assertIn('btn-back', notif_html)

        # 3. Student Announcements / Town Hall
        with open('templates/student/announcements.html', encoding='utf-8') as f:
            ann_html = f.read()
        self.assertIn('student_dashboard', ann_html)
        self.assertIn('btn-back', ann_html)

        # 4. Auth pages: Login, Signup, Reset Password
        with open('templates/login.html', encoding='utf-8') as f:
            login_html = f.read()
        self.assertIn('btn-back', login_html)

        with open('templates/signup.html', encoding='utf-8') as f:
            signup_html = f.read()
        self.assertIn('btn-back', signup_html)

        with open('templates/reset_password.html', encoding='utf-8') as f:
            reset_html = f.read()
        self.assertIn('btn-back', reset_html)

        # 5. Error templates: 429 & 500
        with open('templates/errors/429.html', encoding='utf-8') as f:
            e429_html = f.read()
        self.assertIn('history.back()', e429_html)

        with open('templates/errors/500.html', encoding='utf-8') as f:
            e500_html = f.read()
        self.assertIn('history.back()', e500_html)

        # 6. Complete profile backwards step unblocking
        with open('templates/student/complete_profile.html', encoding='utf-8') as f:
            profile_html = f.read()
        self.assertIn('if (nextStep < currentActiveStep)', profile_html)
        self.assertIn('Back to Profile', profile_html)

        print("[PASS] Comprehensive back navigation verified across all portal templates.")

if __name__ == '__main__':
    unittest.main()
