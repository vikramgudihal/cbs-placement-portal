import urllib.request, urllib.parse, http.cookiejar, re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Fetch login page to get CSRF token
login_page = opener.open('http://127.0.0.1:5000/login').read().decode('utf-8')
csrf_match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', login_page)
csrf_token = csrf_match.group(1) if csrf_match else ''
print('CSRF Token found:', bool(csrf_token))

# 2. Post login
login_data = urllib.parse.urlencode({
    'email': 'student@cbs.edu',
    'password': 'Student@123',
    'role': 'student',
    'csrf_token': csrf_token
}).encode('utf-8')

res = opener.open('http://127.0.0.1:5000/login', data=login_data)
login_resp_text = res.read().decode('utf-8')
print('Post login URL:', res.geturl())
if 'student/dashboard' not in res.geturl():
    for line in login_resp_text.split('\n'):
        if 'alert' in line or 'error' in line.lower() or 'invalid' in line.lower():
            print('Line:', line.strip())


dash_res = opener.open('http://127.0.0.1:5000/student/dashboard')
dash_html = dash_res.read().decode('utf-8')
print('Dashboard page fetched. Length:', len(dash_html))
print('Has qa-icon-wrap:', 'qa-icon-wrap' in dash_html)
print('Has vendor/phosphor CSS link:', 'vendor/phosphor/regular/style.css' in dash_html)
print('Has stat-icon-box:', 'stat-icon-box' in dash_html)
print('Has ph-fill ph-file-text:', 'ph-fill ph-file-text' in dash_html)

# 4. Check jobs page
jobs_res = opener.open('http://127.0.0.1:5000/student/jobs')
jobs_html = jobs_res.read().decode('utf-8')
print('Jobs page fetched. Length:', len(jobs_html))
drives = re.findall(r'Drive:\s*([^<\n]+)', jobs_html)
print('Jobs page drive dates:', drives[:3])

# 5. Check Admin Dashboard
cj_admin = http.cookiejar.CookieJar()
opener_admin = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_admin))
login_p = opener_admin.open('http://127.0.0.1:5000/login').read().decode('utf-8')
m = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', login_p)
csrf_admin = m.group(1) if m else ''

admin_login_data = urllib.parse.urlencode({
    'email': 'admin@cbs.edu',
    'password': 'Admin@123',
    'role': 'admin',
    'csrf_token': csrf_admin
}).encode('utf-8')

r_admin = opener_admin.open('http://127.0.0.1:5000/login', data=admin_login_data)
admin_dash_res = opener_admin.open('http://127.0.0.1:5000/admin/dashboard')
admin_dash_html = admin_dash_res.read().decode('utf-8')
print('Admin Dashboard fetched. Length:', len(admin_dash_html))
print('Admin Dashboard has qa-icon-wrap:', 'qa-icon-wrap' in admin_dash_html)
print('Admin Dashboard has stat-card-primary:', 'stat-card-primary' in admin_dash_html)

# 6. Check Production Health Endpoint
health_res = urllib.request.urlopen('http://127.0.0.1:5000/health')
print('Health check status:', health_res.getcode())
health_json = health_res.read().decode('utf-8')
print('Health check payload:', health_json)

# 7. Check Production 404 Error Handler
try:
    urllib.request.urlopen('http://127.0.0.1:5000/some-random-missing-route')
except urllib.error.HTTPError as e:
    print('404 error code:', e.code)
    err_body = e.read().decode('utf-8')
    print('404 renders branded page:', 'Resource Not Found' in err_body or 'Error 404' in err_body)


