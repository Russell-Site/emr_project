/* ============================================================
   dashboard.js - Dashboard Initialization & Navigation
   Naglo-load ng stats, charts, at pinamamahalaan ang navigation
   ============================================================ */

/* ---- I-check muna ang authentication ---- */
if (!requireAuth()) {
    // requireAuth() na mag-re-redirect kung walang session
}

/* ---- I-setup ang user info sa UI ---- */
const currentUser = getCurrentUser();

if (currentUser && currentUser.role === 'admin') {
    document.body.classList.add('is-admin');
    console.log('✅ ADMIN CLASS APPLIED');
} else {
    document.body.classList.remove('is-admin');
}
// I-update ang sidebar user info
document.getElementById('userNameSidebar').textContent = currentUser.name || '—';
document.getElementById('userRoleSidebar').textContent =
    currentUser.role === 'admin' ? 'Administrator' : 'Barangay Health Worker';
document.getElementById('userAvatarSidebar').textContent =
    (currentUser.name || 'U').charAt(0).toUpperCase();

// I-update ang welcome message
document.getElementById('dashWelcome').textContent =
    `Welcome back, ${currentUser.name}! Here's your health system overview.`;

// I-show ang admin-only na items sa sidebar at UI
if (isAdmin()) {
    document.querySelectorAll('.admin-only').forEach(el => {
        el.style.display = '';
    });
}


/* ---- I-update ang datetime display ---- */
function updateDateTime() {
    const now = new Date();
    const options = {
        weekday: 'short',
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    };
    const dateChip = document.getElementById('datetimeChip');
    if (dateChip) {
        dateChip.textContent = now.toLocaleString('en-PH', options);
    }
}
updateDateTime();
setInterval(updateDateTime, 60000); // Update bawat minuto

/* ============================================================
   NAVIGATION - Page section switching
   ============================================================ */

const pageTitles = {
    'dashboard':       'Dashboard',
    'patients':        'Patient Records',
    'medical-records': 'Medical Records',
    'immunizations':   'Immunizations',
    'disease-cases':   'Disease Surveillance',
    'analytics':       'Disease Trend Analytics',
    'bhw-management':  'BHW Management',
    'reports':         'Reports & Export',
    'audit-logs':      'Audit Logs'
};

/**
 * Ipakita ang isang section at itago ang lahat ng iba pa.
 * Ginagamit ng sidebar navigation links.
 */
function showSection(sectionName) {
    // I-hide ang lahat ng sections
    document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));

    // I-show ang pinili
    const target = document.getElementById(`section-${sectionName}`);
    if (target) target.classList.add('active');

    // I-update ang active state ng sidebar
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === sectionName);
    });

    // I-update ang page title sa topbar
    const titleEl = document.getElementById('pageTitle');
    if (titleEl) titleEl.textContent = pageTitles[sectionName] || sectionName;

    // I-load ang data para sa napiling section
    switch(sectionName) {
        case 'dashboard':       loadDashboardStats(); break;
        case 'patients':        window.location.href = '/frontend/pages/patients.html'; break;
        case 'analytics':       loadAnalyticsCharts(); break;
        case 'disease-cases':   loadSurveillance();   break;
        case 'bhw-management':  loadBHWList();         break;
        case 'reports':         loadReportFilters();   break;
        case 'audit-logs':      loadAuditLogs();       break;
    }
}

/* ============================================================
   DISEASE SURVEILLANCE PANEL
   Pinapalitan ang "Record Case" button ng isang full
   surveillance view na nagpapakita ng auto-counted cases
   mula sa patient diagnosis entries.
   ============================================================ */

let survChartInst = null;

/**
 * I-load ang lahat ng surveillance data:
 * - Case counts per disease (table)
 * - Monthly trend mini-chart
 * - Recent auto-recorded entries log
 */
async function loadSurveillance() {
    const year      = parseInt(document.getElementById('surv-year')?.value    || new Date().getFullYear());
    const barangay  = document.getElementById('surv-barangay')?.value || '';

    // I-populate ang barangay filter kung admin
    if (isAdmin() && document.getElementById('surv-barangay')) {
        await loadBarangaysForSelect('surv-barangay');
    }

    await Promise.all([
        loadSurveillanceTable(year, barangay),
        loadSurveillanceTrend(year, barangay),
        loadRecentCases(year, barangay)
    ]);
}

