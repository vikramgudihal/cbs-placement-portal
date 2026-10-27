from flask import Flask, render_template, redirect, url_for, session, request, flash, send_from_directory
from utils.db import get_db, get_fs
from utils.auth import hash_password, verify_password, login_required
import os
from bson.objectid import ObjectId
import gridfs
import datetime
from routes.file_serving import file_serving_bp
from routes.dynamic_forms import dynamic_forms_bp
from werkzeug.utils import secure_filename
import datetime
import csv
from io import StringIO
from flask import make_response
from utils.excel_generator import generate_student_export, generate_application_export

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cbs-3i-cell-stable-secret-key-2026-prod-session')

# Register Blueprints
app.register_blueprint(file_serving_bp)
app.register_blueprint(dynamic_forms_bp)

# Password Reset Serializer
from itsdangerous import URLSafeTimedSerializer
serializer = URLSafeTimedSerializer(app.secret_key)

# Config
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- SECURITY CONFIGURATION ---
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

# 1. Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# 2. Secure Headers (Talisman)
talisman = Talisman(
    app,
    content_security_policy={
        'default-src': ["'self'", "https://fonts.googleapis.com", "https://fonts.gstatic.com", "https://unpkg.com", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        'img-src': ["'self'", "data:", "https:", "blob:"],
        'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", "https://unpkg.com", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://unpkg.com", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        'font-src': ["'self'", "data:", "https://fonts.gstatic.com", "https://cdn.jsdelivr.net", "https://unpkg.com", "https://cdnjs.cloudflare.com"],
        'connect-src': ["'self'", "https://cdn.jsdelivr.net", "https://unpkg.com"]
    },
    force_https=False  # Set to True in production with proper SSL
)

# 3. CSRF Protection
from flask_wtf.csrf import CSRFProtect, CSRFError
csrf = CSRFProtect(app)

# 4. Session & Payload Security
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False, # Set to True in production (HTTPS)
    MAX_CONTENT_LENGTH=16 * 1024 * 1024 # 16 MB max payload defense
)

# 5. Production Structured Logging (Rotating file log)
import logging
from logging.handlers import RotatingFileHandler

os.makedirs('logs', exist_ok=True)
log_file_path = os.path.join('logs', 'cbs_portal.log')
file_handler = RotatingFileHandler(log_file_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8')
file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s [%(module)s:%(lineno)d]: %(message)s'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info("CBS Placement Portal initialized with production-level hardening.")

# Initialize DB
db = get_db()
users_collection = db['users']
students_collection = db['students']
jobs_collection = db['jobs']
applications_collection = db['applications']
announcements_collection = db['announcements']
experiences_collection = db['experiences']
notifications_collection = db['notifications']
login_logs_collection = db['login_logs']
forms_collection = db['forms']
form_responses_collection = db['form_responses']
password_requests_collection = db['password_requests']

# Production Index Optimization
def ensure_production_indexes():
    """Ensure database performance and integrity under high concurrent placement traffic."""
    try:
        users_collection.create_index("email", unique=True)
        users_collection.create_index([("role", 1), ("is_approved", 1)])
        users_collection.create_index([("created_at", -1)])

        students_collection.create_index("user_id", unique=True)
        students_collection.create_index("student_id", sparse=True)
        students_collection.create_index([("is_active", 1), ("cgpa", -1)])
        students_collection.create_index([("branch", 1)])
        students_collection.create_index([("is_verified", 1)])

        applications_collection.create_index([("student_id", 1), ("job_id", 1)])
        applications_collection.create_index([("status", 1), ("applied_at", -1)])
        applications_collection.create_index([("job_id", 1), ("status", 1)])

        jobs_collection.create_index([('status', 1)])
        jobs_collection.create_index([('created_at', -1)])
        jobs_collection.create_index([('expires_at', 1)])
        jobs_collection.create_index([('drive_date', 1)])
        jobs_collection.create_index([('company_name', 'text'), ('role', 'text'), ('description', 'text')])

        announcements_collection.create_index([('status', 1)])
        announcements_collection.create_index([('created_at', -1)])
        announcements_collection.create_index([('expires_at', 1)])

        notifications_collection.create_index([('user_id', 1), ('is_read', 1), ('created_at', -1)])
        login_logs_collection.create_index([('user_id', 1), ('login_time', -1)])
    except Exception as e:
        app.logger.warning(f"Production index creation warning: {e}")

ensure_production_indexes()

# --- PRODUCTION HEALTH CHECK ENDPOINT ---
@app.route('/health')
@app.route('/api/health')
def health_check():
    """Production Uptime & Database Connectivity Monitoring."""
    from utils.db import check_db_health
    db_ok, db_msg = check_db_health()
    status_code = 200 if db_ok else 503
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "database": {
            "connected": db_ok,
            "message": db_msg
        },
        "service": {
            "name": "CBS Placement ERP",
            "version": "2.5.0-production",
            "environment": os.environ.get('FLASK_ENV', 'production'),
            "timestamp": datetime.datetime.now().isoformat()
        }
    }, status_code

