# 🏥 Valenzuela District 1 — Barangay EMR System v2
### Electronic Medical Records — Standalone Web-Based System

---

## 📋 Overview

A **standalone, web-based EMR system** for Barangay-level health management. Each barangay runs its own instance with its own database — no internet required, accessible via local network browser.

**Currently supports:**
- Barangay Veinte Reales
- Barangay Dalandanan

---

## 🧱 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy ORM |
| **Database** | MySQL 8.0+ |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Charts** | Chart.js 4.x + ChartDataLabels plugin |
| **PDF Reports** | ReportLab |
| **Analytics** | Pandas |
| **Security** | bcrypt, JWT, slowapi (rate limiting) |

---

## 📂 Project Structure

```
emr_v2/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── database.py                # Dynamic dual-DB connection
│   ├── reset_admin_password.py    # Run once after DB setup
│   ├── requirements.txt
│   ├── .env.example               # Config template
│   ├── routers/
│   │   ├── auth.py                # Login, logout, change password
│   │   ├── users.py               # BHW management (no OTP)
│   │   ├── patients.py            # Patient CRUD
│   │   ├── analytics.py           # Disease trend analytics
│   │   └── reports.py             # PDF report generation
│   ├── models/
│   │   └── models.py              # SQLAlchemy ORM models
│   ├── middleware/
│   │   └── auth.py                # JWT auth, audit logging
│   └── utils/
│       └── security.py            # bcrypt, JWT, password utils
├── database/
│   └── schema.sql                 # Run this to create both DBs
└── frontend/
    ├── pages/
    │   ├── login.html             # Login page
    │   ├── dashboard.html         # Main dashboard + analytics
    │   └── patients.html          # Patient profiles + records
    └── js/
        ├── api.js                 # API communication + toasts
        └── session.js             # Session timeout + screen lock
```

---

## 🚀 Setup Guide

### Prerequisites
- Python 3.10 or higher
- MySQL 8.0 or higher
- pip

---

### Step 1 — Run the Database Schema

Open **MySQL Workbench** or any MySQL client, then copy-paste the contents of `database/schema.sql` and execute.

This creates **two separate databases**:
- `emr_veinte_reales`
- `emr_dalandanan`

---

### Step 2 — Create Virtual Environment

```powershell
cd C:\CAPSTONE\emr_v2\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

### Step 3 — Configure Environment

```powershell
# Copy the template
copy .env.example .env

# Open and edit .env
notepad .env
```

**Required values to fill in:**

```env
# Which barangay is this instance for?
BARANGAY_DB=emr_veinte_reales
BARANGAY_NAME=Barangay Veinte Reales

# Your MySQL credentials
DB_USER=root
DB_PASSWORD=your_mysql_password_here

# Any long random string (min 32 chars)
SECRET_KEY=put_any_long_random_string_here_minimum_32_characters

DEBUG=True
```

---

### Step 4 — Reset Admin Password

```powershell
venv\Scripts\python reset_admin_password.py
```

Expected output:
```
✅ Connected to database: emr_veinte_reales (Barangay Veinte Reales)
✅ Admin password reset — database: Barangay Veinte Reales
   Email:    admin@vientereales.gov.ph
   Password: Admin@123
   ⚠️  Change this password after first login!
```

---

### Step 5 — Start the Server

```powershell
venv\Scripts\python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
🚀 EMR System starting — Barangay Veinte Reales
✅ Connected to database: emr_veinte_reales (Barangay Veinte Reales)
✅ Ready.
INFO: Uvicorn running on http://0.0.0.0:8000
```

---

### Step 6 — Open in Browser

```
http://localhost:8000
```

Login with:
- **Email:** `admin@vientereales.gov.ph`
- **Password:** `Admin@123`

> ⚠️ Change the password immediately after first login!

---

## 🏘️ Setting Up Barangay Dalandanan (Second Instance)

Copy the entire `backend/` folder to a new location, or simply use a different `.env` file:

```powershell
# Option: run on a different port on the same machine
# Edit .env:
BARANGAY_DB=emr_dalandanan
BARANGAY_NAME=Barangay Dalandanan
APP_PORT=8001

# Run on port 8001
venv\Scripts\python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001

