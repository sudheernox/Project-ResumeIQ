"""
Standalone & Comprehensive Test Suite for:
1. Feature 1: Profile Change Password UI & Validation (collapsed by default, cancel reset, verify password, update)
2. Feature 2: Forgot Password & Secure Reset Flow (link on login, generic response, rate limiting, hashed token, single-use, prevent reuse, expiry)
"""
import os
import sys
import secrets
import hashlib
from datetime import datetime, timedelta

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, _reset_rate_limits
from backend.database import User, PasswordResetToken

app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

client = app.test_client()

passed_count = 0
failed_count = 0


def assert_test(condition, test_name):
    global passed_count, failed_count
    if condition:
        print(f"  [PASS] {test_name}")
        passed_count += 1
    else:
        print(f"  [FAIL] {test_name}")
        failed_count += 1


print("=" * 70)
print("=== TESTING FEATURE 1: PROFILE CHANGE PASSWORD ===")
print("=" * 70)

with app.app_context():
    db.create_all()
    _reset_rate_limits.clear()

# 1. Login page contains Forgot Password? link
res = client.get('/login')
html = res.get_data(as_text=True)
assert_test(res.status_code == 200, "Login page loads successfully (200)")
assert_test('/forgot-password' in html, "Login page contains link to /forgot-password")
assert_test('Forgot Password?' in html, "Login page displays 'Forgot Password?' text")

# 2. Register and login test user
test_email = f"profile_test_{secrets.token_hex(4)}@resumeiq.ai"
test_pass = "OriginalPass123!"
reg_res = client.post('/api/auth/register', json={
    'full_name': 'Profile Tester',
    'email': test_email,
    'password': test_pass,
    'confirm_password': test_pass
})
assert_test(reg_res.status_code == 201, "Test user registered successfully (201)")

login_res = client.post('/api/auth/login', json={
    'email': test_email,
    'password': test_pass,
    'remember': False
})
assert_test(login_res.status_code == 200, "Test user logged in (200)")

# 3. Profile page HTML contains collapsed password section and cancel button
prof_res = client.get('/profile')
prof_html = prof_res.get_data(as_text=True)
assert_test(prof_res.status_code == 200, "Profile page loads for authenticated user")
assert_test('id="showChangePassBtn"' in prof_html, "Clean 'Change Password' button exists")
assert_test('id="changePasswordCollapse"' in prof_html, "Collapsible container exists")
assert_test('style="display: none;"' in prof_html, "Form is collapsed by default (display: none)")
assert_test('id="cancelPassBtn"' in prof_html, "Cancel button exists in password form")
assert_test('id="savePassBtn"' in prof_html, "Update Password button exists")
assert_test('toggle-vis' in prof_html, "Password toggle visibility icons exist")

# 4. Profile password update validations
# A. Incorrect current password
wrong_pass_res = client.post('/api/auth/profile', json={
    'current_password': 'IncorrectPassword999!',
    'new_password': 'NewSecurePass456!',
    'confirm_password': 'NewSecurePass456!'
})
assert_test(wrong_pass_res.status_code == 400, "Wrong current password returns 400")
assert_test('Incorrect current password' in wrong_pass_res.get_json().get('error', ''), "Clear error message on incorrect current password")

# B. Passwords mismatch
mismatch_res = client.post('/api/auth/profile', json={
    'current_password': test_pass,
    'new_password': 'NewSecurePass456!',
    'confirm_password': 'DifferentPass456!'
})
assert_test(mismatch_res.status_code == 400, "Mismatched passwords returns 400")
assert_test('match' in mismatch_res.get_json().get('error', '').lower(), "Clear error message on password mismatch")

# C. Password too short (< 8 chars)
short_res = client.post('/api/auth/profile', json={
    'current_password': test_pass,
    'new_password': 'short',
    'confirm_password': 'short'
})
assert_test(short_res.status_code == 400, "Short password (< 8 chars) returns 400")
assert_test('8 characters' in short_res.get_json().get('error', ''), "Clear error message on password length requirement")

# D. Successful update
new_test_pass = "BrandNewPass888!"
succ_res = client.post('/api/auth/profile', json={
    'current_password': test_pass,
    'new_password': new_test_pass,
    'confirm_password': new_test_pass
})
assert_test(succ_res.status_code == 200, "Valid password update returns 200")
assert_test(succ_res.get_json().get('success') is True, "Success flag in response")