# --- PRODUCTION ERROR HANDLERS ---
@app.errorhandler(403)
def forbidden_error(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found_error(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template('errors/429.html'), 429

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash("Security session expired. Please refresh the page and submit again.", "warning")
    return redirect(request.referrer or url_for('home'))

@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error(f"Internal 500 Exception: {str(e)}", exc_info=True)
    return render_template('errors/500.html'), 500

# --- CONTEXT PROCESSORS ---
@app.context_processor
def inject_notifications():
    if 'user_id' not in session:
        return {'unread_notifications_count': 0, 'recent_notifications': []}
    
    try:
        user_id = ObjectId(session['user_id'])
        # Count unread
        count = notifications_collection.count_documents({'user_id': user_id, 'is_read': False})
        # Get recent 5
        recent = list(notifications_collection.find({'user_id': user_id}).sort('created_at', -1).limit(5))
        return {'unread_notifications_count': count, 'recent_notifications': recent}
    except:
        return {'unread_notifications_count': 0, 'recent_notifications': []}


# --- ROUTES ---

@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
        
    # Fetch real data for landing page
    active_jobs_count = jobs_collection.count_documents({'status': 'published'})
    total_students = students_collection.count_documents({})
    companies_count = len(jobs_collection.distinct('company_name'))
    
    # Calculate a mock 'highest package' from jobs if available, otherwise default
    jobs_with_package = list(jobs_collection.find({'package': {'$exists': True, '$ne': ''}}))
    highest_package = "12 LPA" # default
    if jobs_with_package:
        # Try to extract numbers and find max
        import re
        max_val = 0
        for j in jobs_with_package:
            nums = re.findall(r'\d+(?:\.\d+)?', j.get('package', ''))
            if nums:
                try:
                    val = float(nums[0])
                    if val > max_val: max_val = val
                except:
                    pass
        if max_val > 0:
            highest_package = f"{max_val:g} LPA"

    recent_jobs = list(jobs_collection.find({'status': 'published'}).sort('created_at', -1).limit(3))
    
    return render_template('landing.html', 
                           active_jobs_count=active_jobs_count,
                           total_students=total_students,
                           companies_count=companies_count,
                           highest_package=highest_package,
                           recent_jobs=recent_jobs)

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    
    user = users_collection.find_one({'email': email})
    
    if not user:
        flash("Invalid email or password", "error")
        return redirect(url_for('login'))
    
    # Verify role matches
    if user.get('role') != role:
        flash("Invalid role selected or user not found with this role", "error")
        return redirect(url_for('login'))
    
    if verify_password(user['password'], password):
        # Check if student is approved OR needs to complete profile
        if user['role'] == 'student':
            # Case 1: Profile Incomplete -> Must Complete
            if not user.get('profile_completed'):
                session['user_id'] = str(user['_id'])
                session['role'] = user['role']
                return redirect(url_for('complete_profile'))
            
            # Case 2: Profile Completed but Not Approved -> Wait for Super Admin Approval
            if not user.get('is_approved', False):
                student_doc = students_collection.find_one({'user_id': user['_id']})
                student_name = (student_doc.get('name') if student_doc else None) or user.get('name', 'Student')
                return render_template('login.html', pending_approval=True, pending_email=user['email'], pending_role='Student', pending_name=student_name)
        
        # Check if admin/faculty is approved by super admin
        if user['role'] == 'admin' and not user.get('is_approved', False):
            admin_title = 'Faculty Coordinator' if user.get('admin_level') == 'faculty' else 'Administrator'
            admin_name = user.get('full_name') or user.get('name', 'Admin')
            return render_template('login.html', pending_approval=True, pending_email=user['email'], pending_role=admin_title, pending_name=admin_name)
        
        session['user_id'] = str(user['_id'])
        session['role'] = user['role']
        session['email'] = user['email']
        session['admin_level'] = user.get('admin_level', None)  # For admin hierarchy
        
        # Ensure name is in session
        if user['role'] == 'student':
            student_doc = students_collection.find_one({'user_id': user['_id']})
            session['name'] = user.get('name') or (student_doc.get('name') if student_doc else 'Student')
        else:
            session['name'] = user.get('name') or user.get('full_name') or 'Admin'
        
        # Log login with timestamp
        login_logs_collection.insert_one({
            'user_id': user['_id'],
            'email': email,
            'role': user['role'],
            'login_time': datetime.datetime.now(),
            'ip_address': request.remote_addr
        })
        
        # Update last login for user
        users_collection.update_one(
            {'_id': user['_id']},
            {'$set': {'last_login': datetime.datetime.now()}}
        )
        
        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            # Update student is_active status
            students_collection.update_one(
                {'user_id': user['_id']},
                {'$set': {'last_login': datetime.datetime.now(), 'is_active': True}}
            )
            return redirect(url_for('student_dashboard'))
    
    flash("Invalid email or password", "error")
    return redirect(url_for('login'))

@app.route('/student/complete-profile', methods=['GET', 'POST'])
@login_required(role='student')
def complete_profile():
    user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
    student = students_collection.find_one({'user_id': ObjectId(session['user_id'])})

    if request.method == 'POST':
        try:
            # Helper for safe int/float conversion
            def safe_int(val, default=0):
                try:
                    return int(val) if val and str(val).strip() else default
                except (ValueError, TypeError):
                    return default

            def safe_float(val, default=0.0):
                try:
                    return float(val) if val and str(val).strip() else default
                except (ValueError, TypeError):
                    return default

            # 1. Personal Details
            name = request.form.get('name')
            personal_email = request.form.get('personal_email')
            phone = request.form.get('phone')

            if not name or not personal_email or not phone:
                flash("Required personal details are missing.", "error")
                return redirect(url_for('complete_profile'))
            gender = request.form.get('gender')
            dob = request.form.get('dob')
            alt_phone = request.form.get('alt_phone')
            nationality = request.form.get('nationality')
            marital_status = request.form.get('marital_status')
            aadhaar = request.form.get('aadhaar')
            pan = request.form.get('pan')
            
            permanent_address = request.form.get('permanent_address')
            current_address = request.form.get('current_address')

            # 2. Academic Details - Nested Structure (with safe conversions)
            academic = {
                'tenth': {
                    'school': request.form.get('tenth_school'),
                    'board': request.form.get('tenth_board'),
                    'year': safe_int(request.form.get('tenth_year')),
                    'score': safe_float(request.form.get('tenth_score')),
                },
                'twelfth': {
                    'school': request.form.get('twelfth_school'),
                    'board': request.form.get('twelfth_board'),
                    'year': safe_int(request.form.get('twelfth_year')),
                    'score': safe_float(request.form.get('twelfth_score')),
                    'stream': request.form.get('twelfth_stream')
                },
                'ug': {
                    'college': request.form.get('ug_college'),
                    'university': request.form.get('ug_university'),
                    'degree': request.form.get('ug_degree'),
                    'branch': request.form.get('ug_branch'),
                    'year': safe_int(request.form.get('ug_year')),
                    'score': safe_float(request.form.get('ug_score')),
                    'backlogs': safe_int(request.form.get('ug_backlogs')),
                    'backlog_status': request.form.get('ug_backlog_status')
                },
                'pg': {
                    'college': request.form.get('pg_college'),
                    'university': request.form.get('pg_university'),
                    'degree': request.form.get('pg_degree'),
                    'branch': request.form.get('pg_branch'),
                    'year': safe_int(request.form.get('pg_year')) if request.form.get('pg_year') else None,
                    'score': safe_float(request.form.get('pg_score')) if request.form.get('pg_score') else None,
                    'backlogs': safe_int(request.form.get('pg_backlogs')),
                    'backlog_status': request.form.get('pg_backlog_status')
                }
            }
            
            # Simple flattening for primary sorting/filtering
            main_branch = request.form.get('pg_branch') if request.form.get('pg_degree') else request.form.get('ug_branch')
            main_cgpa = safe_float(request.form.get('pg_score') or request.form.get('ug_score'))

            skills = request.form.get('skills', '')
            projects = request.form.get('projects', '')
            
            # File Upload (GridFS)
            resume_file = request.files.get('resume')
            resume_id = None
            
            if resume_file and resume_file.filename != '':
                filename = secure_filename(resume_file.filename)
                content_type = resume_file.content_type
                # Store in GridFS
                fs = get_fs()
                resume_id = fs.put(
                    resume_file.read(), 
                    filename=filename, 
                    content_type=content_type,
                    metadata={'user_id': ObjectId(session['user_id']), 'type': 'resume'}
                )

            # Build update dict
            update_data = {
                'name': name,
                'gender': gender,
                'dob': dob,
                'phone': phone,
                'alt_phone': alt_phone,
                'personal_email': personal_email,
                'nationality': nationality,
                'marital_status': marital_status,
                'aadhaar': aadhaar,
                'pan': pan,
                'address': {
                    'permanent': permanent_address,
                    'current': current_address
                },
                'academic': academic,
                'branch': main_branch,
                'cgpa': main_cgpa,
                'skills': [s.strip() for s in skills.split(',') if s.strip()],
                'projects': projects,
                'profile_updated_at': datetime.datetime.now()
            }
            
            # University Registration / Roll Number (P02DR25S126001 format)
            new_student_id = request.form.get('student_id', '').strip().upper()
            if new_student_id:
                existing_s = students_collection.find_one({
                    'student_id': new_student_id,
                    'user_id': {'$ne': ObjectId(session['user_id'])}
                })
                if existing_s:
                    flash(f"University Registration / Roll Number {new_student_id} is already taken by another student.", "error")
                    return redirect(url_for('complete_profile'))
                update_data['student_id'] = new_student_id
            
            # Only update resume if a new one was uploaded
            if resume_id:
                update_data['resume_file_id'] = resume_id

            # Update Student Profile
            students_collection.update_one(
                {'user_id': ObjectId(session['user_id'])},
                {'$set': update_data}
            )
            
            # Update User Status & Name
            was_approved = user.get('is_approved', False) if user else False
            users_collection.update_one(
                {'_id': ObjectId(session['user_id'])},
                {'$set': {
                    'name': name, # Sync name
                    'profile_completed': True, 
                    'is_approved': was_approved
                }}
            )
            
            if was_approved:
                flash("Profile updated successfully!", "success")
                return redirect(url_for('student_profile'))
            else:
                flash("Profile submitted successfully! Please wait for Super Admin Approval.", "success")
                return redirect(url_for('login'))
            
        except Exception as e:
            import traceback
            traceback.print_exc() # Print full stack trace to server logs
            flash(f"Error saving profile: {str(e)}", "error")
            return redirect(url_for('complete_profile'))

    return render_template('student/complete_profile.html', student=student)

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
@limiter.limit("3 per hour")
def signup_post():
    try:
        role = request.form.get('role')
        
        if role not in ['student', 'admin', 'faculty']:
            flash("Invalid role selected", "error")
            return redirect(url_for('signup'))
        
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if users_collection.find_one({'email': email}):
            flash("Email already registered", "error")
            return redirect(url_for('signup'))
        
        # Student Registration
        if role == 'student':
            roll_no = request.form.get('roll_no', '').strip().upper()
            if not roll_no:
                flash("University Registration / Roll Number is required (e.g. P02DR25S126001).", "error")
                return redirect(url_for('signup'))
            
            import re
            if not re.match(r'^[A-Z0-9]{8,20}$', roll_no):
                flash("Invalid Roll Number format. Expected university pattern like P02DR25S126001 (alphanumeric, 8-20 characters).", "error")
                return redirect(url_for('signup'))
            
            # Check duplicate roll number
            if students_collection.find_one({'student_id': roll_no}):
                flash(f"University Registration / Roll Number '{roll_no}' is already registered in the system.", "error")
                return redirect(url_for('signup'))
            
            student_id_code = roll_no
            
            # Create User with profile_completed = False, is_approved = False
            user_id = users_collection.insert_one({
                'email': email,
                'password': hash_password(password),
                'role': 'student',
                'name': name,
                'is_approved': False,
                'profile_completed': False,  # Flag to trigger profile flow
                'created_at': datetime.datetime.now()
            }).inserted_id
            
            # Create Minimal Student Profile with official Roll / Reg No
            students_collection.insert_one({
                'user_id': user_id,
                'student_id': student_id_code,
                'name': name,
                'registered_at': datetime.datetime.now(),
                'is_active': False
            })
            
            # Notify super admins of new student registration
            super_admins = users_collection.find({'role': 'admin', 'admin_level': 'super_admin'})
            for admin in super_admins:
                notifications_collection.insert_one({
                    'user_id': admin['_id'],
                    'title': '👤 New Student Signup',
                    'message': f"Student {name} ({email}) registered with Roll No: {student_id_code}. Awaiting your approval.",
                    'link': '/admin/dashboard',
                    'is_read': False,
                    'created_at': datetime.datetime.now(),
                    'type': 'registration',
                    'requester_email': email,
                    'requester_id': user_id
                })
            
            flash("Account created! Please sign in and complete your academic profile.", "success")
        
        # Admin/Faculty Registration
        else:  # admin or faculty
            admin_level = request.form.get('admin_level')
            
            if admin_level not in ['super_admin', 'faculty']:
                flash("Invalid admin level selected", "error")
                return redirect(url_for('signup'))
            
            # Create Admin/Faculty User with pending approval
            user_id = users_collection.insert_one({
                'email': email,
                'password': hash_password(password),
                'role': 'admin',
                'admin_level': admin_level,
                'is_approved': False,  # Super admin approval required
                'created_at': datetime.datetime.now(),
                'full_name': name
            }).inserted_id
            
            # Notify all super admins about new admin/faculty registration
            super_admins = users_collection.find({'role': 'admin', 'admin_level': 'super_admin'})
            for admin in super_admins:
                notifications_collection.insert_one({
                    'user_id': admin['_id'],
                    'title': '👤 New Admin Registration',
                    'message': f"New {admin_level} registration from {name} ({email})",
                    'link': '/admin/manage-admins',
                    'is_read': False,
                    'created_at': datetime.datetime.now(),
                    'type': 'admin_registration'
                })
            
            flash("Admin/Faculty registration successful! Pending super admin approval. Please wait for approval before logging in.", "success")
        
        return redirect(url_for('login'))

    except Exception as e:
        flash(f"Error: {e}", "error")
        return redirect(url_for('signup'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = users_collection.find_one({'email': email})
        
        if user:
            # Check for existing pending request
            existing = password_requests_collection.find_one({'email': email, 'status': 'pending'})
            if existing:
                flash("A password reset request is already pending for this email.", "info")
            else:
                password_requests_collection.insert_one({
                    'user_id': user['_id'],
                    'email': email,
                    'status': 'pending',
                    'requested_at': datetime.datetime.now(),
                    'ip_address': request.remote_addr
                })
                # Notify Super Admins
                # (Optional: Add notification logic here if needed)
                
                flash("Password reset request submitted. Please contact the administrator for approval.", "success")
        else:
            # Security: Don't reveal user existence, but behave consistently
            flash("If an account exists, a reset request has been logged.", "info")
            
        return redirect(url_for('login'))
        
    return render_template('forgot_password.html')

# (Reset Password route is no longer accessible directly by token in this flow, 
# but we might keep it if Admin generates a token link using it. 
# Let's keep the route but purely for the link generated by Admin)
@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=86400) # 24 hours validity for admin links
    except Exception:
        flash("The reset link is invalid or has expired.", "error")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(request.url)
            
        if len(password) < 6:
             flash("Password must be at least 6 characters.", "error")
             return redirect(request.url)
             
        # Update Password
        users_collection.update_one(
            {'email': email},
            {'$set': {'password': hash_password(password)}}
        )
        
        # Mark request as completed if exists
        password_requests_collection.update_one(
            {'email': email, 'status': 'pending'},
            {'$set': {'status': 'completed', 'completed_at': datetime.datetime.now()}}
        )
        
        flash("Password reset successful! You can now login.", "success")
        return redirect(url_for('login'))
        
    return render_template('reset_password.html', token=token)

@app.route('/admin/security/requests')
@login_required(role='admin')
def view_password_requests():
    # Only Super Admins
    if session.get('admin_level') != 'super_admin':
        flash("Unauthorized", "error")
        return redirect(url_for('admin_dashboard'))
        
    requests = list(password_requests_collection.find().sort('requested_at', -1))
    return render_template('admin/password_requests.html', requests=requests)

@app.route('/admin/security/approve/<req_id>', methods=['POST'])
@login_required(role='admin')
def approve_password_request(req_id):
    if session.get('admin_level') != 'super_admin':
        return redirect(url_for('admin_dashboard'))
        
    req = password_requests_collection.find_one({'_id': ObjectId(req_id)})
    if not req:
        flash("Request not found", "error")
        return redirect(url_for('view_password_requests'))
        
    # Generate Link
    token = serializer.dumps(req['email'], salt='password-reset-salt')
    reset_link = url_for('reset_password', token=token, _external=True)
    
    # In a real app with SMTP, we would send it. 
    # Here we Flash it to the Admin so they can copy-paste it to the student.
    flash(f"Request Approved. Send this link to the user: {reset_link}", "success_persistent")
    
    password_requests_collection.update_one(
        {'_id': ObjectId(req_id)},
        {'$set': {'status': 'approved', 'approved_at': datetime.datetime.now(), 'approved_by': session['email']}}
    )
    
    return redirect(url_for('view_password_requests'))

@app.route('/admin/security/reject/<req_id>', methods=['POST'])
@login_required(role='admin')
def reject_password_request(req_id):
    if session.get('admin_level') != 'super_admin':
        return redirect(url_for('admin_dashboard'))
        
    password_requests_collection.update_one(
        {'_id': ObjectId(req_id)},
        {'$set': {'status': 'rejected', 'rejected_at': datetime.datetime.now(), 'rejected_by': session['email']}}
    )
    flash("Request rejected", "info")
    return redirect(url_for('view_password_requests'))

@app.route('/offline')
def offline():
    return render_template('offline.html')

from utils.auth import hash_password, verify_password, login_required
from utils.file_manager import remove_duplicates
import os
from bson.objectid import ObjectId

# --- ADMIN ROUTES ---

@app.route('/admin/cleanup-files', methods=['POST'])
@login_required(role='admin')
def cleanup_files():
    admin_level = session.get('admin_level')
    if admin_level != 'super_admin':
        flash("Only Super Admins can perform system maintenance", "error")
        return redirect(url_for('admin_dashboard'))
    
    upload_dir = os.path.join(app.root_path, 'static', 'uploads')
    removed = remove_duplicates(upload_dir)
    
    if removed:
        flash(f"Cleanup complete. Removed {len(removed)} duplicate files.", "success")
    else:
        flash("System is clean. No duplicate files found.", "info")
            
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/student/<user_id>')
@login_required(role='admin')
def view_student_details(user_id):
    # Only super admins or authorized faculty should view full details
    admin_level = session.get('admin_level')
    if admin_level not in ['super_admin', 'faculty']:
        flash("Unauthorized access", "error")
        return redirect(url_for('admin_dashboard'))

    try:
        # Fetch user and student docs
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        student = students_collection.find_one({'user_id': ObjectId(user_id)})
        
        if not user or not student:
            flash("Student not found", "error")
            return redirect(url_for('manage_users'))

        return render_template('admin/student_details.html', user=user, student=student)
    except Exception as e:
        flash(f"Error fetching student details: {str(e)}", "error")
        return redirect(url_for('manage_users'))

@app.route('/admin/student/<user_id>/resume')
@login_required(role='admin')
def view_student_resume(user_id):
    # Route to serve resume from GridFS if needed, or redirect to static if stored there.
    # Based on complete_profile, resumes are stored in GridFS.
    try:
        student = students_collection.find_one({'user_id': ObjectId(user_id)})
        if not student or 'academic' not in student: 
             # Fallback check if stored directly or if using previous schema
             pass

        # Check for resume_id in student doc (schema from complete_profile didn't explicitly show where resume_id is saved in student doc separate from fs, assuming logic handles it or we need to find it by metadata)
        # Actually complete_profile code: metadata={'user_id': ...}
        # Let's find the file by metadata
        fs = get_fs()
        resume_file = fs.find_one({"metadata.user_id": ObjectId(user_id), "metadata.type": 'resume'})
        
        if not resume_file:
             flash("Resume not found", "error")
             return redirect(url_for('view_student_details', user_id=user_id))
        
        from flask import Response
        return Response(resume_file.read(), mimetype=resume_file.content_type)

    except Exception as e:
        flash(f"Error accessing resume: {str(e)}", "error")
        return redirect(url_for('view_student_details', user_id=user_id))

# --- Helper: Auto-expire jobs past their deadline ---
def auto_expire_jobs():
    """Automatically mark published jobs as expired if past their expires_at date."""
    now = datetime.datetime.now()
    result = jobs_collection.update_many(
        {
            'status': {'$ne': 'expired'},
            'expires_at': {'$lt': now, '$ne': None}
        },
        {'$set': {'status': 'expired'}}
    )
    return result.modified_count

@app.route('/admin/dashboard')
@login_required(role='admin')
def admin_dashboard():
    # Auto-expire jobs on dashboard load
    auto_expire_jobs()
    # Check if user is super admin or faculty
    admin_level = session.get('admin_level')
    
    total_students = students_collection.count_documents({})
    placed_count = len(applications_collection.distinct('student_id', {'status': 'Selected'}))
    placement_rate = round((placed_count / max(total_students, 1)) * 100, 1)

    stats = {
        'total_jobs': jobs_collection.count_documents({}),
        'total_students': total_students,
        'total_applications': applications_collection.count_documents({}),
        'placed_count': placed_count,
        'placement_rate': placement_rate
    }
    
    # Chart Data: Application Status Distribution
    pipeline = [
        {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
    ]
    status_counts = list(applications_collection.aggregate(pipeline))
    chart_data = {item['_id']: item['count'] for item in status_counts}
    for status in ['Applied', 'Shortlisted', 'GD', 'Interview', 'Selected', 'Rejected']:
        if status not in chart_data:
            chart_data[status] = 0

    jobs = list(jobs_collection.find().sort('created_at', -1).limit(6))
    for j in jobs:
        j['applicant_count'] = applications_collection.count_documents({'job_id': j['_id']})
        j['shortlisted_count'] = applications_collection.count_documents({'job_id': j['_id'], 'status': {'$in': ['Shortlisted', 'GD', 'Interview', 'Selected']}})

    announcements = list(announcements_collection.find().sort('created_at', -1).limit(5))
    
    # Get pending students for approval (only super admins)
    pending_students = []
    urgent_notifications = []
    if admin_level == 'super_admin':
        pipeline = [
            {'$match': {'is_approved': False}},
            {'$lookup': {
                'from': 'students',
                'let': {'user_id': '$_id'},
                'pipeline': [{'$match': {'$expr': {'$eq': ['$user_id', '$$user_id']}}}],
                'as': 'student_info'
            }},
            {'$unwind': {'path': '$student_info', 'preserveNullAndEmptyArrays': True}},
            {'$sort': {'created_at': -1}}
        ]
        pending_students = list(users_collection.aggregate(pipeline))
        
        # Fetch unread urgent approval requests & registration notifications for Super Admin
        urgent_notifications = list(notifications_collection.find({
            'user_id': ObjectId(session['user_id']),
            'type': {'$in': ['approval_reminder', 'registration', 'admin_registration']},
            'is_read': False
        }).sort('created_at', -1).limit(15))
        
        urgent_emails = {n.get('requester_email') for n in urgent_notifications if n.get('requester_email')}
        for u in pending_students:
            u['has_urgent_reminder'] = u.get('email') in urgent_emails
    
    # Add pending approvals to stats
    stats['pending_approvals'] = len(pending_students)
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         jobs=jobs, 
                         announcements=announcements, 
                         chart_data=chart_data,
                         admin_level=admin_level,
                         pending_students=pending_students,
                         urgent_notifications=urgent_notifications)

@app.route('/admin/jobs/add', methods=['POST'])
@login_required(role='admin')
def add_job():
    # Check if user has permission (super_admin or faculty)
    admin_level = session.get('admin_level')
    if admin_level not in ['super_admin', 'faculty']:
        flash("You don't have permission to post jobs", "error")
        return redirect(url_for('admin_dashboard'))
    
    # Gather and validate form fields
    try:
        company = request.form.get('company', '').strip()
        role_name = request.form.get('role', '').strip()
        description = request.form.get('description', '').strip()
        package = request.form.get('package', '').strip()
        location = request.form.get('location', '').strip()
        employment_type = request.form.get('employment_type', '').strip()
        min_cgpa_str = request.form.get('min_cgpa', '')
        drive_date_raw = request.form.get('drive_date', '')
        expires_at_raw = request.form.get('expires_at', '')
        action = request.form.get('action', 'draft')

        # Basic required validations
        if not company:
            flash("Company name is required", "error")
            return redirect(url_for('manage_jobs'))
        
        if not role_name:
            flash("Job role is required", "error")
            return redirect(url_for('manage_jobs'))
        
        if not description or len(description) < 20:
            flash("Description is required and must be at least 20 characters", "error")
            return redirect(url_for('manage_jobs'))

        # Parse numeric fields
        min_cgpa = 0.0
        if min_cgpa_str:
            try:
                min_cgpa = float(min_cgpa_str)
                if min_cgpa < 0 or min_cgpa > 10:
                    min_cgpa = 0.0
            except ValueError:
                min_cgpa = 0.0

        # Parse dates if provided
        drive_date = None
        expires_at = None
        try:
            if drive_date_raw:
                drive_date = datetime.datetime.strptime(drive_date_raw, '%Y-%m-%d')
        except Exception:
            pass
        
        try:
            if expires_at_raw:
                expires_at = datetime.datetime.strptime(expires_at_raw, '%Y-%m-%d')
        except Exception:
            pass

        # Handle File Upload
        attachment = request.files.get('attachment')
        attachment_id = None
        if attachment and attachment.filename:
            try:
                fs = get_fs()
                filename = secure_filename(attachment.filename)
                attachment_id = fs.put(
                    attachment.read(),
                    filename=filename,
                    content_type=attachment.content_type,
                    metadata={'uploaded_by': session['user_id'], 'type': 'job_attachment'}
                )
            except Exception as e:
                flash(f"Error uploading file: {e}", "error")
        
        url = request.form.get('url', '').strip()

        job_doc = {
            'company_name': company,
            'role': role_name,
            'description': description,
            'package': package,
            'location': location,
            'employment_type': employment_type,
            'min_cgpa': min_cgpa,
            'drive_date': drive_date,
            'expires_at': expires_at,
            'attachment_id': attachment_id,
            'external_url': url,
            'created_by': session.get('email'),
            'created_by_id': ObjectId(session['user_id']),
            'author_role': admin_level,
            'status': 'published' if action == 'publish' else 'draft',
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now(),
            'published_at': datetime.datetime.now() if action == 'publish' else None
        }

        result = jobs_collection.insert_one(job_doc)

        # Only notify students if the job is published
        if action == 'publish':
            # Smart Notification: Only notify eligible students
            query = {'is_active': True}
            if min_cgpa > 0:
                query['cgpa'] = {'$gte': min_cgpa}
                
            students = list(students_collection.find(query, {'user_id': 1, 'name': 1, 'cgpa': 1}))
            notifications = []
            
            for s in students:
                notifications.append({
                    'user_id': s['user_id'],
                    'title': f"🎯 New Job: {company}",
                    'message': f"Position: {role_name}. You are eligible! Check details.",
                    'link': '/student/jobs',
                    'is_read': False,
                    'created_at': datetime.datetime.now(),
                    'type': 'job_posting',
                    'meta': {'job_id': str(result.inserted_id)}
                })
            
            if notifications:
                notifications_collection.insert_many(notifications)
            
            flash(f"Job published! Notifications sent to {len(notifications)} eligible students.", "success")
        else:
            flash("Job saved as draft.", "success")

        return redirect(url_for('manage_jobs'))

    except Exception as e:
        flash(f"Error posting job: {str(e)}", "error")
        return redirect(url_for('manage_jobs'))

# --- ADMIN USER MANAGEMENT ROUTES (Super Admin Only) ---

@app.route('/admin/manage-users')
@login_required(role='admin')
def manage_users():
    admin_level = session.get('admin_level')
    if admin_level != 'super_admin':
        flash("Only Super Admins can manage users", "error")
        return redirect(url_for('admin_dashboard'))
    
    # Get all users with their login history
    pipeline = [
        {
            '$lookup': {
                'from': 'students',
                'let': {'user_id': '$_id'},
                'pipeline': [{'$match': {'$expr': {'$eq': ['$user_id', '$$user_id']}}}],
                'as': 'student_info'
            }
        },
        {
            '$lookup': {
                'from': 'login_logs',
                'let': {'user_id': '$_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$eq': ['$user_id', '$$user_id']}}},
                    {'$sort': {'login_time': -1}},
                    {'$limit': 1}
                ],
                'as': 'last_login_info'
            }
        },
        {'$sort': {'created_at': -1}}
    ]
    all_users = list(users_collection.aggregate(pipeline))
    
    # Format for display
    for user in all_users:
        user['_id'] = str(user['_id'])
        if user.get('student_info'):
            user['student_info'] = user['student_info'][0] if user['student_info'] else {}
        if user.get('last_login_info'):
            user['last_login_info'] = user['last_login_info'][0] if user['last_login_info'] else {}
    
    return render_template('admin/manage_users.html', users=all_users)

