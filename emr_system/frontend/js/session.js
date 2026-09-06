/* ============================================================
   session.js - Session Timeout & Screen Lock Management
   Awtomatikong naglo-lock ang screen pagkatapos ng inactivity.
   Kailangan ng user na mag-re-enter ng password para i-unlock.
   ============================================================ */

// ---- Session configuration ----
const SESSION_TIMEOUT_MS   = 30 * 60 * 1000;  // 30 minuto ng inactivity
const WARNING_BEFORE_MS    = 2  * 60 * 1000;  // Magbabala 2 minuto bago mag-lock
const TIMER_CHECK_INTERVAL = 30 * 1000;        // Suriin bawat 30 segundo

let sessionTimer      = null;  // Main timeout timer
let warningTimer      = null;  // Warning countdown timer
let sessionLockActive = false; // True kung naka-lock na ang screen
let warningShown      = false; // True kung naka-show na ang babala

/**
 * I-reset ang session timer kapag may aktibidad ang user.
 * Tinatawag ng lahat ng user activity events.
 */
function resetSessionTimer() {
    // Huwag i-reset kung naka-lock na ang screen
    if (sessionLockActive) return;

    // I-save ang last activity timestamp
    sessionStorage.setItem('last_activity', String(Date.now()));

    // I-clear ang mga existing timers
    clearTimeout(sessionTimer);
    clearTimeout(warningTimer);
    warningShown = false;

    // Itago ang warning kung naka-show na ito
    hideSessionWarning();

    // Itakda ang bagong warning timer (mag-babala bago mag-lock)
    warningTimer = setTimeout(showSessionWarning, SESSION_TIMEOUT_MS - WARNING_BEFORE_MS);

    // Itakda ang bagong lock timer
    sessionTimer = setTimeout(lockScreen, SESSION_TIMEOUT_MS);
}

/**
 * Magpakita ng warning notification bago mag-lock ang screen.
 * Bibigyan ng chance ang user na i-extend ang kanilang session.
 */
function showSessionWarning() {
    if (sessionLockActive || warningShown) return;
    warningShown = true;

    // Gumawa ng warning toast na may countdown
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const warningToast = document.createElement('div');
    warningToast.id        = 'sessionWarningToast';
    warningToast.className = 'toast warning';
    warningToast.style.cssText = 'min-width:320px; cursor:pointer;';
    warningToast.innerHTML = `
        <span style="font-size:20px;">⏰</span>
        <div style="flex:1;">
            <div style="font-weight:600;margin-bottom:3px;">Session Expiring Soon</div>
            <div style="font-size:12px;color:var(--text-muted);" id="warningCountdown">
                Screen will lock in 2:00
            </div>
        </div>
        <button onclick="extendSession()" style="background:var(--accent);color:#fff;border:none;
            border-radius:7px;padding:6px 12px;font-size:12px;cursor:pointer;font-weight:600;">
            Stay Active
        </button>
    `;

    container.appendChild(warningToast);

    // Countdown para sa warning
    let secondsLeft = WARNING_BEFORE_MS / 1000;
    const countdownEl = document.getElementById('warningCountdown');
    const countdownInterval = setInterval(() => {
        secondsLeft--;
        if (countdownEl) {
            const mins = Math.floor(secondsLeft / 60);
            const secs = secondsLeft % 60;
            countdownEl.textContent = `Screen will lock in ${mins}:${String(secs).padStart(2,'0')}`;
        }
        if (secondsLeft <= 0) clearInterval(countdownInterval);
    }, 1000);
}

/**
 * Itago ang session warning toast.
 */
function hideSessionWarning() {
    const toast = document.getElementById('sessionWarningToast');
    if (toast) toast.remove();
}

/**
 * I-extend ang session — tinatawag kapag nag-click ang user sa "Stay Active".
 */
function extendSession() {
    hideSessionWarning();
    resetSessionTimer();
    showToast('Session extended. You\'re still logged in.', 'success', 2000);
}

/**
 * I-lock ang screen dahil sa inactivity.
 * Nagpapakita ng lock overlay na nag-re-require ng password.
 */
function lockScreen() {
    // Huwag i-lock kung walang session
    if (!sessionStorage.getItem('access_token')) return;

    sessionLockActive = true;
    hideSessionWarning();

    // I-clear ang mga timers
    clearTimeout(sessionTimer);
    clearTimeout(warningTimer);

    // Ipakita ang lock overlay
    const lockOverlay = document.getElementById('sessionLock');
    if (lockOverlay) {
        lockOverlay.classList.add('show');
        // I-focus ang password field pagkatapos ng animation
        setTimeout(() => {
            const pwField = document.getElementById('unlockPassword');
            if (pwField) {
                pwField.value = '';
                pwField.focus();
            }
        }, 200);
    }

    // I-log sa console para sa debugging
    console.log('🔒 Screen locked due to inactivity at', new Date().toLocaleTimeString());
}

/**
 * I-unlock ang screen pagkatapos ma-verify ang password.
 * Tinatawag ng Unlock button sa lock overlay.
 */
