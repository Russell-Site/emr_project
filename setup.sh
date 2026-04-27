#!/bin/bash
# ============================================================
# setup.sh — EMR System Setup Script
# I-run ito para i-install ang lahat ng dependencies at i-setup
# ang sistema para sa unang beses na paggamit.
# Paano gamitin: bash setup.sh
# ============================================================

set -e  # Ihinto ang script kung may error

# --- Color codes para sa output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       District 1 Health EMR System — Setup Script       ║"
echo "║                 Version 1.0.0                            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ---- Step 1: Suriin ang Python version ----
echo -e "${BLUE}[1/6] Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.10 or higher.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python ${PYTHON_VERSION} found.${NC}"

# ---- Step 2: Gumawa ng virtual environment ----
echo -e "${BLUE}[2/6] Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created.${NC}"
else
    echo -e "${YELLOW}⚠️  Virtual environment already exists. Skipping.${NC}"
fi

# I-activate ang virtual environment
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
echo -e "${GREEN}✅ Virtual environment activated.${NC}"

# ---- Step 3: I-install ang Python packages ----
echo -e "${BLUE}[3/6] Installing Python dependencies...${NC}"
pip install --upgrade pip -q
pip install -r backend/requirements.txt -q
echo -e "${GREEN}✅ Python packages installed.${NC}"

# ---- Step 4: Gumawa ng .env file ----
echo -e "${BLUE}[4/6] Setting up environment configuration...${NC}"
if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env

    # Gumawa ng random secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/your_super_secret_key_here_change_this/${SECRET_KEY}/" backend/.env

    echo -e "${GREEN}✅ .env file created from template.${NC}"
    echo -e "${YELLOW}⚠️  Please edit backend/.env and fill in your database credentials!${NC}"
else
    echo -e "${YELLOW}⚠️  .env file already exists. Skipping.${NC}"
fi

# ---- Step 5: Database setup instructions ----
echo -e "${BLUE}[5/6] Database setup instructions...${NC}"
echo -e "${YELLOW}"
echo "  To set up the MySQL database:"
echo "  1. Make sure MySQL is running"
echo "  2. Log in: mysql -u root -p"
echo "  3. Run: source database/schema.sql"
echo "  OR use the command below:"
echo "  mysql -u root -p < database/schema.sql"
echo -e "${NC}"

# ---- Step 6: Tseklis ng mga files ----
echo -e "${BLUE}[6/6] Verifying project structure...${NC}"

files_to_check=(
    "backend/main.py"
    "backend/database.py"
    "backend/requirements.txt"
    "backend/.env"
    "backend/routers/auth.py"
    "backend/routers/users.py"
    "backend/routers/patients.py"
    "backend/routers/analytics.py"
    "backend/routers/reports.py"
    "backend/models/models.py"
    "backend/schemas/schemas.py"
    "backend/utils/security.py"
    "backend/utils/email_utils.py"
    "backend/middleware/auth.py"
    "frontend/pages/login.html"
    "frontend/pages/dashboard.html"
    "frontend/js/api.js"
    "frontend/js/dashboard.js"
    "frontend/js/patients.js"
    "frontend/js/analytics.js"
    "frontend/js/session.js"
    "frontend/css/global.css"
    "database/schema.sql"
)

all_good=true
for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✅ $file${NC}"
    else
        echo -e "  ${RED}❌ MISSING: $file${NC}"
        all_good=false
    fi
done

# ---- Gumawa ng mga __init__.py files ----
touch backend/__init__.py
touch backend/routers/__init__.py
touch backend/models/__init__.py
touch backend/schemas/__init__.py
touch backend/utils/__init__.py
touch backend/middleware/__init__.py

echo ""
if $all_good; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗"
    echo -e "║         ✅ Setup Complete! System is ready.              ║"
    echo -e "╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}To start the server:${NC}"
    echo -e "  ${YELLOW}cd backend && python main.py${NC}"
    echo ""
    echo -e "${CYAN}Or with uvicorn directly:${NC}"
    echo -e "  ${YELLOW}cd backend && uvicorn main:app --reload --port 8000${NC}"
    echo ""
    echo -e "${CYAN}Then open your browser:${NC}"
    echo -e "  ${YELLOW}http://localhost:8000${NC}"
    echo ""
    echo -e "${CYAN}Default Admin Login:${NC}"
    echo -e "  Email:    ${YELLOW}admin@district1.gov.ph${NC}"
    echo -e "  Password: ${YELLOW}Admin@123${NC}"
    echo -e "  ${RED}⚠️  CHANGE THIS PASSWORD IMMEDIATELY AFTER FIRST LOGIN!${NC}"
else
    echo -e "${RED}╔══════════════════════════════════════════════════════════╗"
    echo -e "║     ❌ Some files are missing. Please check above.       ║"
    echo -e "╚══════════════════════════════════════════════════════════╝${NC}"
fi