@app.route('/admin/approve-student/<user_id>', methods=['POST'])
@login_required(role='admin')
def approve_student(user_id):
    admin_level = session.get('admin_level')
    if admin_level != 'super_admin':
        flash("Only Super Admins can approve students", "error")
        return redirect(url_for('admin_dashboard'))
    
    try:
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'is_approved': True, 'approved_at': datetime.datetime.now(), 'approved_by': session['email']}}
        )
        
        # Send notification to student
        student = students_collection.find_one({'user_id': ObjectId(user_id)})
        if student:
            notifications_collection.insert_one({
                'user_id': ObjectId(user_id),
                'title': 'Account Approved',
                'message': f"Hello {student['name']}, your account has been approved! You can now login.",
                'link': '/student/dashboard',
                'is_read': False,
                'created_at': datetime.datetime.now()
            })
        
        flash("Student approved successfully!", "success")
    except Exception as e:
        flash(f"Error: {e}", "error")
    
    return redirect(url_for('manage_users'))

@app.route('/admin/reject-student/<user_id>', methods=['POST'])
@login_required(role='admin')
def reject_student(user_id):
    admin_level = session.get('admin_level')
    if admin_level != 'super_admin':
        flash("Only Super Admins can reject students", "error")
        return redirect(url_for('admin_dashboard'))
    
    try:
        users_collection.delete_one({'_id': ObjectId(user_id)})
        students_collection.delete_one({'user_id': ObjectId(user_id)})
        flash("Student rejected and removed", "success")
    except Exception as e:
        flash(f"Error: {e}", "error")
    
    return redirect(url_for('manage_users'))

@app.route('/admin/approve-user/<user_id>', methods=['POST'])
@login_required(role='admin')
def approve_user(user_id):
    """Super Admin: Universal approval for student, faculty, or admin accounts."""
    if session.get('admin_level') != 'super_admin':
        flash("Only Super Admins can authorize user registrations.", "error")
        return redirect(url_for('admin_dashboard'))
    
    try:
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            flash("User not found.", "error")
            return redirect(request.referrer or url_for('admin_dashboard'))
        
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'is_approved': True, 'approved_at': datetime.datetime.now(), 'approved_by': session.get('email')}}
        )
        
        # If student, activate profile
        if user.get('role') == 'student':
            students_collection.update_one(
                {'user_id': ObjectId(user_id)},
                {'$set': {'is_active': True}}
            )
            student = students_collection.find_one({'user_id': ObjectId(user_id)})
            student_name = (student.get('name') if student else None) or user.get('name', 'Student')
            notifications_collection.insert_one({
                'user_id': ObjectId(user_id),
                'title': '🎉 Account Approved',
                'message': f"Hello {student_name}, your account has been approved by Super Admin! You can now access all drives and placement services.",
                'link': '/student/dashboard',
                'is_read': False,
                'created_at': datetime.datetime.now()
            })
        else:
            admin_name = user.get('full_name') or user.get('name', 'Admin')
            notifications_collection.insert_one({
                'user_id': ObjectId(user_id),
                'title': '🎉 Admin Account Approved',
                'message': f"Hello {admin_name}, your administrative access has been verified and approved by Super Admin.",
                'link': '/admin/dashboard',
                'is_read': False,
                'created_at': datetime.datetime.now()
            })
            
        # Mark all related approval reminders as read
        notifications_collection.update_many(
            {'requester_email': user.get('email')},
            {'$set': {'is_read': True}}
        )
        
        flash(f"Account for {user.get('email')} approved successfully!", "success")
    except Exception as e:
        flash(f"Error approving user: {e}", "error")
        
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/admin/reject-user/<user_id>', methods=['POST'])
@login_required(role='admin')
def reject_user(user_id):
    """Super Admin: Universal rejection and removal for any pending registration."""
    if session.get('admin_level') != 'super_admin':
        flash("Only Super Admins can reject accounts.", "error")
        return redirect(url_for('admin_dashboard'))
        
    try:
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        if user:
            users_collection.delete_one({'_id': ObjectId(user_id)})
            students_collection.delete_one({'user_id': ObjectId(user_id)})
            notifications_collection.delete_many({'requester_email': user.get('email')})
            flash(f"Registration for {user.get('email')} has been rejected and removed.", "success")
    except Exception as e:
        flash(f"Error rejecting user: {e}", "error")
        
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/notify-admin-approval', methods=['POST'])
def notify_admin_approval():
    """Allows unapproved users to send an urgent authorization notification to Super Admins."""
    email = request.form.get('email', '').strip()
    if not email:
        flash("Email is required.", "error")
        return redirect(url_for('login'))
        
    user = users_collection.find_one({'email': email})
    if not user:
        flash("Account not found.", "error")
        return redirect(url_for('login'))
        
    if user.get('is_approved', False):
        flash("Your account is already approved! You can log in directly.", "success")
        return redirect(url_for('login'))
        
    user_name = user.get('name') or user.get('full_name', 'Applicant')
    role_desc = 'Student' if user.get('role') == 'student' else (user.get('admin_level') or 'Admin/Faculty')
    
    roll_info = ""
    if user.get('role') == 'student':
        s_doc = students_collection.find_one({'user_id': user['_id']})
        if s_doc and s_doc.get('student_id'):
            roll_info = f" (Roll No: {s_doc['student_id']})"
            
    super_admins = list(users_collection.find({'role': 'admin', 'admin_level': 'super_admin'}))
    for sa in super_admins:
        notifications_collection.insert_one({
            'user_id': sa['_id'],
            'title': '🚨 Urgent Approval Request',
            'message': f"{user_name} ({email}, {role_desc}{roll_info}) is awaiting approval and requested immediate authorization.",
            'link': '/admin/dashboard',
            'is_read': False,
            'created_at': datetime.datetime.now(),
            'type': 'approval_reminder',
            'requester_email': email,
            'requester_id': user['_id']
        })
        
    flash(f"Super Admin notified! An urgent authorization alert has been sent for {email}.", "success")
    return redirect(url_for('login'))