# Reset admin for Dalandanan
venv\Scripts\python reset_admin_password.py
```

Open: `http://localhost:8001`
Login: `admin@dalandanan.gov.ph` / `Admin@123`

---

## 🌐 LAN Access (Other Computers on Same Network)

Once the server is running, other computers on the same WiFi/LAN can access it:

```
# Find your computer's IP address:
ipconfig

# Other computers open:
http://192.168.1.x:8000
```

No internet required — fully local network.

---

## 👥 User Roles & Permissions

| Feature | Admin | BHW |
|---------|:-----:|:---:|
| View all patients | ✅ | ✅ |
| Add / edit patients | ✅ | ✅ |
| Archive patients | ✅ | ❌ |
| Add medical records | ✅ | ✅ |
| Add immunizations | ✅ | ✅ |
| Add pregnancy records | ✅ | ✅ |
| Edit health problems | ✅ | ✅ |
| View disease analytics | ✅ | ✅ |
| Generate PDF reports | ✅ | ❌ |
| Manage BHW accounts | ✅ | ❌ |
| View audit logs | ✅ | ❌ |

---

## 🛡️ Security Features

| Feature | Details |
|---------|---------|
| **Password hashing** | bcrypt (12 rounds) |
| **Authentication** | JWT tokens (60-min expiry) |
| **Brute force protection** | 5 failed attempts → 15-min lockout |
| **Session timeout** | 30 minutes idle → screen lock |
| **SQL injection** | SQLAlchemy ORM — no raw SQL |
| **Rate limiting** | slowapi — 30 req/min on health endpoint |
| **Security headers** | X-Frame-Options, CSP, HSTS, XSS-Protection |
| **Audit logging** | LOGIN and LOGOUT events only |
| **OTP** | Removed — not required for BHW registration |

---

## 🗄️ Database Tables

| Table | Purpose |
|-------|---------|
| `users` | Admin and BHW accounts |
| `patient` | Patient records |
| `health_problems` | Allergies, asthma, chronic diseases (input only) |
| `pregnancy` | Pregnancy records (female patients only) |
| `medical_records` | Visit/consultation records |
| `immunization` | Vaccination records |
| `disease` | Master disease list |
| `disease_cases` | Auto-counted from diagnosis field |
| `audit_log` | Login/logout events |

---

## 📊 Disease Auto-Counting

When a medical record is saved with a **diagnosis**, the system automatically:

1. Reads the diagnosis text
2. Matches it against known disease patterns
3. Records a case in `disease_cases` table
4. Updates the surveillance dashboard

**Example normalizations:**
```
"Mild Influenza"    → Influenza
"Severe Flu"        → Influenza
"Gripe"             → Influenza
"DHF"               → Dengue Fever
"Community-acquired pneumonia" → Pneumonia
"Hypertension"      → Hypertension
```

> ⚠️ Health Problems (allergies, asthma, chronic diseases) are **NOT** counted — they are for patient records only.

---

## 📄 PDF Reports (Admin Only)

| Report | Contents |
|--------|---------|
| **Patient Records** | All registered patients with demographics |
| **Disease Trends** | Monthly case counts per disease |
| **Immunization** | Complete vaccination records |

---

## 🐞 Common Issues

**"Database connection failed"**
→ Check `DB_PASSWORD` in `.env`. Make sure MySQL is running.

**"Module not found: passlib"**
→ Run: `pip install passlib[bcrypt]`
→ Or it's already using `bcrypt` directly — check `security.py`

**Charts not showing**
→ Check browser console (F12). Year filter might be wrong — make sure it matches the year of your records.

**Admin features not showing after login**
→ Open browser console and type: `sessionStorage.getItem('user_role')`
→ Should return `"admin"`. If not, check the login response from the API.

**"Access denied for user 'emr_user'"**
→ Your `.env` still has `DB_USER=emr_user`. Change to `DB_USER=root`.

---

## 📞 Support

- **System Administrator:** Change email in schema.sql before running
- **District 1 Health Office, Valenzuela City**

---

*© 2025 Valenzuela City District 1 Health Office. All Rights Reserved.*
*EMR System v2.0 — Standalone Web-Based Barangay Health Information System*