async function unlockSession() {
    const pwField = document.getElementById('unlockPassword');
    const errorEl = document.getElementById('unlockError');

    if (!pwField || !pwField.value) {
        if (errorEl) {
            errorEl.textContent = '⚠️ Please enter your password.';
            errorEl.style.display = 'block';
        }
        return;
    }

    // Kunin ang email ng kasalukuyang user
    const userEmail = sessionStorage.getItem('user_email');
    if (!userEmail) {
        // Walang email, i-redirect sa login
        sessionStorage.clear();
        window.location.href = '/';
        return;
    }

    try {
        // I-verify ang password sa backend
        const response = await fetch(`${window.location.origin}/api/auth/login`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                email:    userEmail,
                password: pwField.value
            })
        });

        if (response.ok) {
            const data = await response.json();

            // I-update ang token sa sessionStorage
            sessionStorage.setItem('access_token',  data.access_token);
            sessionStorage.setItem('token_expires',  String(Date.now() + data.expires_in * 1000));

            // Itago ang lock overlay
            const lockOverlay = document.getElementById('sessionLock');
            if (lockOverlay) lockOverlay.classList.remove('show');

            // I-reset ang mga estado
            sessionLockActive = false;
            warningShown      = false;
            if (errorEl) errorEl.style.display = 'none';
            if (pwField)  pwField.value         = '';

            // I-restart ang session timer
            resetSessionTimer();

            showToast('Session unlocked. Welcome back!', 'success', 2000);
        } else {
            // Mali ang password
            const data = await response.json();
            if (errorEl) {
                errorEl.textContent = '⚠️ ' + (data.detail || 'Incorrect password. Please try again.');
                errorEl.style.display = 'block';
            }
            if (pwField) {
                pwField.value = '';
                pwField.focus();
            }

            // Shake animation para sa feedback
            const lockCard = document.querySelector('.lock-card');
            if (lockCard) {
                lockCard.style.animation = 'none';
                lockCard.offsetHeight;
                lockCard.style.animation = 'lockShake 0.4s ease';
            }
        }
    } catch (error) {
        if (errorEl) {
            errorEl.textContent = '⚠️ Cannot connect to server. Please try again.';
            errorEl.style.display = 'block';
        }
    }
}

/**
 * Mag-logout at i-redirect sa login page.
 * Tinatawag ng "Sign in as different user" link sa lock overlay.
 */
function logoutFromLock() {
    sessionStorage.clear();
    clearTimeout(sessionTimer);
    clearTimeout(warningTimer);
    window.location.href = '/';
}

/* ============================================================
   USER ACTIVITY MONITORING
   I-track ang lahat ng user interactions para i-reset ang timer
   ============================================================ */

// Listahan ng events na nagpapakita ng user activity
const ACTIVITY_EVENTS = [
    'mousemove', 'mousedown', 'keydown',
    'touchstart', 'touchmove', 'scroll', 'click'
];

// I-attach ang event listeners para sa activity monitoring
ACTIVITY_EVENTS.forEach(eventName => {
    document.addEventListener(eventName, () => {
        // Huwag i-reset kung naka-lock na
        if (!sessionLockActive && sessionStorage.getItem('access_token')) {
            // Throttle ang reset — huwag mag-reset kung bago lang na-reset
            const lastReset = parseInt(sessionStorage.getItem('last_timer_reset') || '0');
            if (Date.now() - lastReset > 10000) { // Reset lang bawat 10 segundo minimum
                sessionStorage.setItem('last_timer_reset', String(Date.now()));
                resetSessionTimer();
            }
        }
    }, { passive: true });
});

/* ============================================================
   VISIBILITY CHANGE HANDLING
   Mag-check ng session status kapag nag-balik ang user sa tab
   ============================================================ */

document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') {
        // Kapag nag-balik ang user sa tab, suriin kung expired na ang token
        const tokenExpires = parseInt(sessionStorage.getItem('token_expires') || '0');
        if (!sessionStorage.getItem('access_token') || Date.now() > tokenExpires) {
            // Expired na ang token, i-redirect sa login
            sessionStorage.clear();
            window.location.href = '/';
            return;
        }

        // Suriin kung kailangan na mag-lock dahil sa inactivity
        const lastActivity = parseInt(sessionStorage.getItem('last_activity') || '0');
        const timeSinceActivity = Date.now() - lastActivity;

        if (lastActivity > 0 && timeSinceActivity > SESSION_TIMEOUT_MS) {
            // Matagal nang idle, i-lock agad ang screen
            lockScreen();
        } else {
            // I-reset ang timer
            resetSessionTimer();
        }
    }
});

/* ============================================================
   TOKEN EXPIRY CHECKER
   Periodically sinusuri kung valid pa ang token
   ============================================================ */

setInterval(() => {
    if (sessionLockActive) return;

    const tokenExpires = parseInt(sessionStorage.getItem('token_expires') || '0');
    if (sessionStorage.getItem('access_token') && Date.now() > tokenExpires) {
        // Expired na ang token
        sessionStorage.clear();
        showToast('Your session has expired. Please login again.', 'warning');
        setTimeout(() => window.location.href = '/', 2000);
    }
}, TIMER_CHECK_INTERVAL);

/* ============================================================
   INITIALIZATION
   I-start ang session management sa page load
   ============================================================ */

// I-save ang email ng user para sa unlock verification
const currentUserForSession = getCurrentUser();
if (currentUserForSession && currentUserForSession.email) {
    sessionStorage.setItem('user_email', currentUserForSession.email);
} else {
    // Kunin ang email mula sa API kung wala pa
    apiGet('/api/auth/me').then(user => {
        if (user) sessionStorage.setItem('user_email', user.email);
    }).catch(() => {});
}

// I-start ang session timer
resetSessionTimer();

// CSS animation para sa lock card shake effect
const lockShakeStyle = document.createElement('style');
lockShakeStyle.textContent = `
@keyframes lockShake {
    0%,100% { transform: translateX(0); }
    20%     { transform: translateX(-8px); }
    40%     { transform: translateX(8px); }
    60%     { transform: translateX(-5px); }
    80%     { transform: translateX(5px); }
}`;
document.head.appendChild(lockShakeStyle);

// Enter key sa unlock password field
document.addEventListener('DOMContentLoaded', function() {
    const unlockPwField = document.getElementById('unlockPassword');
    if (unlockPwField) {
        unlockPwField.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') unlockSession();
        });
    }
});