/**
 * I-load ang disease case count table.
 * Nagpapakita ng total cases per disease para sa napiling year at barangay.
 */
async function loadSurveillanceTable(year, barangayId) {
    const tbody = document.getElementById('survTableBody');
    if (!tbody) return;

    try {
        let url = `/api/analytics/top-diseases?limit=15&year=${year}`;
        if (barangayId) url += `&barangay_id=${barangayId}`;

        const data = await apiGet(url);
        if (!data || !data.labels.length) {
            tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state">
                <div class="empty-icon">🦠</div>
                <h3>No disease cases recorded yet</h3>
                <p>Cases are auto-counted when medical records with a diagnosis are saved.</p>
            </div></td></tr>`;

            // I-update ang stat cards na empty
            updateSurvStats(0, 0, '—');
            return;
        }

        const total = data.data.reduce((s, v) => s + v, 0);
        const top   = data.labels[0];
        const topCount = data.data[0];

        updateSurvStats(total, data.labels.length, `${top} (${topCount})`);

        tbody.innerHTML = data.labels.map((disease, i) => {
            const count = data.data[i];
            const pct   = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
            const barW  = total > 0 ? Math.round((count / data.data[0]) * 100) : 0;
            return `
            <tr>
                <td style="color:var(--text-muted);font-size:12px;">${i + 1}</td>
                <td><strong>${escapeHtml(disease)}</strong></td>
                <td><span class="badge badge-active" style="font-size:10px;">Communicable</span></td>
                <td>
                    <div style="display:flex;align-items:center;gap:10px;">
                        <strong style="font-size:15px;color:var(--text);">${count}</strong>
                        <div style="flex:1;height:6px;background:var(--bg);border-radius:3px;max-width:80px;">
                            <div style="height:100%;width:${barW}%;background:var(--primary);border-radius:3px;"></div>
                        </div>
                        <span style="font-size:11px;color:var(--text-muted);">${pct}%</span>
                    </div>
                </td>
                <td>
                    <span style="font-size:11px;color:${i < 3 ? 'var(--danger)' : 'var(--text-muted)'};">
                        ${i === 0 ? 'Highest' : i < 3 ? 'High' : 'Moderate'}
                    </span>
                </td>
            </tr>`;
        }).join('');

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="5" style="padding:20px;color:var(--text-muted);text-align:center;">Error loading data.</td></tr>`;
    }
}

/**
 * I-update ang summary stat cards sa tuktok ng surveillance panel.
 */
function updateSurvStats(totalCases, diseaseCount, topDisease) {
    const grid = document.getElementById('survStatsGrid');
    if (!grid) return;
    grid.innerHTML = `
        <div class="stat-card blue">
            <div class="stat-icon">🦠</div>
            <div class="stat-value">${totalCases.toLocaleString()}</div>
            <div class="stat-label">Total Cases This Year</div>
        </div>
        <div class="stat-card red">
            <div class="stat-icon">📋</div>
            <div class="stat-value">${diseaseCount}</div>
            <div class="stat-label">Diseases Recorded</div>
        </div>
        <div class="stat-card orange" style="grid-column:span 2;">
            <div class="stat-icon">⚠️</div>
            <div class="stat-value" style="font-size:16px;">${escapeHtml(topDisease)}</div>
            <div class="stat-label">Leading Disease This Year</div>
        </div>
    `;
}

/**
 * I-load ang monthly trend mini-chart para sa surveillance panel.
 */
async function loadSurveillanceTrend(year, barangayId) {
    let url = `/api/analytics/disease-trends?year=${year}`;
    if (barangayId) url += `&barangay_id=${barangayId}`;

    const data = await apiGet(url);
    const ctx  = document.getElementById('survTrendChart');
    if (!ctx || !data) return;

    if (survChartInst) survChartInst.destroy();

    if (!data.datasets || !data.datasets.length) return;

    // Ipakita lang ang top 5 diseases para hindi masikip ang legend
    const top5 = data.datasets.slice(0, 5);

    survChartInst = new Chart(ctx, {
        type: 'line',
        data: { labels: data.labels, datasets: top5.map(ds => ({ ...ds, borderWidth: 2, pointRadius: 3 })) },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 }, padding: 8 } }
            },
            scales: {
                x: { grid: { display: false }, ticks: { font: { size: 9 } } },
                y: { beginAtZero: true, ticks: { font: { size: 9 }, stepSize: 1 } }
            }
        }
    });
}