@app.route('/student/update-roll-no', methods=['POST'])
@login_required(role='student')
def update_roll_no():
    """Allow student to update their university roll number / registration number anytime."""
    roll_no = request.form.get('roll_no', '').strip().upper()
    if not roll_no:
        flash("University Registration / Roll Number cannot be empty.", "error")
        return redirect(url_for('student_profile'))
        
    import re
    if not re.match(r'^[A-Z0-9]{8,20}$', roll_no):
        flash("Invalid Roll Number format. Expected pattern like P02DR25S126001 (alphanumeric, 8-20 characters).", "error")
        return redirect(url_for('student_profile'))
        
    # Check duplicate
    existing = students_collection.find_one({
        'student_id': roll_no,
        'user_id': {'$ne': ObjectId(session['user_id'])}
    })
    if existing:
        flash(f"University Registration / Roll Number '{roll_no}' is already assigned to another student.", "error")
        return redirect(url_for('student_profile'))
        
    students_collection.update_one(
        {'user_id': ObjectId(session['user_id'])},
        {'$set': {'student_id': roll_no}}
    )
    flash(f"University Registration / Roll Number updated to '{roll_no}' successfully!", "success")
    return redirect(url_for('student_profile'))

@app.route('/admin/users/batch-approve', methods=['POST'])
@login_required(role='admin')
def batch_approve_students():
    """TPO Manual Work Reduction Engine: Approve all or selected student accounts in 1 click."""
    admin_level = session.get('admin_level')
    if admin_level != 'super_admin':
        flash("Only Super Admins can approve students", "error")
        return redirect(url_for('admin_dashboard'))
    
    user_ids = request.form.getlist('selected_user_ids')
    approve_all = request.form.get('approve_all') == 'true'
    
    query = {'is_approved': False, 'role': 'student'}
    if not approve_all:
        if not user_ids:
            flash("No students selected for approval.", "warning")
            return redirect(url_for('manage_users'))
        valid_oids = []
        for uid in user_ids:
            try:
                valid_oids.append(ObjectId(uid))
            except Exception:
                pass
        query['_id'] = {'$in': valid_oids}
    
    pending_users = list(users_collection.find(query))
    if not pending_users:
        flash("No matching pending student accounts found.", "info")
        return redirect(url_for('manage_users'))
        
    p_ids = [u['_id'] for u in pending_users]
    users_collection.update_many(
        {'_id': {'$in': p_ids}},
        {'$set': {'is_approved': True, 'approved_at': datetime.datetime.now(), 'approved_by': session['email']}}
    )
    
    notifs = []
    for u in pending_users:
        notifs.append({
            'user_id': u['_id'],
            'title': 'Account Approved',
            'message': "Your student placement account has been approved! You can now apply for recruitment drives.",
            'link': '/student/dashboard',
            'is_read': False,
            'created_at': datetime.datetime.now(),
            'type': 'system'
        })
    if notifs:
        notifications_collection.insert_many(notifs)
        
    flash(f"Successfully approved {len(p_ids)} student account(s) in 1 click!", "success")
    return redirect(url_for('manage_users'))

@app.route('/admin/student/<user_id>/toggle-verify', methods=['POST'])
@login_required(role='admin')
def toggle_verify_student(user_id):
    """TPO Anti-Tampering Engine: Officially verify and freeze or unlock student academic credentials."""
    admin_level = session.get('admin_level')
    if admin_level not in ['super_admin', 'faculty']:
        flash("Unauthorized access", "error")
        return redirect(url_for('admin_dashboard'))
        
    try:
        student = students_collection.find_one({'user_id': ObjectId(user_id)})
        if not student:
            flash("Student profile not found.", "error")
            return redirect(request.referrer or url_for('manage_users'))
            
        new_status = not student.get('is_verified', False)
        update_data = {
            'is_verified': new_status,
            'is_locked': new_status,
            'verified_at': datetime.datetime.now() if new_status else None,
            'verified_by': session.get('email') if new_status else None
        }
        students_collection.update_one({'user_id': ObjectId(user_id)}, {'$set': update_data})
        
        if new_status:
            notif_msg = "Your academic profile has been verified and locked by the Placement Cell. Your credentials are now certified for recruiter master sheets."
            notif_title = "✓ Profile Officially Verified"
        else:
            notif_msg = "Your academic profile lock has been released by the Placement Cell coordinator. You may update your academic records."
            notif_title = "Academic Profile Unlocked"
            
        notifications_collection.insert_one({
            'user_id': ObjectId(user_id),
            'title': notif_title,
            'message': notif_msg,
            'link': '/student/profile',
            'is_read': False,
            'created_at': datetime.datetime.now(),
            'type': 'verification'
        })
        
        status_text = "verified & locked" if new_status else "unlocked"
        flash(f"Student profile successfully {status_text}.", "success")
    except Exception as e:
        flash(f"Error updating verification status: {str(e)}", "error")
        
    return redirect(request.referrer or url_for('manage_users'))

@app.route('/admin/manage-admins')
@login_required(role='admin')
def manage_admins():
    admin_level = session.get('admin_level')
    if admin_level != 'super_admin':
        flash("Only Super Admins can manage admins", "error")
        return redirect(url_for('admin_dashboard'))
    
    # Get all admin users
    admins = list(users_collection.find(
        {'role': 'admin'},
        {'email': 1, 'admin_level': 1, 'created_at': 1, 'is_approved': 1}
    ).sort('created_at', -1))
    
    for admin in admins:
        admin['_id'] = str(admin['_id'])
    
    # Separate pending and approved
    pending = [a for a in admins if not a.get('is_approved', False)]
    approved = [a for a in admins if a.get('is_approved', False)]
    
    return render_template('admin/manage_admins.html', admins=admins, pending=pending, approved=approved)

@app.route('/admin/change-admin-level/<admin_id>', methods=['POST'])
@login_required(role='admin')
def change_admin_level(admin_id):
    admin_level = session.get('admin_level')
    if admin_level != 'super_admin':
        flash("Only Super Admins can change admin levels", "error")
        return redirect(url_for('admin_dashboard'))
    
    new_level = request.form.get('level')  # 'super_admin' or 'faculty'
    
    if new_level not in ['super_admin', 'faculty']:
        flash("Invalid admin level", "error")
        return redirect(url_for('manage_admins'))
    
    try:
        users_collection.update_one(
            {'_id': ObjectId(admin_id)},
            {'$set': {'admin_level': new_level}}
        )
        flash(f"Admin level changed to {new_level}", "success")
    except Exception as e:
        flash(f"Error: {e}", "error")
    
    return redirect(url_for('manage_admins'))

@app.route('/admin/approve-admin/<admin_id>', methods=['POST'])
@login_required(role='admin')
def approve_admin(admin_id):
    admin_level = session.get('admin_level')
    if admin_level != 'super_admin':
        flash("Only Super Admins can approve admins", "error")
        return redirect(url_for('admin_dashboard'))
    
    try:
        admin_user = users_collection.find_one({'_id': ObjectId(admin_id)})
        users_collection.update_one(
            {'_id': ObjectId(admin_id)},
            {'$set': {'is_approved': True, 'approved_at': datetime.datetime.now(), 'approved_by': session['email']}}
        )
        
        # Create notification for admin
        notifications_collection.insert_one({
            'user_id': ObjectId(admin_id),
            'title': 'Admin Account Approved',
            'message': f"Your admin account has been approved! You can now login as {admin_user.get('admin_level', 'faculty')}.",
            'link': '/admin/dashboard',
            'is_read': False,
            'created_at': datetime.datetime.now()
        })
        
        flash("Admin approved successfully!", "success")
    except Exception as e:
        flash(f"Error: {e}", "error")
    
    return redirect(url_for('manage_admins'))

@app.route('/admin/reject-admin/<admin_id>', methods=['POST'])
@login_required(role='admin')
def reject_admin(admin_id):
    admin_level = session.get('admin_level')
    if admin_level != 'super_admin':
        flash("Only Super Admins can reject admins", "error")
        return redirect(url_for('admin_dashboard'))
    
    try:
        users_collection.delete_one({'_id': ObjectId(admin_id)})
        flash("Admin rejected and removed", "success")
    except Exception as e:
        flash(f"Error: {e}", "error")
    
    return redirect(url_for('manage_admins'))

@app.route('/admin/view-login-history')
@login_required(role='admin')
def view_login_history():
    admin_level = session.get('admin_level')
    if admin_level != 'super_admin':
        flash("Only Super Admins can view login history", "error")
        return redirect(url_for('admin_dashboard'))
    
    # Get login history for all users
    logs = list(login_logs_collection.find().sort('login_time', -1).limit(500))
    
    for log in logs:
        log['_id'] = str(log['_id'])
        log['user_id'] = str(log['user_id'])
    
    return render_template('admin/login_history.html', logs=logs)

@app.route('/admin/students-activity')
@login_required(role='admin')
def students_activity():
    admin_level = session.get('admin_level')
    if admin_level != 'super_admin':
        flash("Only Super Admins can view student activity", "error")
        return redirect(url_for('admin_dashboard'))
    
    # Get all students with last login info
    pipeline = [
        {
            '$lookup': {
                'from': 'login_logs',
                'let': {'user_id': '$user_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$eq': ['$user_id', '$$user_id']}}},
                    {'$sort': {'login_time': -1}},
                    {'$limit': 1}
                ],
                'as': 'last_login'
            }
        },
        {'$sort': {'registered_at': -1}}
    ]
    
    students = list(students_collection.aggregate(pipeline))
    
    for student in students:
        student['_id'] = str(student['_id'])
        student['user_id'] = str(student['user_id'])
        student['last_login'] = student['last_login'][0] if student['last_login'] else None
    
    return render_template('admin/students_activity.html', students=students)

@app.route('/admin/send-notification/<student_id>', methods=['POST'])
@login_required(role='admin')
def send_notification_to_student(student_id):
    admin_level = session.get('admin_level')
    if admin_level != 'super_admin':
        flash("Only Super Admins can send notifications", "error")
        return redirect(url_for('admin_dashboard'))
    
    title = request.form.get('title')
    message = request.form.get('message')
    
    try:
        notifications_collection.insert_one({
            'user_id': ObjectId(student_id),
            'title': title,
            'message': message,
            'link': '/student/dashboard',
            'is_read': False,
            'created_at': datetime.datetime.now(),
            'sent_by_admin': session['email']
        })
        flash("Notification sent successfully!", "success")
    except Exception as e:
        flash(f"Error: {e}", "error")
    
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/admin/jobs/manage')
@login_required(role='admin')
def manage_jobs():
    # Auto-expire jobs before listing
    auto_expire_jobs()
    jobs = list(jobs_collection.find().sort('created_at', -1))
    
    # Prepare jobs for both display (datetimes) and JSON (strings)
    for job in jobs:
        # Create a safe copy for JSON serialization
        job_safe = job.copy()
        for key, value in job_safe.items():
            if isinstance(value, ObjectId):
                job_safe[key] = str(value)
            elif isinstance(value, datetime.datetime):
                job_safe[key] = value.isoformat()
        
        # Attach the safe dictionary to the job object for the template to use
        job['safe_data'] = job_safe

    return render_template('admin/manage_jobs.html', jobs=jobs)

@app.route('/admin/jobs/delete/<job_id>', methods=['POST'])
@login_required(role='admin')
def delete_job(job_id):
    jobs_collection.delete_one({'_id': ObjectId(job_id)})
    # Also delete associated applications
    applications_collection.delete_many({'job_id': ObjectId(job_id)})
    flash("Job and associated applications deleted", "success")
    return redirect(url_for('manage_jobs'))




