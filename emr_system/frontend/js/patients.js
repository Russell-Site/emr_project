/* ============================================================
   patients.js - Patient Management JavaScript
   Handles: loading, searching, filtering, and CRUD ng patients
   ============================================================ */

/**
 * I-load ang listahan ng mga pasyente na may optional na filters.
 * Tinatawag ng search input at filter dropdowns.
 */
async function loadPatients() {
    try {
        // Kolektahin ang lahat ng filter values
        const search    = document.getElementById('patientSearch')?.value.trim() || '';
        const barangay  = document.getElementById('filterBarangay')?.value || '';
        const sex       = document.getElementById('filterSex')?.value || '';

        // Gumawa ng query string
        let queryParts = [];
        if (search)   queryParts.push(`search=${encodeURIComponent(search)}`);
        if (barangay) queryParts.push(`barangay_id=${barangay}`);
        if (sex)      queryParts.push(`sex=${encodeURIComponent(sex)}`);
        queryParts.push('limit=50');

        const query   = queryParts.length ? `?${queryParts.join('&')}` : '?limit=50';
        const patients = await apiGet(`/api/patients/${query}`);

        const tbody = document.getElementById('patientsTableBody');
        if (!tbody) return;

        if (!patients || patients.length === 0) {
            // Walang nahanap na pasyente
            tbody.innerHTML = `<tr><td colspan="7">
                <div class="empty-state">
                    <div class="empty-icon">👥</div>
                    <h3>No patients found</h3>
                    <p>${search ? `No results for "${escapeHtml(search)}"` : 'No patients registered yet.'}</p>
                </div>
            </td></tr>`;
            return;
        }

        // I-render ang patient rows
        tbody.innerHTML = patients.map((patient, idx) => `
            <tr>
                <td style="color:var(--text-muted);font-size:12px;">${idx + 1}</td>
                <td>
                    <div style="font-weight:600;">${escapeHtml(patient.last_name)}, ${escapeHtml(patient.first_name)}</div>
                    ${patient.middle_name ? `<div style="font-size:11.5px;color:var(--text-muted);">${escapeHtml(patient.middle_name)}</div>` : ''}
                </td>
                <td>
                    <div>${patient.age || calculateAge(patient.birthdate)} yrs</div>
                    <span class="badge ${patient.sex === 'Male' ? 'badge-male' : 'badge-female'}" style="margin-top:3px;">
                        ${patient.sex === 'Male' ? '♂' : '♀'} ${patient.sex}
                    </span>
                </td>
                <td style="font-size:13px;">${escapeHtml(patient.barangay_name || '—')}</td>
                <td style="font-size:13px;">${escapeHtml(patient.contact_number || '—')}</td>
                <td style="font-size:12px;color:var(--text-muted);">${escapeHtml(patient.philhealth_no || '—')}</td>
                <td>
                    <div style="display:flex;gap:5px;">
                        <button class="btn btn-outline btn-sm" onclick="viewPatient(${patient.patient_id})" title="View Details">👁️</button>
                        <button class="btn btn-outline btn-sm" onclick="editPatient(${patient.patient_id})" title="Edit">✏️</button>
                        ${isAdmin() ? `<button class="btn btn-danger btn-sm" onclick="archivePatient(${patient.patient_id}, '${escapeHtml(patient.last_name)}')" title="Archive">🗃️</button>` : ''}
                    </div>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        showToast('Error loading patients: ' + error.message, 'error');
    }
}

/**
 * I-submit ang Add Patient form.
 * Nagva-validate ng data bago ipadala sa backend.
 */
async function submitAddPatient() {
    // Kolektahin ang form data
    const lastName   = document.getElementById('ptLastName')?.value.trim();
    const firstName  = document.getElementById('ptFirstName')?.value.trim();
    const middleName = document.getElementById('ptMiddleName')?.value.trim();
    const birthdate  = document.getElementById('ptBirthdate')?.value;
    const sex        = document.getElementById('ptSex')?.value;
    const civil      = document.getElementById('ptCivilStatus')?.value;
    const barangay   = document.getElementById('ptBarangay')?.value;
    const contact    = document.getElementById('ptContact')?.value.trim();
    const address    = document.getElementById('ptAddress')?.value.trim();
    const philhealth = document.getElementById('ptPhilhealth')?.value.trim();

    // Validation - suriin ang required fields
    if (!lastName || !firstName || !birthdate || !sex || !barangay || !address) {
        showToast('Please fill in all required fields (marked with *).', 'warning');
        return;
    }

    // Suriin ang birthdate (hindi pwedeng sa hinaharap)
    if (new Date(birthdate) > new Date()) {
        showToast('Birthdate cannot be in the future.', 'warning');
        return;
    }

    try {
        const payload = {
            last_name:      lastName,
            first_name:     firstName,
            middle_name:    middleName || null,
            birthdate:      birthdate,
            sex:            sex,
            civil_status:   civil || null,
            barangay_id:    parseInt(barangay),
            contact_number: contact || null,
            address:        address,
            philhealth_no:  philhealth || null
        };

        const result = await apiPost('/api/patients/', payload);

        if (result) {
            showToast(`Patient ${result.last_name}, ${result.first_name} registered successfully!`, 'success');
            closeModal('addPatientModal');

            // I-clear ang form
            document.getElementById('addPatientForm')?.reset();

            // I-reload ang listahan ng pasyente
            loadPatients();
        }
    } catch (error) {
        showToast('Error registering patient: ' + error.message, 'error');
    }
}

/**
 * I-view ang detalye ng isang pasyente.
 * Nagbubukas ng modal na may complete na impormasyon.
 */
async function viewPatient(patientId) {
    try {
        const patient = await apiGet(`/api/patients/${patientId}`);
        if (!patient) return;

        // Gumawa ng simple view modal
        const age = patient.age || calculateAge(patient.birthdate);

        // I-show ang patient details sa isang alert o modal
        const details = [
            `👤 ${patient.last_name}, ${patient.first_name} ${patient.middle_name || ''}`,
            `📅 Birthdate: ${formatDate(patient.birthdate)} (${age} years old)`,
            `⚧ Sex: ${patient.sex} | Civil Status: ${patient.civil_status || 'N/A'}`,
            `🏘️ Barangay: ${patient.barangay_name}`,
            `📱 Contact: ${patient.contact_number || 'N/A'}`,
            `🏥 PhilHealth: ${patient.philhealth_no || 'N/A'}`,
            `🏠 Address: ${patient.address}`
        ].join('\n');

        alert(details); // Sa production, gamitin ang proper modal

    } catch (error) {
        showToast('Error loading patient details: ' + error.message, 'error');
    }
}

/**
 * I-archive (soft delete) ang isang pasyente (Admin only).
 */
async function archivePatient(patientId, lastName) {
    const confirmed = await confirmAction(
        `Are you sure you want to archive patient "${lastName}"? This action can be reversed by the admin.`
    );
    if (!confirmed) return;

    try {
        const result = await apiDelete(`/api/patients/${patientId}`);
        if (result) {
            showToast(`Patient record archived successfully.`, 'success');
            loadPatients();
        }
    } catch (error) {
        showToast('Error archiving patient: ' + error.message, 'error');
    }
}

/**
 * Buksan ang edit form para sa isang pasyente.
 */
async function editPatient(patientId) {
    try {
        const patient = await apiGet(`/api/patients/${patientId}`);
        if (!patient) return;

        // I-populate ang add patient modal para sa editing
        document.getElementById('ptLastName').value  = patient.last_name || '';
        document.getElementById('ptFirstName').value = patient.first_name || '';
        document.getElementById('ptMiddleName').value = patient.middle_name || '';
        document.getElementById('ptBirthdate').value = patient.birthdate || '';
        document.getElementById('ptSex').value       = patient.sex || '';
        document.getElementById('ptCivilStatus').value = patient.civil_status || '';
        document.getElementById('ptAddress').value   = patient.address || '';
        document.getElementById('ptContact').value   = patient.contact_number || '';
        document.getElementById('ptPhilhealth').value = patient.philhealth_no || '';

        // I-set ang barangay filter para sa edit mode
        await loadBarangaysForSelect('ptBarangay');
        document.getElementById('ptBarangay').value = patient.barangay_id || '';

        // I-update ang modal title at submit button para sa edit mode
        const modal = document.getElementById('addPatientModal');
        if (modal) {
            modal.querySelector('.modal-title').textContent = '✏️ Edit Patient Record';

            // I-update ang save button para i-call ang update function
            const saveBtn = modal.querySelector('.modal-footer .btn-primary');
            if (saveBtn) {
                saveBtn.textContent = '💾 Update Patient';
                saveBtn.onclick = () => submitUpdatePatient(patientId);
            }
        }

        openModal('addPatientModal');

    } catch (error) {
        showToast('Error loading patient for editing: ' + error.message, 'error');
    }
}

/**
 * I-submit ang update ng patient information.
 */
async function submitUpdatePatient(patientId) {
    const lastName  = document.getElementById('ptLastName')?.value.trim();
    const firstName = document.getElementById('ptFirstName')?.value.trim();

    if (!lastName || !firstName) {
        showToast('Please fill in the required fields.', 'warning');
        return;
    }

    try {
        const payload = {
            last_name:      document.getElementById('ptLastName')?.value.trim(),
            first_name:     document.getElementById('ptFirstName')?.value.trim(),
            middle_name:    document.getElementById('ptMiddleName')?.value.trim() || null,
            birthdate:      document.getElementById('ptBirthdate')?.value,
            sex:            document.getElementById('ptSex')?.value,
            civil_status:   document.getElementById('ptCivilStatus')?.value || null,
            barangay_id:    parseInt(document.getElementById('ptBarangay')?.value),
            contact_number: document.getElementById('ptContact')?.value.trim() || null,
            address:        document.getElementById('ptAddress')?.value.trim(),
            philhealth_no:  document.getElementById('ptPhilhealth')?.value.trim() || null
        };

        const result = await apiPut(`/api/patients/${patientId}`, payload);
        if (result) {
            showToast('Patient record updated successfully!', 'success');
            closeModal('addPatientModal');
            loadPatients();

            // I-reset ang modal para sa add mode
            const modal = document.getElementById('addPatientModal');
            if (modal) {
                modal.querySelector('.modal-title').textContent = '➕ Register New Patient';
                const saveBtn = modal.querySelector('.modal-footer .btn-primary');
                if (saveBtn) {
                    saveBtn.textContent = '💾 Save Patient';
                    saveBtn.onclick = submitAddPatient;
                }
            }
        }
    } catch (error) {
        showToast('Error updating patient: ' + error.message, 'error');
    }
}

/**
 * I-clear ang lahat ng search filters.
 */
function clearFilters() {
    const searchInput  = document.getElementById('patientSearch');
    const barangayFilter = document.getElementById('filterBarangay');
    const sexFilter    = document.getElementById('filterSex');

    if (searchInput)    searchInput.value    = '';
    if (barangayFilter) barangayFilter.value = '';
    if (sexFilter)      sexFilter.value      = '';

    loadPatients();
}

/* ---- I-populate ang barangay select sa Add Patient Modal ---- */
document.addEventListener('DOMContentLoaded', async function() {
    await loadBarangaysForSelect('ptBarangay');
});
