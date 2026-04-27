# 🏥 District 1 Health EMR System
### Electronic Medical Records with Disease Trend Analytics

---

## 📋 Overview

Isang **standalone EMR (Electronic Medical Records) System** para sa District 1 Health Office na may integrated na **Disease Trend Analytics Dashboard**. Dinisenyo para sa secure, efficient, at user-friendly na pamamahala ng mga rekord ng pasyente at kalusugan ng komunidad.

---

## 🧱 Tech Stack

| Layer       | Technology                              |
|-------------|-----------------------------------------|
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy       |
| **Database**| MySQL 8.0+                              |
| **Frontend**| HTML5, CSS3, Vanilla JavaScript         |
| **Charts**  | Chart.js 4.x                            |
| **PDF**     | ReportLab                               |
| **Security**| bcrypt, JWT (python-jose), slowapi      |

---

## 📂 Project Structure

```
emr_system/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── database.py             # DB connection & session
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment config template
│   ├── models/
│   │   └── models.py           # SQLAlchemy ORM models
│   ├── schemas/
│   │   └── schemas.py          # Pydantic validation schemas
│   ├── routers/
│   │   ├── auth.py             # Login, OTP, logout
│   │   ├── users.py            # BHW account management
│   │   ├── patients.py         # Patient CRUD
│   │   ├── analytics.py        # Disease trend analytics
│   │   └── reports.py          # PDF report generation
│   ├── middleware/
│   │   └── auth.py             # JWT auth, audit logging
│   └── utils/
│       ├── security.py         # Password hash, JWT, OTP
│       └── email_utils.py      # SMTP email sending
├── frontend/
│   ├── pages/
│   │   ├── login.html          # Login page
│   │   └── dashboard.html      # Main dashboard
│   ├── js/
│   │   ├── api.js              # API communication utility
│   │   ├── dashboard.js        # Dashboard logic
│   │   ├── patients.js         # Patient management
│   │   ├── analytics.js        # Chart rendering
│   │   └── session.js          # Session timeout logic
│   └── css/
│       └── global.css          # Global stylesheet
├── database/
│   └── schema.sql              # Complete DB schema
├── setup.sh                    # Setup script
└── README.md                   # This file
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- MySQL 8.0+
- pip (Python package manager)

### 2. Clone/Download the project
```bash
cd emr_system
```

### 3. Run the setup script
```bash
bash setup.sh
```

### 4. Configure environment
```bash
# I-edit ang .env file at lagyan ng tamang values
nano backend/.env
```

Importanteng i-fill in:
```env
DB_HOST=localhost
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
```

### 5. I-setup ang database
```bash
mysql -u root -p < database/schema.sql
```

### 6. I-start ang server
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Buksan ang browser
```
http://localhost:8000
```

---

## 🔐 Default Login

| Field    | Value                          |
|----------|-------------------------------|
| Email    | `admin@district1.gov.ph`      |
| Password | `Admin@123`                   |

> ⚠️ **PALITAN ANG PASSWORD AGAD pagkatapos ng unang login!**

---

## 👥 User Roles & Permissions

| Feature                          | Admin | BHW |
|----------------------------------|:-----:|:---:|
| View all patients (all barangay) |  ✅  |  ❌ |
| View patients (own barangay)     |  ✅  |  ✅ |
| Add/edit patients                |  ✅  |  ✅ |
| Archive patients                 |  ✅  |  ❌ |
| Encode medical records           |  ✅  |  ✅ |
| Encode immunization records      |  ✅  |  ✅ |
| Record disease cases             |  ✅  |  ✅ |
| View disease trend analytics     |  ✅  |  ✅ |
| Generate & download PDF reports  |  ✅  |  ❌ |
| Manage BHW accounts              |  ✅  |  ❌ |
| View audit logs                  |  ✅  |  ❌ |
| System settings                  |  ✅  |  ❌ |

---

## 🛡️ Security Features

### 1. Authentication
- **bcrypt password hashing** — hindi mababasa ang mga password kahit ma-access ang database
- **JWT tokens** — stateless authentication na may expiration
- **Rate limiting** — proteksyon laban sa brute-force attacks

### 2. Login Protection
- **Maximum 5 failed login attempts** bago ma-lock ang account
- **Account lockout ng 15 minuto** pagkatapos ng sobrang daming failed attempts
- **IP address logging** ng lahat ng login attempts

### 3. SQL Injection Prevention
- Gumagamit ng **SQLAlchemy ORM** para sa lahat ng database queries
- **Parameterized queries** — walang raw SQL string concatenation
- **Pydantic validation** ng lahat ng input data

### 4. Session Security
- **Session timeout ng 30 minuto** ng inactivity
- **Automatic screen lock** na nag-re-require ng password para ma-unlock
- **SessionStorage** (hindi localStorage) para sa tokens

### 5. HTTP Security Headers
- `X-Frame-Options: DENY` — kontra sa clickjacking
- `X-Content-Type-Options: nosniff` — kontra sa MIME sniffing
- `Content-Security-Policy` — kontra sa XSS
- `Strict-Transport-Security` — HTTPS enforcement

### 6. OTP Verification
- **SHA-256 hashed OTP** bago i-store sa database
- **10-minute expiration** ng OTP
- **Single-use** — hindi na magagamit ulit ang ginamit na OTP

### 7. Audit Logging
- Lahat ng **login/logout** ay nire-record
- Lahat ng **CRUD operations** ay may audit trail
- **IP address** at **user agent** ay kasama sa logs

### 8. XSS Prevention
- `escapeHtml()` function para sa lahat ng user-generated content
- Content Security Policy headers

---

## 📊 Database Schema

| Table           | Description                                    |
|-----------------|------------------------------------------------|
| `barangay`      | Master list ng mga barangay sa District 1       |
| `users`         | Admin at BHW accounts (may lockout tracking)    |
| `otp_tokens`    | Hashed OTP para sa BHW registration             |
| `patient`       | Patient records na may soft delete              |
| `medical_records`| Visit/consultation records per patient         |
| `immunization`  | Vaccination records per patient                 |
| `disease`       | Master list ng mga sakit (may ICD-10 codes)     |
| `disease_cases` | Aggregated disease cases para sa analytics      |
| `audit_log`     | Complete audit trail ng lahat ng aksyon         |
| `user_sessions` | Server-side session tracking                    |

---

## 📄 PDF Reports Available (Admin Only)

1. **Patient Records Report** — Complete list ng mga pasyente per barangay
2. **Disease Trend Report** — Monthly disease statistics at per-barangay breakdown
3. **Immunization Report** — Complete vaccination records per patient

---

## 🔧 Configuration Reference

### Environment Variables (`.env`)

| Variable                     | Description                        | Default           |
|-----------------------------|------------------------------------|-------------------|
| `DB_HOST`                   | MySQL host address                 | `localhost`       |
| `DB_PORT`                   | MySQL port                         | `3306`            |
| `DB_NAME`                   | Database name                      | `emr_district1`   |
| `DB_USER`                   | MySQL username                     | —                 |
| `DB_PASSWORD`               | MySQL password                     | —                 |
| `SECRET_KEY`                | JWT signing key (change this!)     | —                 |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| Token validity duration           | `60`              |
| `SMTP_HOST`                 | Email server host                  | `smtp.gmail.com`  |
| `SMTP_PORT`                 | Email server port                  | `587`             |
| `SMTP_USER`                 | Email username                     | —                 |
| `SMTP_PASSWORD`             | Email app password                 | —                 |
| `OTP_EXPIRE_MINUTES`        | OTP validity duration              | `10`              |
| `DEBUG`                     | Enable debug mode                  | `False`           |

---

## 📝 API Endpoints Reference

### Authentication
| Method | Endpoint              | Description               | Access |
|--------|-----------------------|---------------------------|--------|
| POST   | `/api/auth/login`     | User login                | Public |
| POST   | `/api/auth/logout`    | User logout               | Auth   |
| POST   | `/api/auth/request-otp` | Request OTP             | Admin  |
| POST   | `/api/auth/verify-otp`  | Verify OTP              | Admin  |
| POST   | `/api/auth/change-password` | Change password    | Auth   |
| GET    | `/api/auth/me`        | Get current user info     | Auth   |

### Users (Admin Only)
| Method | Endpoint           | Description         |
|--------|--------------------|---------------------|
| GET    | `/api/users/`      | List all users      |
| POST   | `/api/users/register` | Register BHW     |
| GET    | `/api/users/{id}`  | Get user details    |
| PUT    | `/api/users/{id}`  | Update user         |
| DELETE | `/api/users/{id}`  | Deactivate user     |

### Patients
| Method | Endpoint              | Description            | Access       |
|--------|-----------------------|------------------------|--------------|
| GET    | `/api/patients/`      | List patients (filtered)| Auth        |
| POST   | `/api/patients/`      | Add patient            | Auth         |
| GET    | `/api/patients/{id}`  | Get patient details    | Auth         |
| PUT    | `/api/patients/{id}`  | Update patient         | Auth         |
| DELETE | `/api/patients/{id}`  | Archive patient        | Admin        |

### Analytics
| Method | Endpoint                               | Description              |
|--------|----------------------------------------|--------------------------|
| GET    | `/api/analytics/disease-trends`        | Monthly trend chart data |
| GET    | `/api/analytics/disease-per-barangay`  | Per-barangay bar data    |
| GET    | `/api/analytics/top-diseases`          | Top diseases pie data    |
| GET    | `/api/analytics/age-distribution`      | Age group data           |
| GET    | `/api/analytics/dashboard-summary`     | Dashboard stat cards     |

### Reports (Admin Only)
| Method | Endpoint                       | Description               |
|--------|--------------------------------|---------------------------|
| GET    | `/api/reports/patients`        | Download patient PDF      |
| GET    | `/api/reports/disease-trends`  | Download disease PDF      |
| GET    | `/api/reports/immunization`    | Download immunization PDF |

---

## 🐞 Troubleshooting

**"Database connection failed"**
→ Suriin ang DB credentials sa `.env`. Siguraduhing tumatakbo ang MySQL.

**"OTP email not sending"**
→ Sa Gmail, kailangan ng App Password (hindi regular password).
→ Sundan: Google Account → Security → App Passwords

**"Access denied" errors**
→ Suriin ang role ng user (Admin vs BHW).
→ BHW ay may limitadong access sa records ng ibang barangay.

**Rate limit exceeded**
→ Hintayin ang 1 minuto bago muling subukan.
→ Para sa development, i-disable ang rate limiting sa `main.py`.

---

## 📞 Support

Para sa mga katanungan o issues, makipag-ugnayan sa:
- **System Administrator**: admin@district1.gov.ph
- **District 1 Health Office**: District 1, Caloocan City

---

*© 2025 District 1 Health Office, Caloocan City. All Rights Reserved.*
