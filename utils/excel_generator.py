import csv
from io import StringIO
from flask import make_response
import datetime

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
        'Student Name', 'Student ID', 'Email', 'Phone', 'Branch', 'CGPA',
        'Company', 'Job Role', 'Applied Date', 'Status',
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
        branch_val = app.get('branch') or student_info.get('branch') or 'N/A'
        cgpa_val = app.get('cgpa') or student_info.get('cgpa') or 0.0
        company_val = (job_info.get('company_name') if isinstance(job_info, dict) else None) or app.get('company_name') or 'N/A'
        role_val = (job_info.get('role') if isinstance(job_info, dict) else None) or app.get('job_role') or app.get('role') or 'N/A'
        skills_raw = app.get('skills') or student_info.get('skills', [])
        skills_str = ", ".join(skills_raw) if isinstance(skills_raw, list) else str(skills_raw)

        cw.writerow([
            student_name,
            student_id_val,
            email_val,
            phone_val,
            branch_val,
            cgpa_val,
            company_val,
            role_val,
            applied_date,
            app.get('status', 'Pending'),
            response,
            response_date,
            is_multiple,
            skills_str
        ])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=applications_{job_title.replace(' ', '_')}.csv"
    output.headers["Content-type"] = "text/csv"
    return output