@app.route('/admin/jobs/<job_id>/publish', methods=['POST'])
@login_required(role='admin')
def publish_job(job_id):
    """Publish a draft or expired job with valid future expiration"""
    try:
        job = jobs_collection.find_one({'_id': ObjectId(job_id)})
        if not job:
            flash("Job not found", "error")
            return redirect(url_for('manage_jobs'))
        
        # Check authorization
        if str(job.get('created_by_id')) != session.get('user_id') and session.get('admin_level') not in ['super_admin', 'faculty']:
            flash("You don't have permission to publish this job", "error")
            return redirect(url_for('manage_jobs'))
        
        # Ensure expires_at is in the future so auto_expire_jobs() does not immediately re-expire it
        now = datetime.datetime.now()
        current_expiry = job.get('expires_at')
        new_expiry = current_expiry
        if not current_expiry or current_expiry < now:
            new_expiry = now + datetime.timedelta(days=30)
        
        # Publish the job
        jobs_collection.update_one(
            {'_id': ObjectId(job_id)},
            {'$set': {
                'status': 'published',
                'is_published': True,
                'expires_at': new_expiry,
                'published_at': now,
                'updated_at': now
            }}
        )
        
        # Send notifications
        students = list(students_collection.find({}, {'user_id': 1}))
        notifications = []
        for s in students:
            notifications.append({
                'user_id': s['user_id'],
                'title': f"New Job: {job.get('company_name')}",
                'message': f"Position '{job.get('role')}' is now open for applications.",
                'link': '/student/jobs',
                'is_read': False,
                'created_at': datetime.datetime.now(),
                'meta': {'job_id': ObjectId(job_id)}
            })
        if notifications:
            notifications_collection.insert_many(notifications)
            
        flash(f"Job '{job.get('company_name')}' published successfully with deadline extended to {new_expiry.strftime('%d %b %Y')}!", "success")
        return redirect(url_for('manage_jobs'))
    except Exception as e:
        flash(f"Error publishing job: {str(e)}", "error")
        return redirect(url_for('manage_jobs'))

@app.route('/admin/jobs/republish-expired', methods=['POST'])
@login_required(role='admin')
def republish_expired_jobs():
    """1-Click action for TPO: Extend all expired recruitment drives by 30 days and republish them."""
    try:
        now = datetime.datetime.now()
        future_date = now + datetime.timedelta(days=30)
        result = jobs_collection.update_many(
            {'status': 'expired'},
            {'$set': {
                'status': 'published',
                'is_published': True,
                'expires_at': future_date,
                'updated_at': now
            }}
        )
        flash(f"Successfully republished {result.modified_count} expired drive(s) with application deadline extended to {future_date.strftime('%d %b %Y')}!", "success")
    except Exception as e:
        flash(f"Error republishing expired drives: {str(e)}", "error")
    return redirect(url_for('manage_jobs'))



@app.route('/admin/announcements/add', methods=['POST'])
@login_required(role='admin')
def add_announcement():
    try:
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', 'General').strip()
        priority = request.form.get('priority', 'normal').strip()
        action = request.form.get('action', 'draft')
        target_all_students = request.form.get('target_all_students') == 'on'
        publish_date_raw = request.form.get('publish_date', '')
        expiry_date_raw = request.form.get('expiry_date', '')

        # Validation
        if not title or len(title) < 3:
            flash("Title is required and must be at least 3 characters", "error")
            return redirect(url_for('manage_announcements'))
        
        if not content or len(content) < 20:
            flash("Content is required and must be at least 20 characters", "error")
            return redirect(url_for('manage_announcements'))

        # Parse dates
        published_at = None
        expires_at = None
        
        if action == 'publish':
            published_at = datetime.datetime.now()
        
        if expiry_date_raw:
            try:
                expires_at = datetime.datetime.fromisoformat(expiry_date_raw)
            except Exception:
                pass

        # Handle File Upload
        attachment = request.files.get('attachment')
        attachment_id = None
        if attachment and attachment.filename:
            try:
                fs = get_fs()
                filename = secure_filename(attachment.filename)
                attachment_id = fs.put(
                    attachment.read(),
                    filename=filename,
                    content_type=attachment.content_type,
                    metadata={'uploaded_by': session['user_id'], 'type': 'townhall_attachment'}
                )
            except Exception as e:
                flash(f"Error uploading file: {e}", "error")
        
        url = request.form.get('url', '').strip()

        ann = {
            'title': title,
            'content': content,
            'category': category,
            'priority': priority,
            'created_by': session.get('email'),
            'created_by_id': ObjectId(session['user_id']),
            'author_role': session.get('admin_level'),
            'status': 'published' if action == 'publish' else 'draft',
            'target_all_students': target_all_students,
            'attachment_id': attachment_id,
            'external_url': url,
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now(),
            'published_at': published_at,
            'expires_at': expires_at
        }

        res = announcements_collection.insert_one(ann)

        if action == 'publish' and target_all_students:
            students = list(students_collection.find({}, {'user_id': 1, 'name': 1}))
            notifications = []
            priority_icon = '🚨' if priority == 'urgent' else '⚠️' if priority == 'high' else '📢'
            for s in students:
                notifications.append({
                    'user_id': s['user_id'],
                    'title': f"{priority_icon} {category}: {title}",
                    'message': f"{content[:150]}..." if len(content) > 150 else content,
                    'link': '/student/dashboard',
                    'is_read': False,
                    'created_at': datetime.datetime.now(),
                    'type': 'announcement',
                    'meta': {'announcement_id': str(res.inserted_id)}
                })
            if notifications:
                notifications_collection.insert_many(notifications)
            flash("Announcement published successfully! Notifications sent to all students.", "success")
        else:
            flash("Announcement saved successfully." if action == 'draft' else "Announcement published.", "success")

        return redirect(url_for('manage_announcements'))

    except Exception as e:
        flash(f"Error creating announcement: {str(e)}", "error")
        return redirect(url_for('manage_announcements'))


@app.route('/admin/jobs/edit/<job_id>', methods=['POST'])
@login_required(role='admin')
def edit_job(job_id):
    try:
        job_obj = jobs_collection.find_one({'_id': ObjectId(job_id)})
        if not job_obj:
            flash("Job not found", "error")
            return redirect(url_for('manage_jobs'))

        # Authorization: allow if author or super_admin/faculty
        admin_level = session.get('admin_level')
        if str(job_obj.get('created_by_id')) != session.get('user_id') and admin_level not in ['super_admin', 'faculty']:
            # allow admins with proper level
            pass

        # Update fields
        company = request.form.get('company')
        role_name = request.form.get('role')
        description = request.form.get('description', '')
        package = request.form.get('package', '')
        location = request.form.get('location', '')
        employment_type = request.form.get('employment_type', '')
        min_cgpa = float(request.form.get('min_cgpa') or job_obj.get('min_cgpa', 0))
        drive_date_raw = request.form.get('drive_date')
        expires_at_raw = request.form.get('expires_at')
        publish_action = request.form.get('action') == 'publish'

        # Parse dates
        try:
            drive_date = datetime.datetime.fromisoformat(drive_date_raw) if drive_date_raw else job_obj.get('drive_date')
        except Exception:
            drive_date = drive_date_raw or job_obj.get('drive_date')
        try:
            expires_at = datetime.datetime.fromisoformat(expires_at_raw) if expires_at_raw else job_obj.get('expires_at')
        except Exception:
            expires_at = expires_at_raw or job_obj.get('expires_at')

        # Handle File Upload
        attachment = request.files.get('attachment')
        attachment_id = job_obj.get('attachment_id') # Default to existing
        if attachment and attachment.filename:
            try:
                fs = get_fs()
                filename = secure_filename(attachment.filename)
                attachment_id = fs.put(
                    attachment.read(),
                    filename=filename,
                    content_type=attachment.content_type,
                    metadata={'uploaded_by': session['user_id'], 'type': 'job_attachment'}
                )
            except Exception as e:
                flash(f"Error uploading file: {e}", "error")
        
        url = request.form.get('url', '').strip()

        update_doc = {
            'company_name': company or job_obj.get('company_name'),
            'role': role_name or job_obj.get('role'),
            'description': description,
            'package': package,
            'location': location,
            'employment_type': employment_type,
            'min_cgpa': min_cgpa,
            'drive_date': drive_date,
            'expires_at': expires_at,
            'attachment_id': attachment_id,
            'external_url': url,
            'status': 'published' if publish_action else job_obj.get('status', 'draft'),
            'is_published': bool(publish_action) or job_obj.get('is_published', False),
            'updated_at': datetime.datetime.now(),
        }

        if publish_action and not job_obj.get('is_published'):
            update_doc['published_at'] = datetime.datetime.now()

        jobs_collection.update_one({'_id': ObjectId(job_id)}, {'$set': update_doc})

        # Notify on publish
        if publish_action:
            students = list(students_collection.find({}, {'user_id': 1}))
            notifications = []
            for s in students:
                notifications.append({
                    'user_id': s['user_id'],
                    'title': f"Updated Job: {update_doc['company_name']}",
                    'message': f"Position '{update_doc['role']}' has been published/updated.",
                    'link': '/student/jobs',
                    'is_read': False,
                    'created_at': datetime.datetime.now(),
                    'meta': {'job_id': ObjectId(job_id)}
                })
            if notifications:
                notifications_collection.insert_many(notifications)

        flash("Job updated successfully.", "success")
        return redirect(url_for('manage_jobs'))

    except Exception as e:
        flash(f"Error updating job: {e}", "error")
        return redirect(url_for('manage_jobs'))




def enrich_announcements_attachments(announcements_list):
    """Enrich announcement documents with attachment metadata (type, filename, size in KB)."""
    from utils.db import get_fs
    fs = None
    for ann in announcements_list:
        att_id = ann.get('attachment_id')
        if att_id:
            try:
                if fs is None:
                    fs = get_fs()
                f_obj = fs.get(ObjectId(str(att_id)))
                ann['attachment_filename'] = f_obj.filename or 'Document'
                fname_lower = (f_obj.filename or '').lower()
                if fname_lower.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg')):
                    ann['attachment_type'] = 'image'
                elif fname_lower.endswith('.pdf'):
                    ann['attachment_type'] = 'pdf'
                else:
                    ann['attachment_type'] = 'file'
                ann['attachment_size_kb'] = round(f_obj.length / 1024, 1)
            except Exception:
                ann['attachment_filename'] = 'Attached File'
                ann['attachment_type'] = 'file'
                ann['attachment_size_kb'] = 0
        else:
            ann['attachment_type'] = None
            ann['attachment_filename'] = None
            ann['attachment_size_kb'] = 0

@app.route('/admin/announcements/manage')
@login_required(role='admin')
def manage_announcements():
    announcements = list(announcements_collection.find().sort('created_at', -1))
    enrich_announcements_attachments(announcements)
    
    # Prepare for both display and JSON
    announcements_data = []
    for ann in announcements:
        ann_safe = ann.copy()
        for key, value in ann_safe.items():
            if isinstance(value, ObjectId):
                ann_safe[key] = str(value)
            elif isinstance(value, datetime.datetime):
                ann_safe[key] = value.isoformat()
        ann['safe_data'] = ann_safe
        announcements_data.append(ann_safe)
        
    return render_template('admin/manage_announcements.html', announcements=announcements, announcements_data=announcements_data)

@app.route('/admin/announcements/delete/<ann_id>', methods=['POST'])
@login_required(role='admin')
def delete_announcement(ann_id):
    announcements_collection.delete_one({'_id': ObjectId(ann_id)})
    flash("Announcement deleted", "success")
    return redirect(url_for('manage_announcements'))

