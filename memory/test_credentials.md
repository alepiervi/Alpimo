# Test credentials – Portale Affiliati Alpimo

| Ruolo | Email | Password |
|---|---|---|
| Admin principale (super) | admin@alpimo.it | Alpimo-Admin-2026 |
| Affiliato in attesa di approvazione | sole@demo.it | demo1234 |
| Affiliato approvato (loghi pronti, URL verificati) | mario@demo.it | demo1234 |
| Affiliato con sito consegnato (dominio in scadenza tra 6 gg) | blu@demo.it | demo1234 |

Auth endpoints: POST /api/auth/register, /api/auth/login, /api/auth/logout, /api/auth/refresh, GET /api/auth/me,
POST /api/auth/verify, /api/auth/resend, /api/auth/forgot, /api/auth/reset, /api/auth/accept-terms, /api/auth/change-password.

Codes for email verification / password reset are visible to the admin in "Registro email" (GET /api/admin/emails),
because real email sending (Aruba/Brevo) is not configured yet.
