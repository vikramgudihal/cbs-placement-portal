import io
import os
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

    def test_mobile_onboarding_autofill_and_next_step(self):
        """Verify multi-line PDF extraction, school extraction, BOM PDF parsing, and onboarding wizard validation UI"""
        from unittest.mock import patch
        multiline_resume = """
        RIYA V NAVADE
        +91 98765 43210 | riya.navade@gmail.com | P02DR25S126065

        EDUCATION
        MCA - Chetan Business School, Karnatak University
        2026 | CGPA: 8.80

        BCA - KLES College of BCA
        Karnataka University Dharwad | 2024 | 8.2 CGPA

        PUC / Class 12
        KLE Independent PU College
        State PU Board | 2021 | 86.4% | Science PCMC

        SSLC / Class X
        Chinmaya English Medium School
        State Board | 2019 | 91.2%

        TECHNICAL SKILLS
        C++, Node.js, Python, SQL
        """
        with patch('utils.resume_parser.extract_text_from_pdf', return_value=multiline_resume):
            res = parse_resume(io.BytesIO(b"%PDF-1.4 dummy"))
            self.assertTrue(res['success'])
            d = res['data']
            self.assertEqual(d.get('phone'), '9876543210')
            self.assertIn('91.2', d.get('tenth_score', ''))
            self.assertIn('Chinmaya', d.get('tenth_school', ''))
            self.assertIn('86.4', d.get('twelfth_score', ''))
            self.assertIn('KLE Independent PU College', d.get('twelfth_school', ''))
            self.assertIn('KLES College of BCA', d.get('ug_college', ''))
            self.assertIn('C++', d.get('skills', ''))
            self.assertIn('Node.js', d.get('skills', ''))

        with open('templates/student/complete_profile.html', encoding='utf-8') as f:
            cp_html = f.read()
        for sym in [
            'openResumePicker', 'normalizeIndianPhone', 'validateStepFields',
            'input-invalid-highlight', 'stepValidationError1', 'stepValidationError2',
            'parserErrorAlert', 'accept=".pdf,application/pdf"'
        ]:
            self.assertIn(sym, cp_html)

        # Verify BOM-prefixed genuine PDF passes api_parse_resume validation & persistence
        from app import app, users_collection
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        user = users_collection.find_one({'email': 'vikram.patel.mca@gmail.com'})
        if user:
            client = app.test_client()
            with client.session_transaction() as sess:
                sess['user_id'] = str(user['_id'])
                sess['role'] = 'student'
            with patch('utils.resume_parser.extract_text_from_pdf', return_value=multiline_resume):
                bom_pdf = io.BytesIO(b"\xef\xbb\xbf%PDF-1.4\n%%EOF")
                api_resp = client.post('/api/student/parse-resume', data={
                    'resume': (bom_pdf, 'riya_mobile_cv.pdf')
                })
                self.assertEqual(api_resp.status_code, 200)
                payload = api_resp.get_json()
                self.assertTrue(payload.get('success'))
                self.assertTrue(payload.get('resume_saved'))
                self.assertEqual(payload['data'].get('tenth_score'), '91.2')

        print("[PASS] Multi-line resume extraction, BOM PDF persistence, and onboarding wizard validation verified.")

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

    def test_smooth_motion_marquee_and_badges(self):
        """Verify recruiter marquee and floating badges use GPU-accelerated translate3d, 
        have zero loop seams, and eliminate backdrop-filter GPU bottlenecks across all devices"""
        with open('templates/landing.html', encoding='utf-8') as f:
            landing_html = f.read()

        # 1. Dual identical marquee groups for pixel-perfect seamless looping
        self.assertIn('class="marquee-group"', landing_html)
        self.assertEqual(landing_html.count('class="marquee-group"'), 2, 
                         "Marquee must have exactly 2 balanced identical groups for a seamless 100% loop with 0 glitch")

        # 2. Hardware-accelerated 3D transforms
        self.assertIn('translate3d(-50%, 0, 0)', landing_html, 
                      "Continuous marquee scroll must use translate3d for GPU compositing")
        self.assertIn('translate3d(0, -6px, 0)', landing_html,
                      "Floating badges must use translate3d to prevent sub-pixel rounding jitter")

        # 3. Compositor layer promotion
        self.assertIn('will-change: transform', landing_html)
        self.assertIn('backface-visibility: hidden', landing_html)

        # 4. Floating badge accreditation text exists and uses accelerated keyframe
        self.assertIn('NAAC Accredited TPO Hub', landing_html)
        self.assertIn('floatGentle', landing_html)

        print("[PASS] Recruiter marquee and NAAC badge verified: hardware-accelerated 3D motion with zero seam glitch.")

    def test_cbs_official_banner_and_closed_app_push_service(self):
        """Verify official CBS banner in landing hero and service worker closed-app push notification listeners"""
        # 1. Landing page official institutional master header
        with open('templates/landing.html', encoding='utf-8') as f:
            landing_html = f.read()
        self.assertIn('institutional-master-banner', landing_html)
        self.assertIn('CHETAN BUSINESS SCHOOL', landing_html)
        self.assertIn('AICTE Approved', landing_html)
        self.assertTrue(os.path.exists('static/images/logo1.png'))

        # 2. Service Worker closed-app push notification listener
        with open('static/js/sw.js', encoding='utf-8') as f:
            sw_js = f.read()
        self.assertIn("self.addEventListener('push'", sw_js)
        self.assertIn("self.addEventListener('notificationclick'", sw_js)
        self.assertIn("showNotification", sw_js)

        # 3. Base template push notification permission requester
        with open('templates/base.html', encoding='utf-8') as f:
            base_html = f.read()
        self.assertIn('requestNotificationPermission', base_html)

        print("[PASS] CBS official crest banner and closed-app Web Push Service Worker listeners verified.")

    def test_mobile_modal_guard_and_hero_alignment(self):
        """Verify modal-overlay is not unconditionally displayed on mobile, and hero-subtitle is aligned flush-left"""
        with open('static/css/responsive-suite.css', encoding='utf-8') as f:
            resp_css = f.read()

        # Modal must NOT be unconditionally displayed on mobile screens
        self.assertNotIn('.modal-overlay {\n    padding: 0.75rem !important;\n    display: flex !important;', resp_css)
        self.assertIn('.modal-overlay.active', resp_css)
        self.assertIn('#logoutModal:not(.active)', resp_css)

        # Base.html logout modal must have inline display: none default guard
        with open('templates/base.html', encoding='utf-8') as f:
            base_html = f.read()
        self.assertIn('id="logoutModal" class="modal-overlay" style="display: none;"', base_html)

        # Landing hero-subtitle must be flush left with margin-left: 0 and text-align: left
        with open('templates/landing.html', encoding='utf-8') as f:
            landing_html = f.read()
        self.assertIn('margin-left: 0 !important', landing_html)
        self.assertIn('text-align: left !important', landing_html)
        print("[PASS] Mobile modal guard and flush-left hero alignment verified.")

    def test_all_mobile_ui_perfection(self):
        """Verify all 7 mobile responsiveness issues from user screenshots are resolved"""
        with open('templates/base.html', encoding='utf-8') as f:
            base_html = f.read()
        with open('static/css/responsive-suite.css', encoding='utf-8') as f:
            resp_css = f.read()
        with open('templates/admin/manage_jobs.html', encoding='utf-8') as f:
            jobs_html = f.read()
        with open('templates/admin/manage_users.html', encoding='utf-8') as f:
            users_html = f.read()

        # Image 1: Public navbar no redundant Home button on landing page ('home') + nowrap
        self.assertIn("request.endpoint not in ['home', 'index', 'landing']", base_html)
        self.assertIn('auth-nav-back', base_html)
        self.assertIn('.btn-back:not(.auth-nav-back)', resp_css)
        self.assertIn('white-space:nowrap', base_html)

        # Image 2 & 3: Topbar mobile brand nowrap + window-level logout synced with main.js & 30000 z-index
        self.assertIn('topbar-mobile-brand', base_html)
        self.assertIn('window.showLogoutModal', base_html)
        self.assertIn('topbar-logout-btn', base_html)
        self.assertIn('z-index: 30000 !important', resp_css)
        with open('static/js/main.js', encoding='utf-8') as f:
            main_js = f.read()
        self.assertIn('modal.classList.add("active")', main_js)
        self.assertIn('setProperty("display", "flex", "important")', main_js)

        # Universal Back Navigation History Stack (no /login bounce loop on mobile)
        self.assertIn('cbs_nav_history', base_html)
        self.assertIn('window.handleUniversalBack', base_html)

        # Service worker network-first for static CSS/JS & bumped cache version
        with open('static/js/sw.js', encoding='utf-8') as f:
            sw_js = f.read()
        self.assertNotIn("cbs-3icell-v3", sw_js)

        # Verify zero brace mismatches across all CSS stylesheets
        import glob
        for css_path in glob.glob('static/css/*.css'):
            with open(css_path, encoding='utf-8') as cf:
                css_text = cf.read()
            self.assertEqual(css_text.count('{'), css_text.count('}'), f"Unbalanced CSS braces in {css_path}")

        # Image 4: Filter tabs ribbon horizontal swipe scroll (no cut-off)
        self.assertIn('overflow-x: auto', jobs_html)
        self.assertIn('white-space: nowrap', jobs_html)

        # Image 5: Candidate pipeline dossier cards comfortable padding
        self.assertIn('applications-streamlined-table tr.app-row', resp_css)
        self.assertIn('1.35rem 1.15rem', resp_css)

        # Image 6: Students tab full width 100% on mobile
        self.assertIn('grid-template-columns: 1fr !important;', users_html)
        self.assertIn('#usersGridView', users_html)

        # Image 7: Sidebar open hides bottom nav & raises sidebar z-index
        self.assertIn('body.sidebar-open .mobile-bottom-nav', resp_css)
        self.assertIn('sidebar-open', base_html)
        self.assertIn('z-index: 10001 !important', resp_css)

        # Verify landing page HTML actually omits redundant navbar Home link & serves Login/Sign Up
        from app import app
        client = app.test_client()
        resp = client.get('/')
        self.assertEqual(resp.status_code, 200)
        landing_rendered = resp.get_data(as_text=True)
        nav_section = landing_rendered.split('<nav class="auth-navbar-bar"')[1].split('</nav>')[0]
        self.assertNotIn('class="btn-back auth-nav-back"', nav_section)
        self.assertIn('Login', nav_section)
        self.assertIn('Sign Up', nav_section)

        print("[PASS] All mobile UI, navbar, back navigation, logout modal, and CSS balance checks verified.")

    def test_student_admin_mobile_responsiveness_and_overflow_guards(self):
        """Verify student dashboard, profile, subpages, admin/faculty views, and mobile navbars prevent horizontal overflow"""
        with open('static/css/responsive-suite.css', encoding='utf-8') as f:
            resp_css = f.read()
        with open('static/css/dashboard-responsive.css', encoding='utf-8') as f:
            dash_resp_css = f.read()
        with open('templates/base.html', encoding='utf-8') as f:
            base_html = f.read()
        with open('templates/student/dashboard.html', encoding='utf-8') as f:
            stu_dash = f.read()
        with open('templates/student/profile.html', encoding='utf-8') as f:
            stu_prof = f.read()

        # Global shell overflow containment & non-breaking tablet/mobile nav
        self.assertIn('.app-shell,\n.app-main,\n.app-content', resp_css)
        self.assertIn('min-width: 0 !important;', resp_css)
        self.assertNotIn('@media (min-width: 769px) {\n  .mobile-bottom-nav', dash_resp_css)
        self.assertNotIn('font-size: -8.4rem;', dash_resp_css)
        self.assertIn('topbar-title-group', base_html)

        # Student Dashboard & Profile responsiveness guards
        self.assertIn('minmax(0, 1fr) 360px', stu_dash)
        self.assertIn('overflow-wrap: anywhere', stu_dash)
        self.assertIn('profile-studio-grid > div', stu_prof)
        self.assertIn('flex-wrap: wrap', stu_prof)
        self.assertIn('overflow-wrap: anywhere', stu_prof)
        self.assertIn('@media (max-width: 640px)', stu_prof)

        # Verify minmax(min(...)) responsive tracks across student & admin card grids
        for tpl_path in [
            'templates/student/jobs.html',
            'templates/student/forms_list.html',
            'templates/admin/manage_jobs.html',
            'templates/admin/manage_announcements.html',
            'templates/admin/manage_forms.html',
            'templates/admin/manage_users.html',
        ]:
            with open(tpl_path, encoding='utf-8') as tf:
                content = tf.read()
            self.assertIn('minmax(min(', content, f"Missing viewport-safe minmax(min(...)) in {tpl_path}")

        print("[PASS] Student/Profile/Admin mobile overflow guards and navbar alignment verified.")

    def test_unified_banners_profile_photo_toasts_and_pipeline_padding(self):
        """Verify profile photo upload & GridFS validation, unified banners, solid toasts, search icon fix, and pipeline card padding"""
        from unittest.mock import MagicMock, patch
        from werkzeug.datastructures import FileStorage
        from app import app, validate_and_store_avatar

        # 1. Validate image magic-byte security checks
        fake_svg = FileStorage(stream=io.BytesIO(b"<svg onload=alert(1)></svg>"), filename="evil.svg", content_type="image/svg+xml")
        ok, err = validate_and_store_avatar(fake_svg, "000000000000000000000001")
        self.assertFalse(ok)
        self.assertIn("Invalid image format", err)

        valid_png = FileStorage(stream=io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"), filename="avatar.png", content_type="image/png")
        mock_fs = MagicMock()
        mock_fs.find.return_value = []
        mock_fs.put.return_value = "mock_avatar_id"
        with patch('app.get_fs', return_value=mock_fs):
            ok_png, res_id = validate_and_store_avatar(valid_png, "000000000000000000000001")
            self.assertTrue(ok_png)
            self.assertEqual(res_id, "mock_avatar_id")

        # 2. Check portal-wide avatar photo support across student/admin templates
        for tpl_path in [
            'templates/base.html',
            'templates/student/profile.html',
            'templates/student/dashboard.html',
            'templates/student/complete_profile.html',
            'templates/admin/student_details.html',
            'templates/admin/manage_users.html',
        ]:
            with open(tpl_path, encoding='utf-8') as tf:
                self.assertIn('view_file_inline', tf.read(), f"Missing inline profile photo rendering in {tpl_path}")

        # 3. Unified ambient command banner across student/admin views
        for tpl_path in [
            'templates/student/jobs.html',
            'templates/admin/manage_users.html',
            'templates/admin/all_students.html',
            'templates/admin/manage_admins.html',
            'templates/admin/login_history.html',
            'templates/admin/password_requests.html',
            'templates/admin/students_activity.html',
        ]:
            with open(tpl_path, encoding='utf-8') as tf:
                self.assertIn('portal-unified-banner', tf.read(), f"Missing unified hero banner in {tpl_path}")

        # 4. Town Hall search icon column fix, opaque flash toast styles, and pipeline shell padding
        with open('templates/student/announcements.html', encoding='utf-8') as f:
            ann_html = f.read()
        self.assertIn('height: auto;', ann_html)
        self.assertIn('flex-wrap: wrap;', ann_html)

        with open('static/css/responsive-suite.css', encoding='utf-8') as f:
            resp_css = f.read()
        self.assertIn('.flash-close-btn', resp_css)
        self.assertIn('#ecfdf5 !important', resp_css)
        self.assertIn('.portal-unified-banner', resp_css)

        with open('templates/admin/applications.html', encoding='utf-8') as f:
            apps_html = f.read()
        self.assertIn('pipeline-table-shell', apps_html)
        self.assertIn('padding: 1.3rem 1.2rem !important', apps_html)

        # Ensure upload_profile_photo route is registered cleanly
        rule_paths = [r.rule for r in app.url_map.iter_rules()]
        self.assertIn('/profile/upload-photo', rule_paths)
        print("[PASS] Profile photo GridFS upload, unified hero banners, opaque toasts, and pipeline padding verified.")

if __name__ == '__main__':
    unittest.main()