@app.route('/admin/announcements/<ann_id>/edit', methods=['POST'])
@login_required(role='admin')
def edit_announcement(ann_id):
    """Edit an existing announcement"""
    try:
        ann = announcements_collection.find_one({'_id': ObjectId(ann_id)})
        if not ann:
            flash("Announcement not found", "error")
            return redirect(url_for('manage_announcements'))
        
        # Check authorization
        if ann.get('created_by_id') != ObjectId(session['user_id']) and session.get('admin_level') != 'super_admin':
            flash("You don't have permission to edit this announcement", "error")
            return redirect(url_for('manage_announcements'))
        
        # Update fields
        title = request.form.get('title', '').strip() or ann['title']
        content = request.form.get('content', '').strip() or ann.get('content', '')
        category = request.form.get('category', '').strip() or ann.get('category', 'General')
        priority = request.form.get('priority', '').strip() or ann.get('priority', 'normal')
        action = request.form.get('action', 'draft')
        target_all_students = request.form.get('target_all_students') == 'on'
        expiry_date_raw = request.form.get('expiry_date', '')
        
        # Parse expiry date
        expires_at = ann.get('expires_at')
        if expiry_date_raw:
            try:
                expires_at = datetime.datetime.fromisoformat(expiry_date_raw)
            except Exception:
                pass
        
        # Handle File Upload
        attachment = request.files.get('attachment')
        attachment_id = ann.get('attachment_id')
        if attachment and attachment.filename:
            try:
                fs = get_fs()
                filename = secure_filename(attachment.filename)
                attachment_id = fs.put(
                    attachment.read(),
                    filename=filename,
                    content_type=attachment.content_type,
                    metadata={'uploaded_by': session['user_id'], 'type': 'townhall_attachment'}
                )
            except Exception as e:
                flash(f"Error uploading file: {e}", "error")
        
        url = request.form.get('url', '').strip() or ann.get('external_url', '')

        update_doc = {
            'title': title,
            'content': content,
            'category': category,
            'priority': priority,
            'target_all_students': target_all_students,
            'expires_at': expires_at,
            'attachment_id': attachment_id,
            'external_url': url,
            'updated_at': datetime.datetime.now(),
            'status': 'published' if action == 'publish' else ann.get('status', 'draft')
        }
        
        # If publishing for the first time
        if action == 'publish' and ann.get('status') != 'published':
            update_doc['published_at'] = datetime.datetime.now()
            # Notify students
            if target_all_students:
                students = list(students_collection.find({}, {'user_id': 1}))
                notifications = []
                priority_icon = '🚨' if priority == 'urgent' else '⚠️' if priority == 'high' else '📢'
                for s in students:
                    notifications.append({
                        'user_id': s['user_id'],
                        'title': f"{priority_icon} {category}: {title}",
                        'message': f"{content[:150]}..." if len(content) > 150 else content,
                        'link': '/student/dashboard',
                        'is_read': False,
                        'created_at': datetime.datetime.now(),
                        'type': 'announcement',
                        'meta': {'announcement_id': str(ann_id)}
                    })
                if notifications:
                    notifications_collection.insert_many(notifications)
        
        announcements_collection.update_one({'_id': ObjectId(ann_id)}, {'$set': update_doc})
        flash("Announcement updated successfully!", "success")
        return redirect(url_for('manage_announcements'))
    except Exception as e:
        flash(f"Error updating announcement: {str(e)}", "error")
        return redirect(url_for('manage_announcements'))

@app.route('/admin/announcements/<ann_id>/publish', methods=['POST'])
@login_required(role='admin')
def publish_announcement(ann_id):
    """Publish a draft announcement"""
    try:
        ann = announcements_collection.find_one({'_id': ObjectId(ann_id)})
        if not ann:
            flash("Announcement not found", "error")
            return redirect(url_for('manage_announcements'))
        
        # Check authorization
        if ann.get('created_by_id') != ObjectId(session['user_id']) and session.get('admin_level') != 'super_admin':
            flash("You don't have permission to publish this announcement", "error")
            return redirect(url_for('manage_announcements'))
        
        # Publish the announcement
        announcements_collection.update_one(
            {'_id': ObjectId(ann_id)},
            {'$set': {
                'status': 'published',
                'published_at': datetime.datetime.now(),
                'updated_at': datetime.datetime.now()
            }}
        )
        
        # Send notifications
        if ann.get('target_all_students', True):
            students = list(students_collection.find({}, {'user_id': 1}))
            notifications = []
            category = ann.get('category', 'General')
            priority = ann.get('priority', 'normal')
            priority_icon = '🚨' if priority == 'urgent' else '⚠️' if priority == 'high' else '📢'
            for s in students:
                notifications.append({
                    'user_id': s['user_id'],
                    'title': f"{priority_icon} {category}: {ann['title']}",
                    'message': f"{ann.get('content', '')[:150]}...",
                    'link': '/student/dashboard',
                    'is_read': False,
                    'created_at': datetime.datetime.now(),
                    'type': 'announcement',
                    'meta': {'announcement_id': str(ann_id)}
                })
            if notifications:
                notifications_collection.insert_many(notifications)
        
        flash("Announcement published successfully!", "success")
        return redirect(url_for('manage_announcements'))
    except Exception as e:
        flash(f"Error publishing announcement: {str(e)}", "error")
        return redirect(url_for('manage_announcements'))

@app.route('/notifications')
@login_required(role=None) # Allow any role
def notifications_page():
    user_id = ObjectId(session['user_id'])
    notifications = list(notifications_collection.find({'user_id': user_id}).sort('created_at', -1).limit(50))
    # For full page, maybe limit 50?
    notifications = list(notifications_collection.find({'user_id': user_id}).sort('created_at', -1).limit(50))
    return render_template('notifications.html', notifications=notifications)

@app.route('/notifications/mark-read/<note_id>', methods=['POST'])
@login_required(role=None)
def mark_notification_read(note_id):
    try:
        notifications_collection.update_one(
            {'_id': ObjectId(note_id), 'user_id': ObjectId(session['user_id'])},
            {'$set': {'is_read': True}}
        )
    except:
        pass
    return redirect(request.referrer or url_for('notifications_page'))

@app.route('/notifications/mark-all-read', methods=['POST'])
@login_required(role=None)
def mark_all_read():
    try:
        notifications_collection.update_many(
            {'user_id': ObjectId(session['user_id']), 'is_read': False},
            {'$set': {'is_read': True}}
        )
        flash("All notifications marked as read", "success")
    except:
        pass
    return redirect(url_for('notifications_page'))

@app.route('/student/announcements')
@login_required(role='student')
def student_announcements():
    announcements = list(announcements_collection.find({'status': 'published'}).sort('created_at', -1))
    enrich_announcements_attachments(announcements)
    return render_template('student/announcements.html', announcements=announcements)

@app.route('/student/jobs/<job_id>/apply', methods=['POST'])
@login_required(role='student')
def apply_job(job_id):
    try:
        user_id = ObjectId(session['user_id'])
        job_id_obj = ObjectId(job_id)
        
        # Check if already applied
        if applications_collection.find_one({'student_id': user_id, 'job_id': job_id_obj}):
            flash("You have already applied for this job.", "info")
            return redirect(url_for('student_jobs'))
            
        # University Placement Policy (Dream Job & Single Offer Rule)
        existing_offer = applications_collection.find_one({
            'student_id': user_id,
            'status': 'Selected'
        })
        if existing_offer:
            existing_job = jobs_collection.find_one({'_id': existing_offer.get('job_id')})
            existing_company = existing_job.get('company_name', 'an organization') if existing_job else 'an organization'
            import re
            nums = re.findall(r'[\d\.]+', str(job.get('package', '0')))
            new_pkg_val = float(nums[0]) if nums else 0.0
            
            if new_pkg_val < 10.0:
                flash(f"Placement Policy Restriction: You have already secured an offer at {existing_company}. Per College Placement Policy, you are eligible to apply only for Dream Category recruitment drives (≥ 10 LPA).", "warning")
                return redirect(url_for('student_jobs'))
            
        # Get Student Details for Snapshot
        student = students_collection.find_one({'user_id': user_id})
        user = users_collection.find_one({'_id': user_id})
        job = jobs_collection.find_one({'_id': job_id_obj})
        
        if not student or not user or not job:
            flash("Error retrieving profile data.", "error")
            return redirect(url_for('student_dashboard'))
            
        # Multiple Application Detection
        active_applications_count = applications_collection.count_documents({
            'student_id': user_id, 
            'status': {'$nin': ['Rejected', 'Withdrawn']}
        })
        
        # Prepare Application Document (Snapshot)
        application = {
            'student_id': user_id,
            'job_id': job_id_obj,
            'company_name': job.get('company_name'), # Helper for quick display
            'job_role': job.get('role'),             # Helper for quick display
            'student_name': student.get('name'),
            'student_email': user.get('email'),
            'student_phone': student.get('phone'),
            'cgpa': student.get('cgpa'),
            'branch': student.get('branch'),
            'resume_file_id': student.get('resume_file_id'),
            'applied_at': datetime.datetime.now(),
            'status': 'Applied',
            'is_multiple_applicant': active_applications_count >= 2 # Flag for Red Highlight
        }
        
        applications_collection.insert_one(application)
        
        # Notify Admin (Optional but good)
        # notifications_collection.insert_one(...) 
        
        flash("Application submitted successfully!", "success")
        return redirect(url_for('student_jobs')) # Redirect to jobs list
        
    except Exception as e:
        flash(f"Error applying to job: {e}", "error")
        return redirect(url_for('student_dashboard'))

@app.route('/student/applications')
@login_required(role='student')
def student_applications():
    user_id = ObjectId(session['user_id'])
    
    # Fetch applications with Job details
    pipeline = [
        {'$match': {'student_id': user_id}},
        {
            '$lookup': {
                'from': 'jobs',
                'localField': 'job_id',
                'foreignField': '_id',
                'as': 'job_info'
            }
        },
        {'$unwind': {'path': '$job_info', 'preserveNullAndEmptyArrays': True}},
        {'$sort': {'applied_at': -1}}
    ]
    
    applications = list(applications_collection.aggregate(pipeline))
    
    # Convert ObjectIds and dates for template rendering
    for app in applications:
        app['_id'] = str(app['_id'])
        app['job_id'] = str(app['job_id']) if app.get('job_id') else None
        if app.get('job_info'):
            app['job_info']['_id'] = str(app['job_info']['_id'])
    
    return render_template('student/applications.html', applications=applications)

@app.route('/student/applications/<app_id>/respond', methods=['POST'])
@login_required(role='student')
def respond_application(app_id):
    response = request.form.get('response') # 'Attending' or 'Not Attending'
    
    if response not in ['Attending', 'Not Attending']:
        flash("Invalid response", "error")
        return redirect(url_for('student_applications'))
        
    try:
        application = applications_collection.find_one({'_id': ObjectId(app_id), 'student_id': ObjectId(session['user_id'])})
        if not application:
            flash("Application not found", "error")
            return redirect(url_for('student_applications'))
        
        applications_collection.update_one(
            {'_id': ObjectId(app_id), 'student_id': ObjectId(session['user_id'])},
            {'$set': {'student_response': response, 'response_at': datetime.datetime.now()}}
        )
        
        # Notify Admin and Super Admin about the response
        student = students_collection.find_one({'user_id': ObjectId(session['user_id'])})
        student_name = student.get('name', 'Unknown') if student else 'Unknown'
        
        # Notify Super Admins
        super_admins = users_collection.find({'role': 'admin', 'admin_level': 'super_admin'})
        for admin in super_admins:
            response_icon = '✅' if response == 'Attending' else '❌'
            notifications_collection.insert_one({
                'user_id': admin['_id'],
                'title': f"{response_icon} Interview/GD Response: {student_name}",
                'message': f"Student {student_name} has responded '{response}' to the {application.get('job_role', 'interview/GD')}.",
                'link': '/admin/applications',
                'is_read': False,
                'created_at': datetime.datetime.now(),
                'type': 'interview_response',
                'meta': {'app_id': str(app_id), 'response': response}
            })
        
        flash("Response recorded successfully. Admins have been notified.", "success")
    except Exception as e:
        flash(f"Error recording response: {e}", "error")
        
    return redirect(url_for('student_applications'))

@app.route('/admin/export/students')
@login_required(role='admin')
def export_students():
    # Fetch all students
    students = list(students_collection.find())
    return generate_student_export(students)

@app.route('/admin/export/applications')
@login_required(role='admin')
def export_applications():
    job_id = request.args.get('job_id')
    match_query = {}
    
    title_suffix = "All_Applications"
    
    if job_id:
        try:
            match_query['job_id'] = ObjectId(job_id)
            # Fetch job title for filename
            job = jobs_collection.find_one({'_id': ObjectId(job_id)})
            if job:
                title_suffix = f"{job.get('company_name')}_{job.get('role')}"
        except:
            pass
            
    # Aggregate to get student details for the export
    pipeline = [
        {'$match': match_query},
        {
            '$lookup': {
                'from': 'students',
                'localField': 'student_id',
                'foreignField': 'user_id',
                'as': 'student_info'
            }
        },
        {
            '$lookup': {
                'from': 'users',
                'localField': 'student_id',
                'foreignField': '_id',
                'as': 'user_info'
            }
        },
        {
            '$lookup': {
                'from': 'jobs',
                'localField': 'job_id',
                'foreignField': '_id',
                'as': 'job_info'
            }
        }
    ]
    apps_raw = list(applications_collection.aggregate(pipeline))
    
    # Format for the generator
    formatted_apps = []
    for app in apps_raw:
        student = app['student_info'][0] if app.get('student_info') else {}
        user = app['user_info'][0] if app.get('user_info') else {}
        job = app['job_info'][0] if app.get('job_info') else {}
        
        formatted_apps.append({
            '_id': app['_id'],
            'student_name': student.get('name') or user.get('name', 'Unknown'),
            'student_id_code': student.get('student_id', 'N/A'),
            'student_email': user.get('email', 'N/A'),
            'applied_at': app.get('applied_at'),
            'status': app.get('status'),
            'job_title': job.get('role', 'Unknown Job') # For context if mixed
        })

    return generate_application_export(formatted_apps, title_suffix)

