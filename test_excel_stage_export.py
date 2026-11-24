"""
Verification script for Excel Stage Progression Export (Single Company & Whole Companies)
Tests both endpoint responses, file formats, and internal sheet contents.
"""
import sys
import io
import zipfile
import xml.etree.ElementTree as ET
from app import app
from utils.db import get_db
from bson import ObjectId

def run_tests():
    db = get_db()
    client = app.test_client()

    print("=================================================================")
    print("Testing Stage Progression Excel Export (Whole Companies & Company)")
    print("=================================================================")

    # 1. Setup Admin Session
    admin_user = db.users.find_one({'role': 'admin'})
    if not admin_user:
        print("[!] No admin user found in database.")
        sys.exit(1)

    with client.session_transaction() as sess:
        sess['user_id'] = str(admin_user['_id'])
        sess['role'] = 'admin'
        sess['email'] = admin_user['email']
        sess['admin_level'] = admin_user.get('admin_level', 'super_admin')

    # 2. Test Whole Companies Excel Export
    print("\n--- Test 1: Whole Companies Master Stage Export ---")
    res1 = client.get('/admin/export/stages/excel')
    print(f"Status Code: {res1.status_code}")
    print(f"Content-Type: {res1.headers.get('Content-Type')}")
    print(f"Content-Disposition: {res1.headers.get('Content-Disposition')}")
    print(f"Bytes received: {len(res1.data)}")

    assert res1.status_code == 200, f"Expected 200, got {res1.status_code}"
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res1.headers.get('Content-Type', '')
    assert "Whole_Companies_Master" in res1.headers.get('Content-Disposition', '')
    assert res1.headers.get('Content-Disposition', '').endswith('.xlsx')
    assert len(res1.data) > 1000, "Excel output is suspiciously small"

    # Verify xlsx ZIP structure and sheets
    zf1 = zipfile.ZipFile(io.BytesIO(res1.data))
    namelist1 = zf1.namelist()
    assert 'xl/workbook.xml' in namelist1, "xl/workbook.xml missing from xlsx archive"
    wb_xml1 = zf1.read('xl/workbook.xml').decode('utf-8')
    assert "Stage Progression" in wb_xml1, "Sheet 'Stage Progression' not found"
    assert "Placed Offers" in wb_xml1, "Sheet 'Placed Offers' not found"
    assert "Company Analytics" in wb_xml1, "Sheet 'Company Analytics' not found"
    print("✓ Master Excel Workbook structure and all 3 sheets verified successfully!")

    # 3. Test Company-Specific Drive Excel Export
    print("\n--- Test 2: Company-Specific Stage Export ---")
    sample_job = db.jobs.find_one({'status': {'$in': ['published', 'draft', 'expired']}})
    if not sample_job:
        sample_job = db.jobs.find_one()
    
    assert sample_job is not None, "No jobs in database to test"
    job_id = str(sample_job['_id'])
    company_name = sample_job.get('company_name', 'Company')
    print(f"Testing for company: {company_name} (ID: {job_id})")

    res2 = client.get(f'/admin/export/applications/job/{job_id}/excel')
    print(f"Status Code: {res2.status_code}")
    print(f"Content-Type: {res2.headers.get('Content-Type')}")
    print(f"Content-Disposition: {res2.headers.get('Content-Disposition')}")
    print(f"Bytes received: {len(res2.data)}")

    assert res2.status_code == 200, f"Expected 200, got {res2.status_code}"
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res2.headers.get('Content-Type', '')
    assert res2.headers.get('Content-Disposition', '').endswith('.xlsx')
    assert len(res2.data) > 1000, "Excel output is suspiciously small"

    zf2 = zipfile.ZipFile(io.BytesIO(res2.data))
    wb_xml2 = zf2.read('xl/workbook.xml').decode('utf-8')
    assert "Stage Progression" in wb_xml2
    assert "Placed Offers" in wb_xml2
    assert "Company Analytics" in wb_xml2
    print("✓ Company Drive Excel Workbook verified successfully!")

    # 4. Test Query Parameter variant: /admin/export/stages/excel?job_id=...
    print("\n--- Test 3: Query Parameter Variant (?job_id=...) ---")
    res3 = client.get(f'/admin/export/stages/excel?job_id={job_id}')
    assert res3.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res3.headers.get('Content-Type', '')
    print("✓ Query param export verified successfully!")

    # 5. Check Content Inspection: Inspect candidate rows in Sheet 1
    print("\n--- Test 4: Workbook Content Inspection ---")
    shared_strings = ""
    if 'xl/sharedStrings.xml' in namelist1:
        import html
        shared_strings = html.unescape(zf1.read('xl/sharedStrings.xml').decode('utf-8'))
    print(f"Shared strings length: {len(shared_strings)} characters")
    
    # Check key domain terms exist in the master sheet
    assert "CHETAN BUSINESS SCHOOL" in shared_strings
    assert "STAGE PROGRESSION" in shared_strings
    assert "Student ID / USN" in shared_strings
    assert "Current Recruitment Stage" in shared_strings
    assert "Candidate RSVP" in shared_strings
    assert "Placement Exit Status" in shared_strings
    print("✓ Header and institutional branding strings verified in master Excel workbook!")

    print("\n=================================================================")
    print("ALL STAGE PROGRESSION EXCEL EXPORT TESTS PASSED (100% SUCCESS)")
    print("=================================================================")

if __name__ == '__main__':
    run_tests()