/**
 * I-load ang pinaka-recent na auto-recorded disease cases.
 * Nagpapakita kung aling diagnosis entries ang nag-trigger ng auto-counting.
 */
async function loadRecentCases(year, barangayId) {
    const tbody = document.getElementById('survRecentBody');
    if (!tbody) return;

    try {
        // Gamitin ang disease-per-barangay data bilang proxy
        // (sa production, gumawa ng dedicated /api/disease-cases/recent endpoint)
        let url = `/api/analytics/disease-per-barangay?year=${year}`;
        if (barangayId) url += `&barangay_id=${barangayId}`;

        const data = await apiGet(url);
        if (!data || !data.labels.length) {
            tbody.innerHTML = `<tr><td colspan="5" style="padding:20px;color:var(--text-muted);text-align:center;">
                No cases recorded yet. Cases will appear here after saving medical records with a diagnosis.
            </td></tr>`;
            return;
        }

        // Ipakita ang per-barangay breakdown
        tbody.innerHTML = data.labels.map((barangay, i) => `
            <tr>
                <td style="font-size:12px;color:var(--text-muted);">${year}</td>
                <td><strong>Multiple Diagnoses</strong></td>
                <td>${escapeHtml(barangay)}</td>
                <td><strong>${data.data[i]}</strong></td>
                <td style="font-size:11px;color:var(--text-muted);">Auto-recorded</td>
            </tr>
        `).join('');

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="5" style="padding:16px;color:var(--text-muted);text-align:center;">Error loading recent cases.</td></tr>`;
    }
}

/* ============================================================
   DASHBOARD STATS LOADING
   ============================================================ */

// Chart instances - i-store para ma-destroy bago gumawa ng bago
let trendChartInst     = null;
let topDiseasesInst    = null;
let barangayChartInst  = null;
let ageChartInst       = null;

/**
 * I-load ang lahat ng dashboard statistics at charts.
 * Tinatawag sa startup at pag-balik sa dashboard.
 */
async function loadDashboardStats() {
    try {
        // Kunin ang summary stats mula sa analytics endpoint
        const stats = await apiGet('/api/analytics/dashboard-summary');
        if (!stats) return;

        // I-update ang stat cards
        animateCount('statPatients',       stats.total_patients);
        animateCount('statRecords',        stats.total_medical_records);
        animateCount('statImmunizations',  stats.total_immunizations);
        animateCount('statCases',          stats.cases_this_month);

        // I-update ang month label
        const monthLabel = document.getElementById('dashMonthLabel');
        if (monthLabel) monthLabel.textContent = `📅 ${stats.current_month}`;

        // Kung Admin, i-load din ang BHW stats
        if (isAdmin()) {
            const userStats = await apiGet('/api/users/stats/summary');
            if (userStats) {
                animateCount('statBHW', userStats.active_bhw);
            }
        }

        // I-load ang mga charts
        await loadTrendChart();
        await loadTopDiseasesChart();
        await loadBarangayChart();
        await loadAgeChart();

    } catch (error) {
        console.error('Error loading dashboard stats:', error);
        showToast('Error loading dashboard data.', 'error');
    }
}

/**
 * Number counter animation para sa stat cards.
 * Nagbibigay ng animated na pagbabago ng numero.
 */
function animateCount(elementId, targetValue) {
    const el = document.getElementById(elementId);
    if (!el) return;

    const start = 0;
    const duration = 800;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // Easing function para sa mas natural na animation
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(eased * targetValue).toLocaleString();
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

/* ============================================================
   CHART LOADING FUNCTIONS
   ============================================================ */

/**
 * I-load ang monthly disease trend line chart.
 * Ginagamit ang Chart.js para sa visualization.
 */
async function loadTrendChart() {
    const year = parseInt(document.getElementById('trendYearFilter')?.value || new Date().getFullYear());
    const data = await apiGet(`/api/analytics/disease-trends?year=${year}`);
    if (!data) return;

    const ctx = document.getElementById('trendChart');
    if (!ctx) return;

    // I-destroy ang lumang chart bago gumawa ng bago
    if (trendChartInst) trendChartInst.destroy();

    trendChartInst = new Chart(ctx, {
        type: 'line',
        data: {
            labels:   data.labels,
            datasets: data.datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, font: { size: 11 }, padding: 10 }
                },
                tooltip: {
                    backgroundColor: 'rgba(10,30,50,0.9)',
                    titleFont: { size: 12 },
                    bodyFont:  { size: 11 }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 10 } }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: { font: { size: 10 }, stepSize: 1 }
                }
            }
        }
    });
}

/**
 * I-load ang top diseases doughnut chart.
 */
async function loadTopDiseasesChart() {
    const data = await apiGet('/api/analytics/top-diseases?limit=6');
    if (!data || !data.labels.length) return;

    const ctx = document.getElementById('topDiseasesChart');
    if (!ctx) return;

    if (topDiseasesInst) topDiseasesInst.destroy();

    topDiseasesInst = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels:   data.labels,
            datasets: [{
                data:            data.data,
                backgroundColor: data.backgroundColor,
                borderWidth:     2,
                borderColor:     '#fff',
                hoverOffset:     6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '62%',
            plugins: {
                legend: {
                    position: 'right',
                    labels: { boxWidth: 12, font: { size: 11 }, padding: 8 }
                }
            }
        }
    });
}

/**
 * I-load ang cases per barangay bar chart.
 */
async function loadBarangayChart() {
    const year = new Date().getFullYear();
    const data = await apiGet(`/api/analytics/disease-per-barangay?year=${year}`);
    if (!data || !data.labels.length) return;

    const ctx = document.getElementById('barangayChart');
    if (!ctx) return;

    if (barangayChartInst) barangayChartInst.destroy();

    barangayChartInst = new Chart(ctx, {
        type: 'bar',
        data: {
            labels:   data.labels,
            datasets: [{
                label:           'Total Cases',
                data:            data.data,
                backgroundColor: data.backgroundColor,
                borderRadius:    6,
                borderSkipped:   false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { backgroundColor: 'rgba(10,30,50,0.9)' }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 10 } }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: { font: { size: 10 } }
                }
            }
        }
    });
}

/**
 * I-load ang age distribution chart.
 */
async function loadAgeChart() {
    const data = await apiGet('/api/analytics/age-distribution');
    if (!data || !data.labels.length) return;

    const ctx = document.getElementById('ageChart');
    if (!ctx) return;

    if (ageChartInst) ageChartInst.destroy();

    ageChartInst = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Male',
                    data: data.male,
                    backgroundColor: '#0a4f7680',
                    borderColor: '#0a4f76',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: 'Female',
                    data: data.female,
                    backgroundColor: '#8e44ad80',
                    borderColor: '#8e44ad',
                    borderWidth: 1,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, font: { size: 11 } }
                }
            },
            scales: {
                x: { grid: { display: false }, ticks: { font: { size: 10 } } },
                y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } }
            }
        }
    });
}

/* ============================================================
   BHW MANAGEMENT
   ============================================================ */

/**
 * I-load ang listahan ng lahat ng BHW accounts.
 */
async function loadBHWList() {
    if (!isAdmin()) return;

    try {
        const [users, stats] = await Promise.all([
            apiGet('/api/users/?role=bhw'),
            apiGet('/api/users/stats/summary')
        ]);

        // I-update ang BHW stat cards
        if (stats) {
            animateCount('bhwTotal',    stats.total_bhw);
            animateCount('bhwActive',   stats.active_bhw);
            animateCount('bhwInactive', stats.inactive_bhw);
            animateCount('bhwLocked',   stats.locked_accounts);
        }

        // I-update ang BHW table
        const tbody = document.getElementById('bhwTableBody');
        if (!tbody || !users) return;

        if (users.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8">
                <div class="empty-state">
                    <div class="empty-icon">👤</div>
                    <h3>No BHW accounts found</h3>
                    <p>Click "Register New BHW" to add the first account.</p>
                </div>
            </td></tr>`;
            return;
        }

        tbody.innerHTML = users.map((user, idx) => `
            <tr>
                <td>${idx + 1}</td>
                <td><strong>${escapeHtml(user.name)}</strong></td>
                <td style="color:var(--text-muted);font-size:12.5px;">${escapeHtml(user.email)}</td>
                <td>${escapeHtml(user.barangay_name || '—')}</td>
                <td>${escapeHtml(user.position || '—')}</td>
                <td>
                    <span class="badge badge-${user.status}">
                        ${user.status === 'active' ? '✅' : user.status === 'locked' ? '🔒' : '⏸️'}
                        ${user.status.charAt(0).toUpperCase() + user.status.slice(1)}
                    </span>
                </td>
                <td style="font-size:12px;color:var(--text-muted);">${formatDateTime(user.last_login)}</td>
                <td>
                    <div style="display:flex;gap:6px;">
                        ${user.status === 'active'
                            ? `<button class="btn btn-outline btn-sm" onclick="toggleUserStatus(${user.user_id}, 'inactive')" title="Deactivate">⏸️</button>`
                            : `<button class="btn btn-success btn-sm" onclick="toggleUserStatus(${user.user_id}, 'active')" title="Activate">▶️</button>`
                        }
                        ${user.status === 'locked'
                            ? `<button class="btn btn-primary btn-sm" onclick="toggleUserStatus(${user.user_id}, 'active')" title="Unlock">🔓</button>`
                            : ''
                        }
                    </div>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        showToast('Error loading BHW list: ' + error.message, 'error');
    }
}

/**
 * I-toggle ang status ng isang user (active/inactive).
 */
async function toggleUserStatus(userId, newStatus) {
    const confirmed = await confirmAction(
        `Are you sure you want to ${newStatus === 'active' ? 'activate' : 'deactivate'} this account?`
    );
    if (!confirmed) return;

    try {
        const result = await apiPut(`/api/users/${userId}`, { status: newStatus });
        if (result) {
            showToast(`User account ${newStatus === 'active' ? 'activated' : 'deactivated'} successfully.`, 'success');
            loadBHWList(); // I-reload ang list
        }
    } catch (error) {
        showToast('Error updating user status: ' + error.message, 'error');
    }
}

/* ============================================================
   OTP FLOW PARA SA BHW REGISTRATION
   ============================================================ */

/**
 * Humiling ng OTP mula sa server para sa BHW registration.
 */
async function requestOTP() {
    try {
        const result = await apiPost('/api/auth/request-otp', {});
        if (result) {
            showToast(result.message || 'OTP sent to your email.', 'success');
            closeModal('otpRequestModal');
            // Sa development, ipakita ang OTP kung nandoon ito
            if (result.otp_for_development) {
                showToast(`DEV MODE - OTP: ${result.otp_for_development}`, 'warning', 15000);
            }
            openModal('otpVerifyModal');
            setTimeout(() => document.getElementById('otp1')?.focus(), 200);
        }
    } catch (error) {
        showToast('Error requesting OTP: ' + error.message, 'error');
    }
}

/**
 * I-verify ang OTP na ini-input ng Admin.
 * Pagkatapos ma-verify, bubuksan ang BHW registration modal.
 */
async function verifyOTP() {
    // Kolektahin ang mga digit mula sa OTP input fields
    const otpCode = ['otp1','otp2','otp3','otp4','otp5','otp6']
        .map(id => document.getElementById(id)?.value || '')
        .join('');

    if (otpCode.length !== 6) {
        document.getElementById('otpError').style.display = 'block';
        document.getElementById('otpError').textContent = '⚠️ Please enter all 6 digits.';
        return;
    }

    try {
        const result = await apiPost('/api/auth/verify-otp', {
            otp_code: otpCode,
            purpose:  'registration'
        });

        if (result && result.verified) {
            showToast('OTP verified! You may now register a new BHW.', 'success');
            closeModal('otpVerifyModal');
            // I-clear ang OTP fields
            ['otp1','otp2','otp3','otp4','otp5','otp6'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            document.getElementById('otpError').style.display = 'none';

            // I-load ang barangays para sa registration form
            await loadBarangaysForSelect('bhwBarangay');
            openModal('registerBHWModal');
        }
    } catch (error) {
        document.getElementById('otpError').style.display = 'block';
        document.getElementById('otpError').textContent = '⚠️ ' + (error.message || 'Invalid OTP.');
    }
}

// OTP digit auto-advance (kapag nag-type sa isang digit, lumalipat sa susunod)
document.addEventListener('DOMContentLoaded', function() {
    ['otp1','otp2','otp3','otp4','otp5','otp6'].forEach((id, idx, arr) => {
        const el = document.getElementById(id);
        if (!el) return;

        el.addEventListener('input', function() {
            // Siguraduhing numero lamang
            this.value = this.value.replace(/[^0-9]/g, '');
            if (this.value && idx < arr.length - 1) {
                document.getElementById(arr[idx + 1])?.focus();
            }
        });

        el.addEventListener('keydown', function(e) {
            // Backspace: lumipat sa nakaraan
            if (e.key === 'Backspace' && !this.value && idx > 0) {
                document.getElementById(arr[idx - 1])?.focus();
            }
        });
    });
});

/**
 * I-submit ang BHW registration form.
 */
async function submitRegisterBHW() {
    const name     = document.getElementById('bhwName')?.value.trim();
    const email    = document.getElementById('bhwEmail')?.value.trim();
    const barangay = document.getElementById('bhwBarangay')?.value;
    const position = document.getElementById('bhwPosition')?.value.trim();
    const password = document.getElementById('bhwPassword')?.value;
    const confirm  = document.getElementById('bhwConfirmPassword')?.value;

    // Validation
    if (!name || !email || !barangay || !password) {
        showToast('Please fill in all required fields.', 'warning');
        return;
    }
    if (!isValidEmail(email)) {
        showToast('Please enter a valid email address.', 'warning');
        return;
    }
    if (password !== confirm) {
        showToast('Passwords do not match.', 'warning');
        return;
    }
    if (password.length < 8) {
        showToast('Password must be at least 8 characters.', 'warning');
        return;
    }

    try {
        const result = await apiPost('/api/users/register', {
            name:        name,
            email:       email,
            barangay_id: parseInt(barangay),
            position:    position || null,
            password:    password,
            role:        'bhw'
        });

        if (result) {
            showToast(`BHW account for ${result.name} created successfully!`, 'success');
            closeModal('registerBHWModal');
            loadBHWList();
        }
    } catch (error) {
        showToast('Error registering BHW: ' + error.message, 'error');
    }
}

/* ============================================================
   REPORTS
   ============================================================ */

/**
 * I-load ang barangay options sa report filter dropdowns.
 */
async function loadReportFilters() {
    const selectIds = ['reportPatientBarangay', 'reportImmunBarangay'];
    for (const id of selectIds) {
        await loadBarangaysForSelect(id);
    }
}

/**
 * Mag-generate at mag-download ng PDF report.
 */
async function generateReport(type) {
    let url = '';
    let filename = '';

    switch(type) {
        case 'patients': {
            const bid = document.getElementById('reportPatientBarangay')?.value;
            url = `/api/reports/patients${bid ? `?barangay_id=${bid}` : ''}`;
            filename = `patient_report_${new Date().toISOString().slice(0,10)}.pdf`;
            break;
        }
        case 'disease-trends': {
            const year = document.getElementById('reportDiseaseYear')?.value;
            url = `/api/reports/disease-trends?year=${year}`;
            filename = `disease_trend_${year}.pdf`;
            break;
        }
        case 'immunization': {
            const bid = document.getElementById('reportImmunBarangay')?.value;
            url = `/api/reports/immunization${bid ? `?barangay_id=${bid}` : ''}`;
            filename = `immunization_report_${new Date().toISOString().slice(0,10)}.pdf`;
            break;
        }
    }

    if (!url) return;
    showToast('Generating report, please wait...', 'info');
    await downloadPDF(url, filename);
}

/* ============================================================
   AUDIT LOGS
   ============================================================ */

/**
 * I-load ang listahan ng audit logs.
 */
async function loadAuditLogs() {
    if (!isAdmin()) return;

    try {
        const logs = await apiGet('/api/audit-logs/?limit=100');
        const tbody = document.getElementById('auditTableBody');
        if (!tbody || !logs) return;

        if (logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6">
                <div class="empty-state"><div class="empty-icon">🔍</div><h3>No audit logs found.</h3></div>
            </td></tr>`;
            return;
        }

        // Kung BHW, ipakita ang babala na barangay-filtered ang logs
        const isBHW = !isAdmin();
        const filterNote = isBHW
            ? `<div style="padding:10px 14px;font-size:12px;color:var(--text-muted);
                           background:var(--primary-pale);border-bottom:1px solid var(--border);">
                Showing login/logout activity for your barangay only.
               </div>`
            : '';

        const actionBadge = (action) => {
            if (action.startsWith('LOGIN'))  return `<span class="badge badge-active">${escapeHtml(action)}</span>`;
            if (action === 'LOGOUT')         return `<span class="badge badge-inactive">LOGOUT</span>`;
            return `<span style="font-size:12px;">${escapeHtml(action)}</span>`;
        };

        const tableEl = document.getElementById('auditTableBody');
        tableEl.closest('.card-body').insertAdjacentHTML('afterbegin', filterNote);

        tbody.innerHTML = logs.map((log, idx) => `
            <tr>
                <td style="color:var(--text-muted);font-size:12px;">${idx + 1}</td>
                <td><strong>${escapeHtml(log.user_name || 'System')}</strong></td>
                <td>
                    <span class="badge ${log.user_role === 'admin' ? 'badge-admin' : 'badge-bhw'}"
                          style="font-size:10px;">
                        ${escapeHtml((log.user_role || '—').toUpperCase())}
                    </span>
                </td>
                <td style="font-size:12.5px;">${escapeHtml(log.barangay_name || '—')}</td>
                <td>${actionBadge(log.action)}</td>
                <td style="font-family:monospace;font-size:12px;color:var(--text-muted);">
                    ${escapeHtml(log.ip_address || '—')}
                </td>
                <td style="font-size:12px;color:var(--text-muted);">${formatDateTime(log.date_time)}</td>
            </tr>
        `).join('');

    } catch (error) {
        showToast('Error loading audit logs: ' + error.message, 'error');
    }
}

