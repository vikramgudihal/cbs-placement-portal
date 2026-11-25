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

if __name__ == '__main__':
    unittest.main()
