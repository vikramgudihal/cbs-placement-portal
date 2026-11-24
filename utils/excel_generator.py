import csv
import io
from io import StringIO
from flask import make_response
import datetime
import xlsxwriter
from bson import ObjectId

def generate_student_export(students):
    """
    Generates a comprehensive CSV file from all student documents.
    Matches dashboard data exactly with all academic and personal details.
    """
    si = StringIO()
    cw = csv.writer(si)
    
    # Comprehensive Header matching dashboard data
    headers = [
        'Student ID', 'Full Name', 'Email', 'Phone', 'Gender', 
        'Date of Birth', 'Aadhaar Number', 'PAN',
        '10th School', '10th Board', '10th Year', '10th Percentage',
        '12th School', '12th Board', '12th Year', '12th Percentage', '12th Stream',
        'UG College', 'UG University', 'UG Degree', 'UG Branch', 'UG Year', 'UG CGPA', 'UG Backlogs', 'UG Backlog Status',
        'PG College', 'PG University', 'PG Degree', 'PG Branch', 'PG Year', 'PG CGPA', 'PG Backlogs', 'PG Backlog Status',
        'Skills', 'Projects', 'Branch', 'CGPA', 'Status', 'Registered At'
    ]
    cw.writerow(headers)
    
    # Data
    for s in students:
        # Extract academic info safely
        academic = s.get('academic', {})
        tenth = academic.get('tenth', {})
        twelfth = academic.get('twelfth', {})
        ug = academic.get('ug', {})
        pg = academic.get('pg', {})
        
        # Get user email from users collection if needed
        from utils.db import get_db
        db = get_db()
        user = db.users.find_one({'_id': s.get('user_id')})
        email = user.get('email', 'N/A') if user else 'N/A'
        
        cw.writerow([
            s.get('student_id', 'N/A'),
            s.get('name', 'N/A'),
            email,
            s.get('phone', 'N/A'),
            s.get('gender', 'N/A'),
            s.get('dob', 'N/A'),
            s.get('aadhaar', 'N/A'),
            s.get('pan', 'N/A'),
            # 10th
            tenth.get('school', ''),
            tenth.get('board', ''),
            tenth.get('year', ''),
            tenth.get('score', ''),
            # 12th
            twelfth.get('school', ''),
            twelfth.get('board', ''),
            twelfth.get('year', ''),
            twelfth.get('score', ''),
            twelfth.get('stream', ''),
            # UG
            ug.get('college', ''),
            ug.get('university', ''),
            ug.get('degree', ''),
            ug.get('branch', ''),
            ug.get('year', ''),
            ug.get('score', ''),
            ug.get('backlogs', 0),
            ug.get('backlog_status', ''),
            # PG
            pg.get('college', ''),
            pg.get('university', ''),
            pg.get('degree', ''),
            pg.get('branch', ''),
            pg.get('year', ''),
            pg.get('score', ''),
            pg.get('backlogs', 0),
            pg.get('backlog_status', ''),
            # Skills & Projects
            ", ".join(s.get('skills', [])),
            s.get('projects', ''),
            # Quick filters
            s.get('branch', 'N/A'),
            s.get('cgpa', 0.0),
            'Active' if s.get('is_active') else 'Inactive',
            s.get('registered_at', '').strftime('%Y-%m-%d') if s.get('registered_at') else 'N/A'
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=students_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output


def generate_application_export(applications, job_title="All_Applications"):
    """
    Generates a comprehensive CSV file for job applications.
    Includes auto-filled student data + job-specific data + multiple application flag.
    """
    si = StringIO()
    cw = csv.writer(si)
    
    # Comprehensive headers matching admin dashboard
    headers = [
        'Student Name', 'Student ID', 'Email', 'Phone', 'College / Institution', 'Branch', 'CGPA',
        'Company', 'Job Role', 'Applied Date', 'Status',
        'Rejection Stage', 'Panel Feedback',
        'Student Response', 'Response Date',
        'Multiple Applications', 'Skills'
    ]
    cw.writerow(headers)
    
    for app in applications:
        # Safely extract student info (can be dict or list of dicts)
        si_raw = app.get('student_info')
        if isinstance(si_raw, list):
            student_info = si_raw[0] if si_raw else {}
        elif isinstance(si_raw, dict):
            student_info = si_raw
        else:
            student_info = {}

        # Safely extract user info
        ui_raw = app.get('user_info')
        if isinstance(ui_raw, list):
            user_info = ui_raw[0] if ui_raw else {}
        elif isinstance(ui_raw, dict):
            user_info = ui_raw
        else:
            user_info = {}

        # Safely extract job info
        ji_raw = app.get('job_info')
        if isinstance(ji_raw, list):
            job_info = ji_raw[0] if ji_raw else {}
        elif isinstance(ji_raw, dict):
            job_info = ji_raw
        else:
            job_info = {}

        # Multiple application flag
        is_multiple = 'YES' if app.get('is_multiple_applicant') else 'NO'

        # Response handling
        response = app.get('student_response', 'Pending')
        response_date = app.get('response_at', '')
        if response_date:
            if hasattr(response_date, 'strftime'):
                response_date = response_date.strftime('%Y-%m-%d %H:%M')
        else:
            response_date = 'N/A'

        applied_date = app.get('applied_at', '')
        if applied_date:
            if hasattr(applied_date, 'strftime'):
                applied_date = applied_date.strftime('%Y-%m-%d %H:%M')
        else:
            applied_date = 'N/A'

        # Resolve field values with full fallbacks
        student_name = app.get('student_name') or student_info.get('name') or user_info.get('name') or 'N/A'
        student_id_val = app.get('student_id_code') or student_info.get('student_id') or app.get('student_id') or 'N/A'
        email_val = app.get('student_email') or user_info.get('email') or 'N/A'
        phone_val = app.get('student_phone') or student_info.get('phone') or 'N/A'
        candidate_college = app.get('candidate_college') or student_info.get('college') or 'Chetan Business School'
        branch_val = app.get('branch') or student_info.get('branch') or 'N/A'
        cgpa_val = app.get('cgpa') or student_info.get('cgpa') or 0.0
        company_val = (job_info.get('company_name') if isinstance(job_info, dict) else None) or app.get('company_name') or 'N/A'
        role_val = (job_info.get('role') if isinstance(job_info, dict) else None) or app.get('job_role') or app.get('role') or 'N/A'
        rejection_stage = app.get('rejection_stage') or ('N/A' if app.get('status') != 'Rejected' else 'Resume Screening')
        panel_feedback = app.get('rejection_reason') or app.get('round_note') or 'N/A'
        skills_raw = app.get('skills') or student_info.get('skills', [])
        skills_str = ", ".join(skills_raw) if isinstance(skills_raw, list) else str(skills_raw)

        cw.writerow([
            student_name,
            student_id_val,
            email_val,
            phone_val,
            candidate_college,
            branch_val,
            cgpa_val,
            company_val,
            role_val,
            applied_date,
            app.get('status', 'Pending'),
            rejection_stage,
            panel_feedback,
            response,
            response_date,
            is_multiple,
            skills_str
        ])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=applications_{job_title.replace(' ', '_')}.csv"
    output.headers["Content-type"] = "text/csv"
    return output


def generate_stage_progression_excel(applications, job_info=None, title_suffix="Whole_Companies_Master"):
    """
    Generates a professional, multi-sheet Microsoft Excel (.xlsx) workbook for:
    1. Single Company recruitment drive OR
    2. Whole Companies consolidated master stage tracking.
    
    Includes:
    - Sheet 1: Candidate Stage Progression (All candidates, academic details, current stage, panel remarks, RSVP)
    - Sheet 2: Placed Offers & Corporate Transitions (Candidates who secured offers, packages, and exit status)
    - Sheet 3: Company Stage Analytics (Breakdown of applicant counts across each stage per company)
    """
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})

    # Color Palette & Styles
    title_fmt = wb.add_format({
        'bold': True, 'font_size': 14, 'font_color': '#FFFFFF', 
        'bg_color': '#1E3A8A', 'align': 'center', 'valign': 'vcenter'
    })
    sub_fmt = wb.add_format({
        'font_size': 9, 'italic': True, 'font_color': '#334155', 
        'bg_color': '#F1F5F9', 'align': 'center', 'valign': 'vcenter', 'border': 1
    })
    th_fmt = wb.add_format({
        'bold': True, 'font_size': 10, 'font_color': '#FFFFFF', 
        'bg_color': '#1E40AF', 'align': 'center', 'valign': 'vcenter', 
        'border': 1, 'text_wrap': True
    })
    th_placed_fmt = wb.add_format({
        'bold': True, 'font_size': 10, 'font_color': '#FFFFFF', 
        'bg_color': '#065F46', 'align': 'center', 'valign': 'vcenter', 
        'border': 1, 'text_wrap': True
    })
    th_analytics_fmt = wb.add_format({
        'bold': True, 'font_size': 10, 'font_color': '#FFFFFF', 
        'bg_color': '#4C1D95', 'align': 'center', 'valign': 'vcenter', 
        'border': 1, 'text_wrap': True
    })
    
    # Cell Formats
    cell_left = wb.add_format({'font_size': 9, 'border': 1, 'valign': 'vcenter'})
    cell_center = wb.add_format({'font_size': 9, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
    cell_bold_center = wb.add_format({'font_size': 9, 'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
    cell_bold_left = wb.add_format({'font_size': 9, 'bold': True, 'border': 1, 'valign': 'vcenter'})
    cell_num = wb.add_format({'font_size': 9, 'border': 1, 'align': 'right', 'valign': 'vcenter', 'num_format': '#,##0.00'})

    # Stage Status Badges
    badge_selected = wb.add_format({
        'font_size': 9, 'bold': True, 'bg_color': '#D1FAE5', 'font_color': '#065F46', 
        'border': 1, 'align': 'center', 'valign': 'vcenter'
    })
    badge_interview = wb.add_format({
        'font_size': 9, 'bold': True, 'bg_color': '#FEF3C7', 'font_color': '#92400E', 
        'border': 1, 'align': 'center', 'valign': 'vcenter'
    })
    badge_shortlisted = wb.add_format({
        'font_size': 9, 'bold': True, 'bg_color': '#DBEAFE', 'font_color': '#1E40AF', 
        'border': 1, 'align': 'center', 'valign': 'vcenter'
    })
    badge_gd = wb.add_format({
        'font_size': 9, 'bold': True, 'bg_color': '#EDE9FE', 'font_color': '#5B21B6', 
        'border': 1, 'align': 'center', 'valign': 'vcenter'
    })
    badge_rejected = wb.add_format({
        'font_size': 9, 'bold': True, 'bg_color': '#FEE2E2', 'font_color': '#991B1B', 
        'border': 1, 'align': 'center', 'valign': 'vcenter'
    })
    badge_withdrawn = wb.add_format({
        'font_size': 9, 'italic': True, 'bg_color': '#F3F4F6', 'font_color': '#4B5563', 
        'border': 1, 'align': 'center', 'valign': 'vcenter'
    })
    badge_applied = wb.add_format({
        'font_size': 9, 'bg_color': '#F8FAFC', 'font_color': '#334155', 
        'border': 1, 'align': 'center', 'valign': 'vcenter'
    })

    # Extract & standardize application rows
    parsed_rows = []
    for idx, app in enumerate(applications, start=1):
        # Extract student info
        si_raw = app.get('student_info')
        if isinstance(si_raw, list):
            si = si_raw[0] if si_raw else {}
        elif isinstance(si_raw, dict):
            si = si_raw
        else:
            si = {}

        ui_raw = app.get('user_info')
        if isinstance(ui_raw, list):
            ui = ui_raw[0] if ui_raw else {}
        elif isinstance(ui_raw, dict):
            ui = ui_raw
        else:
            ui = {}

        ji_raw = app.get('job_info')
        if isinstance(ji_raw, list):
            ji = ji_raw[0] if ji_raw else {}
        elif isinstance(ji_raw, dict):
            ji = ji_raw
        else:
            ji = {}

        academic = si.get('academic', {})
        tenth = academic.get('tenth', {})
        twelfth = academic.get('twelfth', {})
        ug = academic.get('ug', {})

        student_name = app.get('student_name') or si.get('name') or ui.get('name') or 'N/A'
        sid = app.get('student_id_code') or si.get('student_id') or app.get('student_id') or 'N/A'
        if isinstance(sid, ObjectId):
            sid = si.get('student_id', str(sid))
        email = app.get('student_email') or ui.get('email') or 'N/A'
        phone = app.get('student_phone') or si.get('phone') or 'N/A'
        college = app.get('candidate_college') or si.get('college') or 'Chetan Business School'
        branch = app.get('branch') or si.get('branch') or 'N/A'
        try:
            cgpa = float(app.get('cgpa') or si.get('cgpa') or 0.0)
        except Exception:
            cgpa = 0.0
        backlogs = ug.get('backlogs', 0)
        tenth_val = tenth.get('score', 'N/A')
        twelfth_val = twelfth.get('score', 'N/A')
        ug_score = ug.get('score', cgpa)

        company = (ji.get('company_name') if isinstance(ji, dict) else None) or app.get('company_name') or 'Recruiter'
        role = (ji.get('role') if isinstance(ji, dict) else None) or app.get('job_role') or app.get('role') or 'Associate'
        package = (ji.get('package') if isinstance(ji, dict) else None) or app.get('package') or 'Disclosed in Drive'

        status = app.get('status', 'Applied')
        rejection_stage = app.get('rejection_stage') or ('N/A' if status != 'Rejected' else 'Resume Screening')
        panel_remarks = app.get('rejection_reason') or app.get('round_note') or ('Placement Benchmark Met' if status == 'Selected' else 'Evaluation in Progress')

        if status == 'Selected':
            stage_desc = 'Final Offer Letter Extended'
            stage_group = 'Selected'
        elif status == 'Interview':
            stage_desc = 'Technical / HR Interview Round'
            stage_group = 'Interview'
        elif status == 'GD':
            stage_desc = 'Group Discussion (GD)'
            stage_group = 'GD'
        elif status == 'Shortlisted':
            stage_desc = 'Online Assessment / Shortlisted'
            stage_group = 'Shortlisted'
        elif status == 'Rejected':
            stage_desc = f'Eliminated at {rejection_stage}'
            stage_group = 'Rejected'
        elif status in ['Auto_Withdrawn', 'Withdrawn']:
            stage_desc = 'Withdrawn (Placed Elsewhere)'
            stage_group = 'Withdrawn'
        else:
            stage_desc = 'Application Screening'
            stage_group = 'Applied'

        applied_at = app.get('applied_at')
        applied_str = applied_at.strftime('%d-%b-%Y') if hasattr(applied_at, 'strftime') else (str(applied_at)[:10] if applied_at else 'N/A')

        updated_at = app.get('updated_at') or applied_at
        updated_str = updated_at.strftime('%d-%b-%Y') if hasattr(updated_at, 'strftime') else (str(updated_at)[:10] if updated_at else 'N/A')

        p_status = si.get('placement_status', 'Active')
        if p_status == 'Placed_Archived':
            exit_display = 'Placed & Corporate Exited'
        elif p_status == 'Placed_Pending_Exit':
            exit_display = 'Placed (48h Transition Window)'
        elif status == 'Selected':
            exit_display = 'Offer Received (Transitioning)'
        else:
            exit_display = 'Active Candidate'

        rsvp = app.get('student_response') or 'Pending'

        # Candidate Drive-Specific Custom Requirements Data
        custom_res = app.get('custom_responses', {}) or {}
        github_val = custom_res.get('github_url') or si.get('github_url', 'N/A')
        linkedin_val = custom_res.get('linkedin_url') or si.get('linkedin_url', 'N/A')
        relocate_val = custom_res.get('willing_to_relocate') or si.get('willing_to_relocate', 'N/A')
        location_val = custom_res.get('preferred_location') or si.get('preferred_location', 'N/A')
        custom_ans_val = custom_res.get('custom_answer', 'N/A')

        parsed_rows.append({
            'idx': idx,
            'student_id': sid,
            'student_name': student_name,
            'email': email,
            'phone': phone,
            'college': college,
            'branch': branch,
            'cgpa': cgpa,
            'backlogs': backlogs,
            'tenth': tenth_val,
            'twelfth': twelfth_val,
            'ug_score': ug_score,
            'company': company,
            'role': role,
            'package': package,
            'current_stage': stage_desc,
            'status': status,
            'stage_group': stage_group,
            'rejection_stage': rejection_stage,
            'panel_remarks': panel_remarks,
            'rsvp': rsvp,
            'applied_str': applied_str,
            'updated_str': updated_str,
            'exit_display': exit_display,
            'github': github_val,
            'linkedin': linkedin_val,
            'relocate': relocate_val,
            'preferred_location': location_val,
            'custom_answer': custom_ans_val
        })

    # Scope Title
    if job_info:
        scope_title = f"Company Drive: {job_info.get('company_name', 'Company')} ({job_info.get('role', 'Role')})"
    else:
        scope_title = "Whole Companies (Consolidated Master Report)"
    report_time = datetime.datetime.now().strftime('%d-%b-%Y %I:%M %p')

    # ============================================================
    # SHEET 1: Candidate Stage Progression
    # ============================================================
    ws1 = wb.add_worksheet('Stage Progression')
    headers1 = [
        'SI No', 'Student ID / USN', 'Candidate Name', 'Email ID', 'Phone Number',
        'Branch', 'Current CGPA', 'Active Backlogs', '10th %', '12th %',
        'Company Name', 'Role / Profile', 'Package', 'Current Recruitment Stage',
        'Status Outcome', 'Elimination Stage', 'Panel Feedback / Remarks',
        'Candidate RSVP', 'Applied Date', 'Last Updated', 'Placement Exit Status',
        'GitHub URL', 'LinkedIn URL', 'Relocation Preference', 'Preferred Location', 'Screening Answer'
    ]

    ws1.merge_range(0, 0, 0, len(headers1) - 1, 'CHETAN BUSINESS SCHOOL — CAMPUS RECRUITMENT & STAGE PROGRESSION REPORT', title_fmt)
    ws1.set_row(0, 32)
    ws1.merge_range(1, 0, 1, len(headers1) - 1, f'Scope: {scope_title}  |  Generated On: {report_time}  |  Total Candidate Records: {len(parsed_rows)}', sub_fmt)
    ws1.set_row(1, 20)
    ws1.set_row(3, 26)

    for c_idx, h in enumerate(headers1):
        ws1.write(3, c_idx, h, th_fmt)

    for r_idx, r in enumerate(parsed_rows, start=4):
        ws1.set_row(r_idx, 20)
        sg = r['stage_group']
        if sg == 'Selected':
            st_fmt = badge_selected
        elif sg == 'Interview':
            st_fmt = badge_interview
        elif sg == 'Shortlisted':
            st_fmt = badge_shortlisted
        elif sg == 'GD':
            st_fmt = badge_gd
        elif sg == 'Rejected':
            st_fmt = badge_rejected
        elif sg == 'Withdrawn':
            st_fmt = badge_withdrawn
        else:
            st_fmt = badge_applied

        ws1.write(r_idx, 0, r['idx'], cell_center)
        ws1.write(r_idx, 1, str(r['student_id']), cell_bold_center)
        ws1.write(r_idx, 2, r['student_name'], cell_bold_left)
        ws1.write(r_idx, 3, r['email'], cell_left)
        ws1.write(r_idx, 4, str(r['phone']), cell_center)
        ws1.write(r_idx, 5, r['branch'], cell_center)
        ws1.write(r_idx, 6, r['cgpa'], cell_num)
        ws1.write(r_idx, 7, r['backlogs'], cell_center)
        ws1.write(r_idx, 8, str(r['tenth']), cell_center)
        ws1.write(r_idx, 9, str(r['twelfth']), cell_center)
        ws1.write(r_idx, 10, r['company'], cell_bold_left)
        ws1.write(r_idx, 11, r['role'], cell_left)
        ws1.write(r_idx, 12, r['package'], cell_center)
        ws1.write(r_idx, 13, r['current_stage'], cell_bold_left)
        ws1.write(r_idx, 14, r['status'], st_fmt)
        ws1.write(r_idx, 15, r['rejection_stage'], cell_left)
        ws1.write(r_idx, 16, r['panel_remarks'], cell_left)
        ws1.write(r_idx, 17, r['rsvp'], cell_center)
        ws1.write(r_idx, 18, r['applied_str'], cell_center)
        ws1.write(r_idx, 19, r['updated_str'], cell_center)
        ws1.write(r_idx, 20, r['exit_display'], cell_center)
        ws1.write(r_idx, 21, str(r.get('github', 'N/A')), cell_left)
        ws1.write(r_idx, 22, str(r.get('linkedin', 'N/A')), cell_left)
        ws1.write(r_idx, 23, str(r.get('relocate', 'N/A')), cell_center)
        ws1.write(r_idx, 24, str(r.get('preferred_location', 'N/A')), cell_left)
        ws1.write(r_idx, 25, str(r.get('custom_answer', 'N/A')), cell_left)

    if parsed_rows:
        ws1.autofilter(3, 0, len(parsed_rows) + 3, len(headers1) - 1)

    col_widths1 = [7, 16, 24, 28, 15, 14, 12, 14, 10, 10, 22, 22, 14, 30, 15, 24, 32, 14, 14, 14, 26, 24, 24, 16, 18, 28]
    for c_idx, w in enumerate(col_widths1):
        ws1.set_column(c_idx, c_idx, w)

    # ============================================================
    # SHEET 2: Placed Candidates & Corporate Offers
    # ============================================================
    ws2 = wb.add_worksheet('Placed Offers')
    headers2 = [
        'SI No', 'Student ID / USN', 'Candidate Name', 'Email ID', 'Phone Number',
        'Branch', 'CGPA', 'Recruiter / Company', 'Designation / Role', 'Compensation (CTC)',
        'Selection Date', 'Corporate Transition Status'
    ]

    placed_rows = [r for r in parsed_rows if r['status'] == 'Selected']

    ws2.merge_range(0, 0, 0, len(headers2) - 1, 'CHETAN BUSINESS SCHOOL — CORPORATE PLACEMENT OFFERS SECURED', title_fmt)
    ws2.set_row(0, 32)
    ws2.merge_range(1, 0, 1, len(headers2) - 1, f'Scope: {scope_title}  |  Total Placed Offers: {len(placed_rows)}  |  Generated On: {report_time}', sub_fmt)
    ws2.set_row(1, 20)
    ws2.set_row(3, 26)

    for c_idx, h in enumerate(headers2):
        ws2.write(3, c_idx, h, th_placed_fmt)

    for r_idx, r in enumerate(placed_rows, start=4):
        ws2.set_row(r_idx, 20)
        ws2.write(r_idx, 0, r_idx - 3, cell_center)
        ws2.write(r_idx, 1, str(r['student_id']), cell_bold_center)
        ws2.write(r_idx, 2, r['student_name'], cell_bold_left)
        ws2.write(r_idx, 3, r['email'], cell_left)
        ws2.write(r_idx, 4, str(r['phone']), cell_center)
        ws2.write(r_idx, 5, r['branch'], cell_center)
        ws2.write(r_idx, 6, r['cgpa'], cell_num)
        ws2.write(r_idx, 7, r['company'], cell_bold_left)
        ws2.write(r_idx, 8, r['role'], cell_left)
        ws2.write(r_idx, 9, r['package'], cell_bold_center)
        ws2.write(r_idx, 10, r['updated_str'], cell_center)
        ws2.write(r_idx, 11, r['exit_display'], badge_selected)

    if placed_rows:
        ws2.autofilter(3, 0, len(placed_rows) + 3, len(headers2) - 1)

    col_widths2 = [7, 16, 24, 28, 15, 14, 12, 24, 24, 16, 16, 28]
    for c_idx, w in enumerate(col_widths2):
        ws2.set_column(c_idx, c_idx, w)

    # ============================================================
    # SHEET 3: Company Stage Analytics Summary
    # ============================================================
    ws3 = wb.add_worksheet('Company Analytics')
    headers3 = [
        'SI No', 'Company Name', 'Job Role', 'Package',
        'Total Applied', 'Shortlisted', 'In GD', 'In Interview',
        'Final Selected', 'Eliminated', 'Conversion Rate (%)'
    ]

    ws3.merge_range(0, 0, 0, len(headers3) - 1, 'CHETAN BUSINESS SCHOOL — COMPANY-WISE STAGE RECRUITMENT FUNNEL', title_fmt)
    ws3.set_row(0, 32)
    ws3.merge_range(1, 0, 1, len(headers3) - 1, f'Recruiter Pipeline Summary  |  Report Generated: {report_time}', sub_fmt)
    ws3.set_row(1, 20)
    ws3.set_row(3, 26)

    for c_idx, h in enumerate(headers3):
        ws3.write(3, c_idx, h, th_analytics_fmt)

    # Aggregate by company
    company_map = {}
    for r in parsed_rows:
        ckey = (r['company'], r['role'])
        if ckey not in company_map:
            company_map[ckey] = {
                'company': r['company'],
                'role': r['role'],
                'package': r['package'],
                'total': 0,
                'shortlisted': 0,
                'gd': 0,
                'interview': 0,
                'selected': 0,
                'rejected': 0
            }
        cm = company_map[ckey]
        cm['total'] += 1
        st = r['status']
        if st == 'Selected':
            cm['selected'] += 1
        elif st == 'Interview':
            cm['interview'] += 1
        elif st == 'GD':
            cm['gd'] += 1
        elif st == 'Shortlisted':
            cm['shortlisted'] += 1
        elif st == 'Rejected':
            cm['rejected'] += 1

    summary_list = list(company_map.values())
    summary_list.sort(key=lambda x: x['total'], reverse=True)

    for r_idx, cm in enumerate(summary_list, start=4):
        ws3.set_row(r_idx, 20)
        rate = round((cm['selected'] / max(cm['total'], 1)) * 100, 1)
        ws3.write(r_idx, 0, r_idx - 3, cell_center)
        ws3.write(r_idx, 1, cm['company'], cell_bold_left)
        ws3.write(r_idx, 2, cm['role'], cell_left)
        ws3.write(r_idx, 3, cm['package'], cell_center)
        ws3.write(r_idx, 4, cm['total'], cell_center)
        ws3.write(r_idx, 5, cm['shortlisted'], cell_center)
        ws3.write(r_idx, 6, cm['gd'], cell_center)
        ws3.write(r_idx, 7, cm['interview'], cell_center)
        ws3.write(r_idx, 8, cm['selected'], badge_selected if cm['selected'] > 0 else cell_center)
        ws3.write(r_idx, 9, cm['rejected'], badge_rejected if cm['rejected'] > 0 else cell_center)
        ws3.write(r_idx, 10, f"{rate}%", cell_bold_center)

    if summary_list:
        ws3.autofilter(3, 0, len(summary_list) + 3, len(headers3) - 1)

    col_widths3 = [7, 26, 24, 16, 14, 14, 12, 14, 16, 14, 20]
    for c_idx, w in enumerate(col_widths3):
        ws3.set_column(c_idx, c_idx, w)

    wb.close()
    output.seek(0)

    clean_filename = f"CBS_Placement_Stages_{title_suffix.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={clean_filename}"
    response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return response