/* ============================================================
   LOGOUT
   ============================================================ */

/**
 * I-handle ang logout ng user.
 * Tinatawag ang backend logout endpoint at kina-clear ang session.
 */
async function handleLogout() {
    const confirmed = await confirmAction('Are you sure you want to sign out?');
    if (!confirmed) return;

    try {
        // I-call ang backend logout para ma-log ang logout event
        await apiPost('/api/auth/logout', {});
    } catch (_) {
        // Kahit may error, i-clear pa rin ang session
    } finally {
        sessionStorage.clear();
        window.location.href = '/';
    }
}

/* ============================================================
   HELPER: I-load ang barangays para sa select dropdown
   ============================================================ */

async function loadBarangaysForSelect(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;

    try {
        const barangays = await apiGet('/api/disease-cases/barangays');
        if (!barangays) return;

        // I-keep ang unang option (All Barangays)
        const firstOption = select.options[0];
        select.innerHTML = '';
        select.appendChild(firstOption);

        barangays.forEach(b => {
            const option = document.createElement('option');
            option.value = b.barangay_id;
            option.textContent = b.barangay_name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading barangays:', error);
    }
}

/* ---- I-initialize ang dashboard sa page load ---- */
document.addEventListener('DOMContentLoaded', async function() {
    // I-populate ang barangay filters
    await loadBarangaysForSelect('filterBarangay');
    await loadBarangaysForSelect('analyticsBarangay');

    // I-load ang initial dashboard data
    await loadDashboardStats();
});