# E. Verify login works with updated password and fails with old password
client.get('/logout')
fail_old_login = client.post('/api/auth/login', json={'email': test_email, 'password': test_pass})
assert_test(fail_old_login.status_code == 401, "Old password cannot log in after change")

succ_new_login = client.post('/api/auth/login', json={'email': test_email, 'password': new_test_pass})
assert_test(succ_new_login.status_code == 200, "New password successfully logs in")


print("\n" + "=" * 70)
print("=== TESTING FEATURE 2: FORGOT PASSWORD & SECURE RESET FLOW ===")
print("=" * 70)

# 1. Forgot password page loads
fp_page_res = client.get('/forgot-password')
assert_test(fp_page_res.status_code == 200, "Forgot password page loads (200)")
assert_test('Send Reset Link' in fp_page_res.get_data(as_text=True), "Forgot password page displays 'Send Reset Link' button")

# 2. Non-existent email returns generic message (no enumeration)
client.get('/logout')
with app.app_context():
    _reset_rate_limits.clear()

nonexistent_res = client.post('/api/auth/forgot-password', json={
    'email': 'nobody_exists_12345@resumeiq.ai'
})
assert_test(nonexistent_res.status_code == 200, "Non-existent email returns 200 generic response")
nonexist_data = nonexistent_res.get_json()
assert_test(nonexist_data.get('success') is True, "Success flag True for privacy")
assert_test('If an account is associated with this email' in nonexist_data.get('message', ''), "Generic confirmation message shown")
assert_test('dev_reset_url' not in nonexist_data, "No dev token generated for non-existent email")

# 3. Existing user forgot password request
existing_user_email = f"forgot_user_{secrets.token_hex(4)}@resumeiq.ai"
initial_user_pass = "ResetMe12345!"
client.post('/api/auth/register', json={
    'full_name': 'Forgot Tester',
    'email': existing_user_email,
    'password': initial_user_pass,
    'confirm_password': initial_user_pass
})

existing_fp_res = client.post('/api/auth/forgot-password', json={
    'email': existing_user_email
})
assert_test(existing_fp_res.status_code == 200, "Existing user forgot password returns 200")
existing_fp_data = existing_fp_res.get_json()
assert_test(existing_fp_data.get('success') is True, "Success flag True")
assert_test('If an account is associated with this email' in existing_fp_data.get('message', ''), "Generic confirmation message shown")
assert_test('notice' in existing_fp_data or 'dev_reset_url' in existing_fp_data, "SMTP notice or dev link supplied when SMTP is unconfigured")

# 4. Check DB for secure hashed token (never plain text)
with app.app_context():
    user = User.query.filter_by(email=existing_user_email).first()
    db_token = PasswordResetToken.query.filter_by(user_id=user.id).order_by(PasswordResetToken.created_at.desc()).first()
    assert_test(db_token is not None, "PasswordResetToken record created in DB")
    assert_test(db_token.is_used is False, "New token has is_used = False")
    assert_test(len(db_token.token_hash) == 64, "Token is stored as 64-char SHA-256 hash (never plain text)")
    assert_test(db_token.expires_at > datetime.utcnow(), "Token expiry set in the future (1 hour)")

# 5. Test Rate Limiting
print("\n--- Rate Limiting Verification ---")
with app.app_context():
    _reset_rate_limits.clear()

rate_email = f"ratelimit_{secrets.token_hex(4)}@resumeiq.ai"
for i in range(5):
    r = client.post('/api/auth/forgot-password', json={'email': rate_email})
    assert_test(r.status_code == 200, f"Request {i+1}/5 allowed within rate limit")

blocked_req = client.post('/api/auth/forgot-password', json={'email': rate_email})
assert_test(blocked_req.status_code == 429, "6th request is blocked by rate limiter (HTTP 429)")
assert_test('Too many password reset requests' in blocked_req.get_json().get('error', ''), "Clear rate limit error message returned")

# 6. Reset Password Page verification (/reset-password/<token>)
print("\n--- Reset Password Page & Token Verification ---")
with app.app_context():
    raw_token = user.create_reset_token(expires_hours=1)