@app.route('/admin/applications')
@login_required(role='admin')
def view_applications():
    # Aggregate to get student and job details
    # Add multiple application detection
    pipeline = [
        {
            '$lookup': {
                'from': 'students',
                'let': {'student_id': '$student_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$eq': ['$user_id', '$student_id']}}}
                ],
                'as': 'student_info'
            }
        },
        {
            '$lookup': {
                'from': 'users',
                'localField': 'student_id',
                'foreignField': '_id',
                'as': 'user_info'
            }
        },
        {
            '$lookup': {
                'from': 'jobs',
                'localField': 'job_id',
                'foreignField': '_id',
                'as': 'job_info'
            }
        },
        {'$unwind': {'path': '$student_info', 'preserveNullAndEmptyArrays': True}},
        {'$unwind': {'path': '$job_info', 'preserveNullAndEmptyArrays': True}}
    ]
    applications = list(applications_collection.aggregate(pipeline))

    # Enrichment: Fallback to snapshot data if lookups failed
    for app in applications:
        if not app.get('student_info'):
            app['student_info'] = {
                'name': app.get('student_name', 'Unknown (Deleted)'),
                'contact_email': app.get('student_email'),
                'phone': app.get('student_phone'),
                'cgpa': app.get('cgpa'),
                'branch': app.get('branch'),
                'resume_file_id': app.get('resume_file_id')
            }
        if not app.get('job_info'):
            app['job_info'] = {
                'company_name': app.get('company_name', 'Unknown Company'),
                'role': app.get('job_role', 'Unknown Role')
            }
        
        # If user info is missing (deleted user), allow basic details from snapshot
        if 'user_info' not in app or not app['user_info']:
             app['user_info'] = {'email': app.get('student_email', 'N/A')}
        elif isinstance(app['user_info'], list) and len(app['user_info']) > 0:
             app['user_info'] = app['user_info'][0]
        elif isinstance(app['user_info'], list):
             app['user_info'] = {'email': app.get('student_email', 'N/A')}
    
    # Calculate multiple applications per student
    student_app_counts = {}
    for app in applications:
        sid = str(app['student_id'])
        if sid not in student_app_counts:
            student_app_counts[sid] = 0
        student_app_counts[sid] += 1
    
    # Mark students with multiple applications
    for app in applications:
        sid = str(app['student_id'])
        app['is_multiple_applicant'] = student_app_counts[sid] >= 2
    
    return render_template('admin/applications.html', applications=applications)


@app.route('/admin/applications/job/<job_id>')
@login_required(role='admin')
def view_job_applications(job_id):
    """Super Admin/Faculty: View applicants for a specific job"""
    if session.get('admin_level') not in ['super_admin', 'faculty']:
        flash("Unauthorized access", "error")
        return redirect(url_for('admin_dashboard'))
    
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    if not job:
        flash("Job not found", "error")
        return redirect(url_for('manage_jobs'))
    
    # Get applications for this job
    pipeline = [
        {'$match': {'job_id': ObjectId(job_id)}},
        {
            '$lookup': {
                'from': 'students',
                'let': {'student_id': '$student_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$eq': ['$user_id', '$student_id']}}}
                ],
                'as': 'student_info'
            }
        },
        {
            '$lookup': {
                'from': 'users',
                'localField': 'student_id',
                'foreignField': '_id',
                'as': 'user_info'
            }
        },
        {'$unwind': {'path': '$student_info', 'preserveNullAndEmptyArrays': True}},
        {'$unwind': {'path': '$user_info', 'preserveNullAndEmptyArrays': True}},
        {'$sort': {'applied_at': -1}}
    ]
    
    applications = list(applications_collection.aggregate(pipeline))

    # Enrichment: Fallback to snapshot data if lookups failed
    for app in applications:
        if not app.get('student_info'):
            app['student_info'] = {
                'name': app.get('student_name', 'Unknown (Deleted)'),
                'contact_email': app.get('student_email'),
                'phone': app.get('student_phone'),
                'cgpa': app.get('cgpa'),
                'branch': app.get('branch'),
                'resume_file_id': app.get('resume_file_id')
            }
        
        # Correctly handle user_info if it was unwound or missing
        # If preserveNull.. is True, it might be None or a dict. 
        if not app.get('user_info'):
             app['user_info'] = {'email': app.get('student_email', 'N/A')}

        # Ensure job_info is always present on each application dict
        if not app.get('job_info'):
            app['job_info'] = {
                'company_name': (job.get('company_name') if job else None) or app.get('company_name', 'Recruitment Drive'),
                'role': (job.get('role') if job else None) or app.get('job_role', 'Role')
            }
    
    # Calculate multiple applications
    student_app_counts = {}
    for app in applications:
        sid = str(app['student_id'])
        if sid not in student_app_counts:
            student_app_counts[sid] = 0
        student_app_counts[sid] += 1
    
    for app in applications:
        sid = str(app['student_id'])
        app['is_multiple_applicant'] = student_app_counts[sid] >= 2
    
    return render_template('admin/applications.html', applications=applications, current_job=job)


@app.route('/admin/export/applications/job/<job_id>')
@login_required(role='admin')
def export_job_applications(job_id):
    """Super Admin/Faculty: Export applicants for a specific job"""
    # Allow Faculty to export too
    if session.get('admin_level') not in ['super_admin', 'faculty']:
        flash("Unauthorized access", "error")
        return redirect(url_for('admin_dashboard'))
    
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    if not job:
        flash("Job not found", "error")
        return redirect(url_for('manage_jobs'))
    
    # Get applications for this job
    pipeline = [
        {'$match': {'job_id': ObjectId(job_id)}},
        {
            '$lookup': {
                'from': 'students',
                'localField': 'student_id',
                'foreignField': 'user_id',
                'as': 'student_info'
            }
        },
        {
            '$lookup': {
                'from': 'users',
                'localField': 'student_id',
                'foreignField': '_id',
                'as': 'user_info'
            }
        },
        {
            '$lookup': {
                'from': 'jobs',
                'localField': 'job_id',
                'foreignField': '_id',
                'as': 'job_info'
            }
        }
    ]
    
    apps_raw = list(applications_collection.aggregate(pipeline))
    
    # Calculate multiple applications flag
    student_app_counts = {}
    for app in apps_raw:
        sid = str(app['student_id'])
        if sid not in student_app_counts:
            student_app_counts[sid] = 0
        student_app_counts[sid] += 1
    
    formatted_apps = []
    for app in apps_raw:
        student = app['student_info'][0] if app.get('student_info') else {}
        user = app['user_info'][0] if app.get('user_info') else {}
        job_info = app['job_info'][0] if app.get('job_info') else {}
        
        sid = str(app['student_id'])
        is_multiple = student_app_counts[sid] >= 2
        
        formatted_apps.append({
            '_id': app['_id'],
            'student_name': student.get('name') or user.get('name', 'Unknown'),
            'student_id_code': student.get('student_id', 'N/A'),
            'student_email': user.get('email', 'N/A'),
            'student_phone': student.get('phone', 'N/A'),
            'branch': student.get('branch', 'N/A'),
            'cgpa': student.get('cgpa', 0.0),
            'skills': student.get('skills', []),
            'applied_at': app.get('applied_at'),
            'status': app.get('status'),
            'student_response': app.get('student_response'),
            'response_at': app.get('response_at'),
            'is_multiple_applicant': is_multiple,
            'job_info': job_info
        })
    
    title_suffix = f"{job.get('company_name', 'Job')}_{job.get('role', 'Applications')}"
    return generate_application_export(formatted_apps, title_suffix)

@app.route('/admin/applications/update/<app_id>', methods=['POST'])
@login_required(role='admin')
def update_application_status(app_id):
    new_status = request.form.get('status')
    applications_collection.update_one(
        {'_id': ObjectId(app_id)},
        {'$set': {'status': new_status, 'updated_at': datetime.datetime.now()}}
    )
    flash("Status updated successfully", "success")
    return redirect(request.referrer or url_for('view_applications'))

@app.route('/admin/applications/batch-status-update', methods=['POST'])
@login_required(role='admin')
def batch_status_update():
    """TPO Bulk Action: Update selected checked applications from the data table."""
    app_ids = request.form.getlist('selected_app_ids')
    new_status = request.form.get('batch_status')
    if not app_ids or not new_status:
        flash("No applications or invalid status selected.", "warning")
        return redirect(request.referrer or url_for('view_applications'))

    obj_ids = []
    for aid in app_ids:
        try:
            obj_ids.append(ObjectId(aid))
        except Exception:
            pass

    if obj_ids:
        res = applications_collection.update_many(
            {'_id': {'$in': obj_ids}},
            {'$set': {'status': new_status, 'updated_at': datetime.datetime.now()}}
        )
        flash(f"Updated {res.modified_count} application(s) to '{new_status}'.", "success")
    return redirect(request.referrer or url_for('view_applications'))

@app.route('/admin/applications/bulk-advance', methods=['POST'])
@login_required(role='admin')
def bulk_advance_applications():
    """
    TPO Operations Engine: Batch advance applications.
    Takes candidate identifiers (roll numbers, student IDs, or emails) and a target status.
    Instantly updates all matching candidate applications for the drive and notifies students.
    """
    job_id = request.form.get('job_id')
    target_status = request.form.get('target_status')
    raw_identifiers = request.form.get('identifiers', '')
    round_note = request.form.get('round_note', '').strip()

    valid_statuses = ['Applied', 'Shortlisted', 'GD', 'Interview', 'Selected', 'Rejected', 'Withdrawn']
    if target_status not in valid_statuses:
        flash("Invalid target status selected.", "error")
        return redirect(request.referrer or url_for('view_applications'))

    import re
    tokens = [t.strip() for t in re.split(r'[\r\n,;\s]+', raw_identifiers) if t.strip()]
    if not tokens:
        flash("Please provide at least one Student ID, Roll Number, or Email.", "warning")
        return redirect(request.referrer or url_for('view_applications'))

    matched_user_ids = set()
    found_students = list(students_collection.find({'student_id': {'$in': tokens}}))
    for s in found_students:
        matched_user_ids.add(s['user_id'])
        
    found_users = list(users_collection.find({'email': {'$in': tokens}}))
    for u in found_users:
        matched_user_ids.add(u['_id'])

    if not matched_user_ids:
        flash(f"No students found matching the provided {len(tokens)} identifiers.", "error")
        return redirect(request.referrer or url_for('view_applications'))

    app_query = {'student_id': {'$in': list(matched_user_ids)}}
    if job_id and job_id != 'all':
        try:
            app_query['job_id'] = ObjectId(job_id)
        except Exception:
            pass

    update_data = {
        'status': target_status,
        'updated_at': datetime.datetime.now()
    }
    if round_note:
        update_data['round_note'] = round_note

    result = applications_collection.update_many(app_query, {'$set': update_data})

    # Notify students
    notif_title = f"Placement Drive Update: {target_status}"
    notif_msg = f"Your application status has been updated to '{target_status}'."
    if round_note:
        notif_msg += f" Info: {round_note}"

    notifs = []
    for uid in matched_user_ids:
        notifs.append({
            'user_id': uid,
            'title': notif_title,
            'message': notif_msg,
            'link': '/student/applications',
            'is_read': False,
            'created_at': datetime.datetime.now(),
            'type': 'status_update'
        })
    if notifs:
        notifications_collection.insert_many(notifs)

    flash(f"Batch Advancement Complete: Updated {result.modified_count} application(s) to '{target_status}'. Notified {len(matched_user_ids)} student(s).", "success")
    return redirect(request.referrer or url_for('view_applications'))

@app.route('/admin/export/custom-master-sheet', methods=['POST'])
@login_required(role='admin')
def export_custom_master_sheet():
    """
    Generate tailored candidate Excel/CSV based on recruiter criteria:
    - Min CGPA, Max backlogs, Branches, Gender
    """
    try:
        min_cgpa = float(request.form.get('min_cgpa') or 0.0)
    except Exception:
        min_cgpa = 0.0

    try:
        max_backlogs = int(request.form.get('max_backlogs') or 99)
    except Exception:
        max_backlogs = 99

    branches = request.form.getlist('branches')
    gender = request.form.get('gender')

    query = {'is_active': True}
    if min_cgpa > 0:
        query['cgpa'] = {'$gte': min_cgpa}
    if branches and 'ALL' not in branches:
        query['branch'] = {'$in': branches}
    if gender and gender != 'ALL':
        query['gender'] = gender

    students = list(students_collection.find(query))

    if max_backlogs < 99:
        filtered = []
        for s in students:
            ug_backlogs = s.get('academic', {}).get('ug', {}).get('backlogs', 0)
            try:
                if int(ug_backlogs) <= max_backlogs:
                    filtered.append(s)
            except Exception:
                filtered.append(s)
        students = filtered

    si = StringIO()
    cw = csv.writer(si)
    headers = [
        'Roll No / Student ID', 'Full Name', 'Branch', 'CGPA', 'UG Backlogs',
        'Email', 'Mobile', 'Gender', '10th %', '12th %', 'Key Skills'
    ]
    cw.writerow(headers)

    for s in students:
        user = users_collection.find_one({'_id': s.get('user_id')})
        email = user.get('email', '') if user else ''
        ac = s.get('academic', {})
        cw.writerow([
            s.get('student_id', 'N/A'),
            s.get('name', 'N/A'),
            s.get('branch', 'N/A'),
            s.get('cgpa', 0.0),
            ac.get('ug', {}).get('backlogs', 0),
            email,
            s.get('phone', ''),
            s.get('gender', ''),
            ac.get('tenth', {}).get('score', ''),
            ac.get('twelfth', {}).get('score', ''),
            ", ".join(s.get('skills', []))
        ])

    output = make_response(si.getvalue())
    filename = f"Recruiter_Master_Sheet_CGPA_{min_cgpa}.csv"
    output.headers["Content-Disposition"] = f"attachment; filename={filename}"
    output.headers["Content-type"] = "text/csv"
    return output



