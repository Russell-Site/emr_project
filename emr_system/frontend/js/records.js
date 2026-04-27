/* ============================================================
   records.js - Medical Records, Immunizations, Disease Cases
   I-add mo ito bilang bagong JS file o i-append sa dashboard.js
   ============================================================ */

/* ============================================================
   PATIENT DROPDOWN LOADER
   Para sa lahat ng modals na kailangan ng patient select
   ============================================================ */

/**
 * I-load ang mga pasyente sa isang select dropdown.
 * Tinatawag bago buksan ang mga modals na may patient field.
 */
async function loadPatientsForSelect(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;

    try {
        const patients = await apiGet('/api/patients/?limit=100');
        if (!patients) return;

        // I-keep ang unang option
        const firstOption = select.options[0];
        select.innerHTML = '';
        select.appendChild(firstOption);

        patients.forEach(p => {
            const option    = document.createElement('option');
            option.value    = p.patient_id;
            option.textContent = `${p.last_name}, ${p.first_name} — ${p.barangay_name || ''}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading patients for select:', error);
    }
}

/* ============================================================
   MEDICAL RECORDS
   ============================================================ */

/**
 * Override ng Add Record button — i-load muna ang patients
 * bago buksan ang modal.
 */
async function openAddRecordModal() {
    // I-set ang default na date ngayon
    const today = new Date().toISOString().split('T')[0];
    const dateField = document.getElementById('recVisitDate');
    if (dateField) dateField.value = today;

    // I-load ang patients sa dropdown
    await loadPatientsForSelect('recPatientId');
    openModal('addRecordModal');
}

/**
 * I-submit ang Add Medical Record form.
 */
async function submitAddRecord() {
    const patientId     = document.getElementById('recPatientId')?.value;
    const visitDate     = document.getElementById('recVisitDate')?.value;
    const chiefComplaint = document.getElementById('recChiefComplaint')?.value.trim();
    const symptoms      = document.getElementById('recSymptoms')?.value.trim();
    const diagnosis     = document.getElementById('recDiagnosis')?.value.trim();
    const treatment     = document.getElementById('recTreatment')?.value.trim();
    const bp            = document.getElementById('recBP')?.value.trim();
    const temp          = document.getElementById('recTemp')?.value;
    const weight        = document.getElementById('recWeight')?.value;
    const notes         = document.getElementById('recNotes')?.value.trim();

    // Validation
    if (!patientId || !visitDate) {
        showToast('Pumili ng patient at lagyan ng visit date.', 'warning');
        return;
    }

    try {
        const payload = {
            patient_id:      parseInt(patientId),
            visit_date:      visitDate,
            chief_complaint: chiefComplaint || null,
            symptoms:        symptoms       || null,
            diagnosis:       diagnosis      || null,
            treatment:       treatment      || null,
            blood_pressure:  bp             || null,
            temperature:     temp           ? parseFloat(temp)   : null,
            weight_kg:       weight         ? parseFloat(weight) : null,
            notes:           notes          || null
        };

        const result = await apiPost('/api/medical-records/', payload);
        if (result) {
            showToast('Medical record saved successfully!', 'success');
            closeModal('addRecordModal');
            // I-clear ang form
            document.getElementById('addRecordModal').querySelectorAll('input, textarea, select').forEach(el => {
                if (el.tagName === 'SELECT') el.selectedIndex = 0;
                else el.value = '';
            });
        }
    } catch (error) {
        showToast('Error saving record: ' + error.message, 'error');
    }
}

/* ============================================================
   IMMUNIZATIONS
   ============================================================ */

/**
 * Buksan ang Add Immunization modal na may patients loaded.
 */
async function openAddImmunModal() {
    const today = new Date().toISOString().split('T')[0];
    const dateField = document.getElementById('immunDateGiven');
    if (dateField) dateField.value = today;

    await loadPatientsForSelect('immunPatientId');
    openModal('addImmunModal');
}

/**
 * I-submit ang Add Immunization form.
 */
async function submitAddImmun() {
    const patientId   = document.getElementById('immunPatientId')?.value;
    const vaccineName = document.getElementById('immunVaccineName')?.value.trim();
    const dateGiven   = document.getElementById('immunDateGiven')?.value;
    const dose        = document.getElementById('immunDose')?.value;
    const nextSched   = document.getElementById('immunNextSched')?.value;
    const adminBy     = document.getElementById('immunAdminBy')?.value.trim();
    const batch       = document.getElementById('immunBatch')?.value.trim();
    const remarks     = document.getElementById('immunRemarks')?.value.trim();

    // Validation
    if (!patientId || !vaccineName || !dateGiven) {
        showToast('Pumili ng patient, vaccine name, at date given.', 'warning');
        return;
    }

    try {
        const payload = {
            patient_id:      parseInt(patientId),
            vaccine_name:    vaccineName,
            date_given:      dateGiven,
            dose_number:     dose        ? parseInt(dose) : 1,
            next_schedule:   nextSched   || null,
            administered_by: adminBy     || null,
            batch_number:    batch       || null,
            remarks:         remarks     || null
        };

        const result = await apiPost('/api/immunizations/', payload);
        if (result) {
            showToast('Immunization record saved successfully!', 'success');
            closeModal('addImmunModal');
            document.getElementById('addImmunModal').querySelectorAll('input, textarea, select').forEach(el => {
                if (el.tagName === 'SELECT') el.selectedIndex = 0;
                else el.value = '';
            });
        }
    } catch (error) {
        showToast('Error saving immunization: ' + error.message, 'error');
    }
}

/* ============================================================
   DISEASE CASES
   ============================================================ */

/**
 * Buksan ang Add Disease Case modal na may diseases at barangays loaded.
 */
async function openAddCaseModal() {
    const today = new Date().toISOString().split('T')[0];
    const dateField = document.getElementById('caseDate');
    if (dateField) dateField.value = today;

    // I-load ang diseases, barangays, at patients sabay-sabay
    await Promise.all([
        loadDiseasesForSelect('caseDisease'),
        loadBarangaysForSelect('caseBarangay'),
        loadPatientsForSelect('casePatient')
    ]);

    // Kung BHW, i-set at i-disable ang barangay
    if (!isAdmin()) {
        const barangaySelect = document.getElementById('caseBarangay');
        if (barangaySelect) {
            barangaySelect.value    = sessionStorage.getItem('barangay_id') || '';
            barangaySelect.disabled = true;
        }
    }

    openModal('addCaseModal');
}

/**
 * I-load ang diseases sa select dropdown.
 */
async function loadDiseasesForSelect(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;

    try {
        const diseases = await apiGet('/api/disease-cases/diseases');
        if (!diseases) return;

        const firstOption = select.options[0];
        select.innerHTML = '';
        select.appendChild(firstOption);

        diseases.forEach(d => {
            const option       = document.createElement('option');
            option.value       = d.disease_id;
            option.textContent = d.disease_name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading diseases:', error);
    }
}

/**
 * I-submit ang Add Disease Case form.
 */
async function submitAddCase() {
    const diseaseId  = document.getElementById('caseDisease')?.value;
    const barangayId = document.getElementById('caseBarangay')?.value;
    const caseDate   = document.getElementById('caseDate')?.value;
    const caseCount  = document.getElementById('caseCaseCount')?.value;
    const ageGroup   = document.getElementById('caseAgeGroup')?.value;
    const sex        = document.getElementById('caseSex')?.value;
    const patientId  = document.getElementById('casePatient')?.value;
    const remarks    = document.getElementById('caseRemarks')?.value.trim();

    // Validation
    if (!diseaseId || !barangayId || !caseDate || !caseCount) {
        showToast('Pumili ng disease, barangay, date, at number of cases.', 'warning');
        return;
    }

    try {
        const payload = {
            disease_id:      parseInt(diseaseId),
            barangay_id:     parseInt(barangayId),
            patient_id:      patientId  ? parseInt(patientId) : null,
            date_recorded:   caseDate,
            number_of_cases: parseInt(caseCount),
            age_group:       ageGroup   || null,
            sex:             sex        || null,
            remarks:         remarks    || null
        };

        const result = await apiPost('/api/disease-cases/', payload);
        if (result) {
            showToast('Disease case recorded successfully!', 'success');
            closeModal('addCaseModal');
            document.getElementById('addCaseModal').querySelectorAll('input, textarea, select').forEach(el => {
                if (el.tagName === 'SELECT') el.selectedIndex = 0;
                else el.value = '';
            });
            // I-refresh ang dashboard charts kung nandoon tayo
            if (document.getElementById('section-dashboard')?.classList.contains('active')) {
                loadDashboardStats();
            }
        }
    } catch (error) {
        showToast('Error recording case: ' + error.message, 'error');
    }
}

/* ============================================================
   OVERRIDE NG SIDEBAR BUTTON ONCLICK HANDLERS
   Para mag-load ng patients/data bago mag-open ng modal
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {

    // I-override ang Add Record button sa medical-records section
    const addRecordBtn = document.querySelector('#section-medical-records .btn-primary');
    if (addRecordBtn) addRecordBtn.onclick = openAddRecordModal;

    // I-override ang Add Immunization button
    const addImmunBtn = document.querySelector('#section-immunizations .btn-primary');
    if (addImmunBtn) addImmunBtn.onclick = openAddImmunModal;

    // I-override ang Record Case button
    const addCaseBtn = document.querySelector('#section-disease-cases .btn-primary');
    if (addCaseBtn) addCaseBtn.onclick = openAddCaseModal;
});