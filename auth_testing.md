# Auth testing notes
- Login: POST /api/auth/login {email,password} sets httpOnly cookies access_token (60 min) + refresh_token (7 d), secure + samesite=none.
- /api/auth/refresh renews cookies. Frontend auto-retries on 401.
- Brute force: 5 failed attempts per ip+email → 429 for 15 minutes.
- Register creates affiliate with verified=false; 6-digit code (24h) is emailed; while email sending is not configured the code body is visible in admin "Registro email" (GET /api/admin/emails).
- Forgot/reset: 6-digit code valid 30 minutes, max 5 tries; response never reveals whether the email exists.
- Admin seeded from ADMIN_EMAIL / ADMIN_PASSWORD (only if missing). Credentials in /app/memory/test_credentials.md.
