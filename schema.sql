-- ============================================================
-- EMR SYSTEM - DISTRICT 1 DATABASE SCHEMA
-- Isang database para sa lahat ng barangay sa District 1
-- May dagdag na columns para sa security at audit trail
-- ============================================================

CREATE DATABASE IF NOT EXISTS emr_district1
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE emr_district1;

-- ============================================================
-- 1. BARANGAY TABLE
-- Listahan ng lahat ng barangay sa District 1
-- ============================================================
CREATE TABLE IF NOT EXISTS barangay (
    barangay_id     INT AUTO_INCREMENT PRIMARY KEY,
    barangay_name   VARCHAR(100) NOT NULL,
    district        VARCHAR(50)  NOT NULL DEFAULT 'District 1',
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_barangay_name (barangay_name)
) ENGINE=InnoDB;

-- ============================================================
-- 2. USERS TABLE
-- Mga account ng Admin at BHW na gumagamit ng sistema
-- Password ay naka-hash (bcrypt) para sa seguridad
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    user_id             INT AUTO_INCREMENT PRIMARY KEY,
    barangay_id         INT          NULL,  -- NULL kung Admin (walang specific barangay)
    name                VARCHAR(150) NOT NULL,
    email               VARCHAR(150) NOT NULL UNIQUE,  -- Para sa OTP at login
    password_hash       VARCHAR(255) NOT NULL,          -- Bcrypt hashed password
    role                ENUM('admin','bhw') NOT NULL DEFAULT 'bhw',
    position            VARCHAR(100) NULL,
    status              ENUM('active','inactive','locked') NOT NULL DEFAULT 'active',
    failed_attempts     INT          NOT NULL DEFAULT 0,  -- Para sa brute-force protection
    locked_until        DATETIME     NULL,                -- Lock time pagkatapos ng maraming failed attempts
    last_login          DATETIME     NULL,
    created_at          DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (barangay_id) REFERENCES barangay(barangay_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ============================================================
-- 3. OTP TABLE
-- Para sa One-Time Password ng Admin bago mag-register ng bagong BHW
-- ============================================================
CREATE TABLE IF NOT EXISTS otp_tokens (
    otp_id      INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT          NOT NULL,   -- Admin na nag-request ng OTP
    otp_code    VARCHAR(10)  NOT NULL,   -- Hashed OTP code
    purpose     VARCHAR(50)  NOT NULL DEFAULT 'registration', -- 'registration' or 'unlock'
    expires_at  DATETIME     NOT NULL,   -- OTP mag-eexpire after 10 minutes
    is_used     TINYINT(1)   NOT NULL DEFAULT 0,
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 4. PATIENT TABLE
-- Impormasyon ng bawat pasyente
-- Naka-link sa barangay kung saan sila nakatira
-- ============================================================
CREATE TABLE IF NOT EXISTS patient (
    patient_id      INT AUTO_INCREMENT PRIMARY KEY,
    barangay_id     INT          NOT NULL,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    middle_name     VARCHAR(100) NULL,
    birthdate       DATE         NOT NULL,
    sex             ENUM('Male','Female') NOT NULL,
    civil_status    ENUM('Single','Married','Widowed','Separated') NULL,
    address         TEXT         NOT NULL,
    contact_number  VARCHAR(20)  NULL,
    philhealth_no   VARCHAR(30)  NULL,  -- Dagdag na column para sa PhilHealth
    is_archived     TINYINT(1)   NOT NULL DEFAULT 0,  -- Soft delete
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (barangay_id) REFERENCES barangay(barangay_id)
) ENGINE=InnoDB;

-- Index para mas mabilis ang paghahanap ng pasyente
CREATE INDEX idx_patient_name    ON patient (last_name, first_name);
CREATE INDEX idx_patient_barangay ON patient (barangay_id);

-- ============================================================
-- 5. MEDICAL RECORDS TABLE
-- Bawat visit/konsultasyon ng pasyente
-- Naka-link sa patient at sa user (BHW/Admin) na nag-encode
-- ============================================================
CREATE TABLE IF NOT EXISTS medical_records (
    record_id       INT AUTO_INCREMENT PRIMARY KEY,
    patient_id      INT          NOT NULL,
    visit_date      DATE         NOT NULL,
    chief_complaint VARCHAR(500) NULL,   -- Dagdag: pangunahing reklamo ng pasyente
    symptoms        TEXT         NULL,
    diagnosis       TEXT         NULL,
    treatment       TEXT         NULL,
    blood_pressure  VARCHAR(20)  NULL,   -- Dagdag: vital signs
    temperature     DECIMAL(4,1) NULL,
    weight_kg       DECIMAL(5,2) NULL,
    height_cm       DECIMAL(5,2) NULL,
    notes           TEXT         NULL,
    user_id         INT          NOT NULL,  -- Sino ang nag-encode
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patient(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)    REFERENCES users(user_id)
) ENGINE=InnoDB;

CREATE INDEX idx_record_patient   ON medical_records (patient_id);
CREATE INDEX idx_record_visitdate ON medical_records (visit_date);

-- ============================================================
-- 6. IMMUNIZATION TABLE
-- Record ng mga bakuna na natanggap ng pasyente
-- ============================================================
CREATE TABLE IF NOT EXISTS immunization (
    immunization_id     INT AUTO_INCREMENT PRIMARY KEY,
    patient_id          INT          NOT NULL,
    vaccine_name        VARCHAR(150) NOT NULL,
    date_given          DATE         NOT NULL,
    dose_number         INT          NULL DEFAULT 1,   -- Dagdag: ika-ilang dose
    administered_by     VARCHAR(150) NULL,             -- Pangalan ng nagbigay ng bakuna
    batch_number        VARCHAR(50)  NULL,             -- Batch number ng bakuna
    next_schedule       DATE         NULL,             -- Susunod na schedule
    remarks             TEXT         NULL,
    user_id             INT          NOT NULL,
    created_at          DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patient(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)    REFERENCES users(user_id)
) ENGINE=InnoDB;

-- ============================================================
-- 7. DISEASE TABLE
-- Master list ng mga sakit / karamdaman
-- ============================================================
CREATE TABLE IF NOT EXISTS disease (
    disease_id      INT AUTO_INCREMENT PRIMARY KEY,
    disease_name    VARCHAR(200) NOT NULL UNIQUE,
    icd_code        VARCHAR(20)  NULL,   -- Dagdag: ICD-10 code ng sakit
    category        VARCHAR(100) NULL,   -- e.g. Communicable, Non-communicable
    is_notifiable   TINYINT(1)   NOT NULL DEFAULT 0,  -- Kung kailangan i-report sa DOH
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- 8. DISEASE CASES TABLE (Para sa Analytics / Trend Dashboard)
-- Bilang ng kaso bawat sakit, bawat barangay, bawat araw
-- ============================================================
CREATE TABLE IF NOT EXISTS disease_cases (
    case_id             INT AUTO_INCREMENT PRIMARY KEY,
    disease_id          INT          NOT NULL,
    barangay_id         INT          NOT NULL,
    patient_id          INT          NULL,   -- Dagdag: para ma-link sa specific na pasyente
    date_recorded       DATE         NOT NULL,
    number_of_cases     INT          NOT NULL DEFAULT 1,
    age_group           VARCHAR(20)  NULL,   -- e.g. '0-5', '6-12', '13-17', '18-59', '60+'
    sex                 ENUM('Male','Female','Both') NULL,
    remarks             TEXT         NULL,
    user_id             INT          NOT NULL,
    created_at          DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (disease_id)  REFERENCES disease(disease_id),
    FOREIGN KEY (barangay_id) REFERENCES barangay(barangay_id),
    FOREIGN KEY (patient_id)  REFERENCES patient(patient_id) ON DELETE SET NULL,
    FOREIGN KEY (user_id)     REFERENCES users(user_id)
) ENGINE=InnoDB;

CREATE INDEX idx_cases_disease  ON disease_cases (disease_id);
CREATE INDEX idx_cases_barangay ON disease_cases (barangay_id);
CREATE INDEX idx_cases_date     ON disease_cases (date_recorded);

-- ============================================================
-- 9. AUDIT LOG TABLE
-- Lahat ng aksyon ng bawat user ay nire-record dito
-- Para sa security monitoring at accountability
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    log_id      INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT          NULL,   -- NULL kung hindi pa naka-login (e.g. failed login)
    action      VARCHAR(500) NOT NULL,  -- Deskripsyon ng ginawa (e.g. "LOGIN", "EDIT PATIENT")
    table_name  VARCHAR(50)  NULL,   -- Kung aling table ang na-affect
    record_id   INT          NULL,   -- ID ng na-affect na record
    ip_address  VARCHAR(45)  NULL,   -- IP address ng user
    user_agent  VARCHAR(500) NULL,   -- Browser info
    date_time   DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE INDEX idx_audit_user     ON audit_log (user_id);
CREATE INDEX idx_audit_datetime ON audit_log (date_time);

-- ============================================================
-- 10. SESSIONS TABLE
-- Para sa server-side session management (mas secure kaysa JWT-only)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id      VARCHAR(128) PRIMARY KEY,  -- Random UUID
    user_id         INT          NOT NULL,
    ip_address      VARCHAR(45)  NULL,
    user_agent      VARCHAR(500) NULL,
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    expires_at      DATETIME     NOT NULL,
    is_active       TINYINT(1)   NOT NULL DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- SAMPLE DATA - Mga barangay sa District 1 ng Caloocan
-- ============================================================
INSERT INTO barangay (barangay_name, district) VALUES
('Barangay 1',  'District 1'),
('Barangay 2',  'District 1'),
('Barangay 3',  'District 1'),
('Barangay 4',  'District 1'),
('Barangay 5',  'District 1'),
('Barangay 6',  'District 1'),
('Barangay 7',  'District 1'),
('Barangay 8',  'District 1'),
('Barangay 9',  'District 1'),
('Barangay 10', 'District 1'),
('Barangay 11', 'District 1'),
('Barangay 12', 'District 1'),
('Barangay 13', 'District 1'),
('Barangay 14', 'District 1'),
('Barangay 15', 'District 1');

-- Sample Admin account (password: Admin@123 - dapat palitan agad!)
-- Ang password_hash na ito ay bcrypt hash ng "Admin@123"
INSERT INTO users (barangay_id, name, email, password_hash, role, position, status)
VALUES (NULL, 'System Administrator', 'admin@district1.gov.ph',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMqJqhcanFp8.mMHtdTNbX1i3y',
        'admin', 'Health Information Officer', 'active');

-- Sample na mga sakit para sa disease master list
INSERT INTO disease (disease_name, icd_code, category, is_notifiable) VALUES
('Dengue Fever',           'A90',   'Communicable',     1),
('Influenza',              'J11',   'Communicable',     0),
('Tuberculosis',           'A15',   'Communicable',     1),
('COVID-19',               'U07.1', 'Communicable',     1),
('Hypertension',           'I10',   'Non-communicable', 0),
('Diabetes Mellitus',      'E11',   'Non-communicable', 0),
('Pneumonia',              'J18',   'Communicable',     1),
('Diarrhea',               'A09',   'Communicable',     0),
('Leptospirosis',          'A27',   'Communicable',     1),
('Typhoid Fever',          'A01',   'Communicable',     1),
('Acute Respiratory Infection', 'J06', 'Communicable', 0),
('Chickenpox',             'B01',   'Communicable',     0),
('Measles',                'B05',   'Communicable',     1),
('Malnutrition',           'E46',   'Non-communicable', 1),
('Asthma',                 'J45',   'Non-communicable', 0);