@app.route('/admin/export/eligible/<job_id>')
@login_required(role='admin')
def export_eligible_students(job_id):
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    if not job:
        flash("Job not found", "error")
        return redirect(url_for('manage_jobs'))
        
    min_cgpa = job.get('min_cgpa', 0.0)
    
    # Find active students with CGPA >= min_cgpa
    query = {'is_active': True}
    if min_cgpa > 0:
        query['cgpa'] = {'$gte': min_cgpa}
        
    students = list(students_collection.find(query))
    
    # Generate CSV
    si = StringIO()
    cw = csv.writer(si)
    
    # Comprehensive Header
    headers = [
        'Student ID', 'Full Name', 'Gender', 'DOB', 'Email', 'Mobile', 'Alt Mobile',
        'Nationality', 'Marital Status', 'Aadhaar', 'PAN',
        'Permanent Address', 'Current Address',
        # 10th
        '10th School', '10th Board', '10th Year', '10th %',
        # 12th
        '12th School', '12th Board', '12th Year', '12th %', '12th Stream',
        # UG
        'UG College', 'UG University', 'UG Degree', 'UG Branch', 'UG Year', 'UG CGPA/%', 'UG Backlogs', 'UG Backlog Status',
        # PG
        'PG College', 'PG University', 'PG Degree', 'PG Branch', 'PG Year', 'PG CGPA/%', 'PG Backlogs', 'PG Backlog Status',
        # Skills
        'Skills', 'Projects'
    ]
    cw.writerow(headers)
    
    for s in students:
        # Get Email from Users collection if not in student doc
        user = users_collection.find_one({'_id': s['user_id']})
        email = user.get('email', '') if user else ''
        
        # Safely get nested fields
        ac = s.get('academic', {})
        tenth = ac.get('tenth', {})
        twelfth = ac.get('twelfth', {})
        ug = ac.get('ug', {})
        pg = ac.get('pg', {})
        addr = s.get('address', {})
        
        row = [
            # Personal
            s.get('student_id', ''),
            s.get('name', ''),
            s.get('gender', ''),
            s.get('dob', ''),
            email, # Personal email is s.get('personal_email') but let's use Login Email as primary or both? User asked for College + Personal.
                  # Logic: s.get('personal_email') is Personal. user['email'] is College/Login.
                  # Let's verify. The form saves 'personal_email'. The User doc has 'email'.
                  # I will export 'personal_email' here if available, or just append it.
                  # Let's stick to the list: Email ID (College + Personal). 
                  # Implementation: I'll put Personal Email next.
            s.get('phone', ''),
            s.get('alt_phone', ''),
            s.get('nationality', ''),
            s.get('marital_status', ''),
            s.get('aadhaar', ''),
            s.get('pan', ''),
            
            # Address
            addr.get('permanent', '') if isinstance(addr, dict) else s.get('address', ''), # Fallback for old data
            addr.get('current', '') if isinstance(addr, dict) else '',
            
            # 10th
            tenth.get('school', ''), tenth.get('board', ''), tenth.get('year', ''), tenth.get('score', ''),
            
            # 12th
            twelfth.get('school', ''), twelfth.get('board', ''), twelfth.get('year', ''), twelfth.get('score', ''), twelfth.get('stream', ''),
            
            # UG
            ug.get('college', ''), ug.get('university', ''), ug.get('degree', ''), ug.get('branch', ''),
            ug.get('year', ''), ug.get('score', ''), ug.get('backlogs', ''), ug.get('backlog_status', ''),
            
            # PG
            pg.get('college', ''), pg.get('university', ''), pg.get('degree', ''), pg.get('branch', ''),
            pg.get('year', ''), pg.get('score', ''), pg.get('backlogs', ''), pg.get('backlog_status', ''),
            
            # Professional
            ", ".join(s.get('skills', [])),
            s.get('projects', '')
        ]
        
        cw.writerow(row)
        
    output = make_response(si.getvalue())
    filename = f"{secure_filename(job['company_name'])}_eligible_students.csv"
    output.headers["Content-Disposition"] = f"attachment; filename={filename}"
    output.headers["Content-type"] = "text/csv"
    return output

# --- STUDENT ROUTES ---


@app.route('/student/dashboard')
@login_required(role='student')
def student_dashboard():
    student = students_collection.find_one({'user_id': ObjectId(session['user_id'])})
    if not student:
        flash("Student profile not found", "error")
        return redirect(url_for('logout'))
    
    # Get user info for login time
    user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
    
    # Get last login time from logs
    last_login_log = login_logs_collection.find_one(
        {'user_id': ObjectId(session['user_id'])},
        sort=[('login_time', -1)]
    )
        
    # Auto-expire jobs
    auto_expire_jobs()
    
    # Recent jobs (published ones) - Smart Filter by CGPA
    student_cgpa = student.get('cgpa', 0.0)
    recent_jobs = list(jobs_collection.find({
        'status': 'published',
        'min_cgpa': {'$lte': student_cgpa}
    }).sort('published_at', -1).limit(5))
    
    # Upcoming drives (jobs with future drive_date)
    now = datetime.datetime.now()
    upcoming_drives = list(jobs_collection.find({
        'status': 'published',
        'drive_date': {'$gte': now}
    }).sort('drive_date', 1).limit(5))
    
    # Announcements
    announcements = list(announcements_collection.find({'status': 'published'}).sort('created_at', -1).limit(5))
    
    # My Applications with detailed info
    pipeline = [
        {
            '$match': {'student_id': ObjectId(session['user_id'])}
        },
        {
            '$lookup': {
                'from': 'jobs',
                'localField': 'job_id',
                'foreignField': '_id',
                'as': 'job_info'
            }
        },
        {'$unwind': '$job_info'},
        {'$sort': {'applied_at': -1}}
    ]
    my_applications = list(applications_collection.aggregate(pipeline))
    applied_job_ids = [app['job_id'] for app in my_applications]
    
    # Activities: Applications that are Shortlisted or Selected (Active Stages)
    activities = [app for app in my_applications if app.get('status') in ['Shortlisted', 'Selected', 'GD', 'Interview']]
    
    # Count applications by status
    shortlisted_count = sum(1 for app in my_applications if app.get('status') == 'Shortlisted')
    selected_count = sum(1 for app in my_applications if app.get('status') == 'Selected')
    
    return render_template('student/dashboard.html', 
                         student=student, 
                         recent_jobs=recent_jobs, 
                         announcements=announcements,
                         my_applications=my_applications,
                         applied_job_ids=applied_job_ids,
                         shortlisted_count=shortlisted_count,
                         selected_count=selected_count,
                         activities=activities,
                         upcoming_drives=upcoming_drives,
                         user=user,
                         last_login_log=last_login_log)

@app.route('/student/profile')
@login_required(role='student')
def student_profile():
    student = students_collection.find_one({'user_id': ObjectId(session['user_id'])})
    return render_template('student/profile.html', student=student)

@app.route('/student/jobs')
@login_required(role='student')
def student_jobs():
    student = students_collection.find_one({'user_id': ObjectId(session['user_id'])})
    all_jobs = list(jobs_collection.find().sort('created_at', -1))
    
    # My Applications to check status
    my_applications = list(applications_collection.find({'student_id': ObjectId(session['user_id'])}))
    applied_job_ids = [str(app['job_id']) for app in my_applications]
    applied_job_ids_str = applied_job_ids  # For template comparison

    # Calculate predictive match scores
    if student:
        for job in all_jobs:
            cgpa_factor = (student.get('cgpa', 0) / 10.0) * 100 if student.get('cgpa') else 0
            # Simulated bonus for IT/CSE branch alignment
            branch = student.get('branch', '') or ''
            branch_bonus = 15 if branch.lower() in job.get('role', '').lower() or branch.lower() == 'cse' else 5
            job['match_score'] = min(100, round(cgpa_factor * 0.8 + branch_bonus))
    
    return render_template('student/jobs.html', student=student, jobs=all_jobs, applied_job_ids_str=applied_job_ids_str)



# --- API ENDPOINTS FOR REAL-TIME NOTIFICATIONS ---

@app.route('/api/notifications/check')
@login_required()
def check_new_notifications():
    """Check for new notifications since last check (for polling)"""
    user_id = ObjectId(session['user_id'])
    last_check = request.args.get('last_check')
    
    try:
        query = {'user_id': user_id}
        if last_check:
            last_check_dt = datetime.datetime.fromisoformat(last_check)
            query['created_at'] = {'$gt': last_check_dt}
        
        new_count = notifications_collection.count_documents(query)
        return {'new_count': new_count}
    except Exception as e:
        return {'new_count': 0, 'error': str(e)}


@app.route('/api/notifications')
@login_required()
def get_notifications():
    """Get all notifications for the current user"""
    user_id = ObjectId(session['user_id'])
    notifications = list(notifications_collection.find({'user_id': user_id}).sort('created_at', -1).limit(20))
    # Convert ObjectIds and Datetimes for JSON
    for n in notifications:
        n['_id'] = str(n['_id'])
        n['user_id'] = str(n['user_id'])
        if n.get('created_at'):
            n['created_at'] = n['created_at'].strftime('%b %d, %H:%M')
    return {'notifications': notifications}


@app.route('/api/notifications/read/<notif_id>', methods=['POST'])
@login_required()
def mark_read(notif_id):
    notifications_collection.update_one(
        {'_id': ObjectId(notif_id), 'user_id': ObjectId(session['user_id'])},
        {'$set': {'is_read': True}}
    )
    return {'status': 'success'}


@app.route('/api/notifications/sync', methods=['POST'])
@login_required()
def sync_notifications():
    """Sync offline notifications"""
    if 'user_id' not in session:
        return {'status': 'error', 'message': 'Not logged in'}, 401
    
    try:
        data = request.get_json()
        if data:
            # Save notification to database
            notifications_collection.insert_one({
                'user_id': ObjectId(session['user_id']),
                'title': data.get('title'),
                'message': data.get('message'),
                'link': data.get('link', '/'),
                'is_read': False,
                'created_at': datetime.datetime.now(),
                'offline_synced': True,
                'type': data.get('type', 'general')
            })
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500


@app.route('/api/notifications/send-external', methods=['POST'])
@login_required(role='admin')
def send_external_notification():
    """Send notification to specific user(s) externally"""
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        title = data.get('title')
        message = data.get('message')
        link = data.get('link', '/student/dashboard')
        
        if not user_ids or not title:
            return {'status': 'error', 'message': 'Missing user_ids or title'}, 400
        
        notifications = []
        for uid in user_ids:
            try:
                notifications.append({
                    'user_id': ObjectId(uid),
                    'title': title,
                    'message': message,
                    'link': link,
                    'is_read': False,
                    'created_at': datetime.datetime.now(),
                    'type': 'external',
                    'sent_by': session.get('email')
                })
            except:
                continue
        
        if notifications:
            notifications_collection.insert_many(notifications)
        
        return {'status': 'success', 'sent': len(notifications)}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500


@app.route('/student/update_resume', methods=['POST'])
@login_required(role='student')
def update_resume():
    if 'resume' not in request.files:
        flash("No file part", "error")
        return redirect(url_for('student_dashboard'))
        
    file = request.files['resume']
    if file.filename == '':
        flash("No selected file", "error")
        return redirect(url_for('student_dashboard'))

    if file:
        student = students_collection.find_one({'user_id': ObjectId(session['user_id'])})
        
        # Remove old file
        old_filename = student.get('resume_path')
        if old_filename:
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
            if os.path.exists(old_path):
                os.remove(old_path)
                
        # Save new file
        new_filename = f"{secure_filename(session['email'])}_{secure_filename(file.filename)}"
        new_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        file.save(new_path)
        
        # Update DB
        students_collection.update_one(
            {'user_id': ObjectId(session['user_id'])},
            {'$set': {'resume_path': new_filename}}
        )
        
        flash("Resume updated successfully!", "success")
        return redirect(url_for('student_dashboard'))

# --- ALL STUDENTS LIST (for admin quick action) ---
@app.route('/admin/all-students')
@login_required(role='admin')
def all_students_list():
    """Display all students in a table with View button."""
    pipeline = [
        {'$match': {'role': 'student'}},
        {'$lookup': {
            'from': 'students',
            'let': {'user_id': '$_id'},
            'pipeline': [{'$match': {'$expr': {'$eq': ['$user_id', '$$user_id']}}}],
            'as': 'student_info'
        }},
        {'$unwind': {'path': '$student_info', 'preserveNullAndEmptyArrays': True}},
        {'$sort': {'created_at': -1}}
    ]
    students = list(users_collection.aggregate(pipeline))
    return render_template('admin/all_students.html', students=students)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(debug=True)
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)