# Valid token renders form
valid_token_res = client.get(f'/reset-password/{raw_token}')
assert_test(valid_token_res.status_code == 200, "Reset password page loads with valid token (200)")
valid_token_html = valid_token_res.get_data(as_text=True)
assert_test('id="resetForm"' in valid_token_html, "Form rendered when token is valid")
assert_test('Set New Password' in valid_token_html, "Heading 'Set New Password' rendered")

# Invalid token renders error state
invalid_res = client.get('/reset-password/completely-bogus-token')
assert_test(invalid_res.status_code == 200, "Reset page handles invalid token safely")
invalid_html = invalid_res.get_data(as_text=True)
assert_test('Link Expired or Invalid' in invalid_html, "Displays 'Link Expired or Invalid'")
assert_test('Request New Reset Link' in invalid_html, "Displays button to request a new link")

# Expired token renders expired message
with app.app_context():
    expired_raw = secrets.token_urlsafe(32)
    exp_hash = hashlib.sha256(expired_raw.encode('utf-8')).hexdigest()
    exp_rec = PasswordResetToken(
        user_id=user.id,
        token_hash=exp_hash,
        expires_at=datetime.utcnow() - timedelta(minutes=5),
        is_used=False
    )
    db.session.add(exp_rec)
    db.session.commit()

exp_res = client.get(f'/reset-password/{expired_raw}')
exp_html = exp_res.get_data(as_text=True)
assert_test('expired' in exp_html.lower(), "Expired token reports 'expired' message")

# 7. Reset Password Action & Token Reuse Prevention
print("\n--- Reset Password Submission & Single-Use Enforcement ---")
# Validation: passwords do not match
rp_mismatch = client.post('/api/auth/reset-password', json={
    'token': raw_token,
    'password': 'BrandNewPass123!',
    'confirm_password': 'MismatchedPass123!'
})
assert_test(rp_mismatch.status_code == 400, "Mismatched passwords rejected (400)")

# Validation: short password (< 8 chars)
rp_short = client.post('/api/auth/reset-password', json={
    'token': raw_token,
    'password': 'short',
    'confirm_password': 'short'
})
assert_test(rp_short.status_code == 400, "Short password rejected (400)")

# Successful password reset
reset_target_pass = "CompletelyFreshPass999!"
rp_success = client.post('/api/auth/reset-password', json={
    'token': raw_token,
    'password': reset_target_pass,
    'confirm_password': reset_target_pass
})
assert_test(rp_success.status_code == 200, "Reset password succeeds (200)")
assert_test(rp_success.get_json().get('success') is True, "Success flag in response")

# Token must now be marked used in DB
with app.app_context():
    token_hash_check = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    consumed_rec = PasswordResetToken.query.filter_by(token_hash=token_hash_check).first()
    assert_test(consumed_rec.is_used is True, "Token is marked is_used = True in DB")

# SINGLE USE ENFORCEMENT: Re-using the same token must fail
reuse_attempt = client.post('/api/auth/reset-password', json={
    'token': raw_token,
    'password': 'AnotherPassAttempt999!',
    'confirm_password': 'AnotherPassAttempt999!'
})
assert_test(reuse_attempt.status_code == 400, "Reusing consumed token is strictly rejected (400)")
assert_test('already been used' in reuse_attempt.get_json().get('error', '').lower(), "Clear message stating token has already been used")

# Visiting the reset URL with consumed token also displays expired/used notice
consumed_page_res = client.get(f'/reset-password/{raw_token}')
assert_test('already been used' in consumed_page_res.get_data(as_text=True).lower(), "Reset page displays token already used message")

# 8. Login verification after password reset
print("\n--- Login with Reset Password ---")
old_pass_login = client.post('/api/auth/login', json={
    'email': existing_user_email,
    'password': initial_user_pass
})
assert_test(old_pass_login.status_code == 401, "Old password cannot log in after reset")

new_pass_login = client.post('/api/auth/login', json={
    'email': existing_user_email,
    'password': reset_target_pass
})
assert_test(new_pass_login.status_code == 200, "New reset password logs in successfully (200)")
assert_test(new_pass_login.get_json().get('success') is True, "Login response success True")

print("\n" + "=" * 70)
print(f"RESULTS: {passed_count} PASSED, {failed_count} FAILED")
print("=" * 70)

if failed_count > 0:
    sys.exit(1)
else:
    sys.exit(0)
