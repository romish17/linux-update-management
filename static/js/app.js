// Global state
let servers = [];
let history = [];

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadServers();
    loadHistory();
    setupEventListeners();

    // Auto-refresh every 30 seconds
    setInterval(() => {
        loadStats();
        loadServers();
        loadHistory();
    }, 30000);
});

// Setup event listeners
function setupEventListeners() {
    const toggleFormBtn = document.getElementById('toggle-form-btn');
    const cancelFormBtn = document.getElementById('cancel-form-btn');
    const serverForm = document.getElementById('server-form');
    const outputModal = document.getElementById('output-modal');
    const closeBtn = document.querySelector('.close');

    toggleFormBtn.addEventListener('click', () => {
        const form = document.getElementById('add-server-form');
        form.style.display = form.style.display === 'none' ? 'block' : 'none';
    });

    cancelFormBtn.addEventListener('click', () => {
        document.getElementById('add-server-form').style.display = 'none';
        serverForm.reset();
    });

    serverForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await addServer();
    });

    closeBtn.addEventListener('click', () => {
        outputModal.style.display = 'none';
    });

    window.addEventListener('click', (e) => {
        if (e.target === outputModal) {
            outputModal.style.display = 'none';
        }
    });
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        document.getElementById('total-servers').textContent = data.total_servers;
        document.getElementById('servers-with-updates').textContent = data.servers_with_updates;
        document.getElementById('total-updates').textContent = data.total_updates;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load servers
async function loadServers() {
    try {
        const response = await fetch('/api/servers');
        servers = await response.json();
        renderServers();
    } catch (error) {
        console.error('Error loading servers:', error);
    }
}

// Render servers
function renderServers() {
    const container = document.getElementById('servers-list');

    if (servers.length === 0) {
        container.innerHTML = '<p style="color: white; text-align: center;">Aucun serveur configuré. Ajoutez-en un pour commencer.</p>';
        return;
    }

    container.innerHTML = servers.map(server => `
        <div class="server-card">
            <div class="server-header">
                <h3>${server.name}</h3>
                <span class="server-status status-${server.status}">${server.status}</span>
            </div>
            <div class="server-info">
                <p><strong>Hostname:</strong> ${server.hostname}:${server.port}</p>
                <p><strong>Utilisateur:</strong> ${server.username}</p>
                <p><strong>Dernière vérif:</strong> ${server.last_check ? new Date(server.last_check).toLocaleString('fr-FR') : 'Jamais'}</p>
                <span class="os-badge">${server.os_type === 'debian' ? '🐧 Debian/Ubuntu' : '🎩 AlmaLinux/RHEL'}</span>
            </div>
            ${server.updates_available > 0 ? `
                <div class="updates-badge">
                    ⚠️ ${server.updates_available} mise(s) à jour disponible(s)
                </div>
            ` : ''}
            <div class="server-actions">
                <button class="btn btn-info" onclick="checkUpdates(${server.id}, false)">🔍 Vérifier tout</button>
                <button class="btn btn-info" onclick="checkUpdates(${server.id}, true)">🔐 Vérifier sécurité</button>
                ${server.updates_available > 0 ? `
                    <button class="btn btn-success" onclick="applyUpdates(${server.id}, false)">⬆️ Tout mettre à jour</button>
                    <button class="btn btn-warning" onclick="applyUpdates(${server.id}, true)">🔐 MAJ sécurité</button>
                ` : ''}
                <button class="btn btn-primary" onclick="openScheduleModal(${server.id})">📅 Planifier</button>
                <button class="btn btn-danger" onclick="deleteServer(${server.id})">🗑️ Supprimer</button>
            </div>
        </div>
    `).join('');
}

// Load history
async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        history = await response.json();
        renderHistory();
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

// Render history
function renderHistory() {
    const container = document.getElementById('history-list');

    if (history.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #666;">Aucun historique disponible.</p>';
        return;
    }

    container.innerHTML = history.slice(0, 20).map(item => {
        const actionLabel = item.action === 'check' ? 'Vérification' :
                           item.action === 'security_update' ? 'MAJ Sécurité' :
                           item.action === 'update' ? 'Mise à jour' : 'Erreur';

        const typeLabel = item.update_type === 'security' ? ' 🔐 Sécurité' :
                         item.update_type === 'all' ? ' 📦 Toutes' : '';

        const duration = item.duration ? ` (${item.duration.toFixed(1)}s)` : '';

        // Build package summary
        let packageSummary = '';
        if (item.package_list && item.package_list.length > 0) {
            const pkgCount = item.package_list.length;
            const pkgNames = item.package_list.slice(0, 3).map(p => p.name).join(', ');
            packageSummary = `<br><small>Paquets: ${pkgNames}${pkgCount > 3 ? `, +${pkgCount - 3} autres` : ''}</small>`;
        }

        return `
            <div class="history-item" onclick="showHistoryDetails(${item.id})" style="cursor: pointer;">
                <div class="history-info">
                    <h4>${item.server_name || 'Serveur inconnu'} ${item.server_hostname ? `(${item.server_hostname})` : ''}</h4>
                    <p>
                        ${new Date(item.created_at).toLocaleString('fr-FR')} - ${actionLabel}${typeLabel} - ${item.packages_count} paquet(s)${duration}
                        ${packageSummary}
                    </p>
                </div>
                <span class="history-badge badge-${item.action}">
                    ${item.success ? '✓' : '✗'}
                </span>
            </div>
        `;
    }).join('');
}

// Show history details
function showHistoryDetails(historyId) {
    const item = history.find(h => h.id === historyId);
    if (!item) return;

    let content = `Serveur: ${item.server_name} (${item.server_hostname})\n`;
    content += `Date: ${new Date(item.created_at).toLocaleString('fr-FR')}\n`;
    content += `Action: ${item.action}\n`;
    content += `Type: ${item.update_type}\n`;
    content += `Succès: ${item.success ? 'Oui' : 'Non'}\n`;
    content += `Paquets: ${item.packages_count}\n`;
    if (item.duration) {
        content += `Durée: ${item.duration.toFixed(2)} secondes\n`;
    }

    if (item.package_list && item.package_list.length > 0) {
        content += `\n=== Liste des paquets (${item.package_list.length}) ===\n\n`;
        item.package_list.forEach((pkg, idx) => {
            content += `${idx + 1}. ${pkg.name}`;
            if (pkg.version) {
                content += ` - ${pkg.version}`;
            } else if (pkg.old_version && pkg.new_version) {
                content += ` (${pkg.old_version} → ${pkg.new_version})`;
            } else if (pkg.new_version) {
                content += ` - ${pkg.new_version}`;
            }
            if (pkg.is_security) {
                content += ' [SÉCURITÉ]';
            }
            content += '\n';
        });
    }

    if (item.output) {
        content += `\n=== Sortie complète ===\n\n${item.output}`;
    }

    showOutput('Détails de l\'historique', content);
}

// Add server
async function addServer() {
    const form = document.getElementById('server-form');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);

    showLoading('Ajout du serveur...');

    try {
        const response = await fetch('/api/servers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        hideLoading();

        if (response.ok) {
            form.reset();
            document.getElementById('add-server-form').style.display = 'none';
            await loadServers();
            await loadStats();
            showMessage('Serveur ajouté avec succès !');
        } else {
            const error = await response.json();
            showMessage('Erreur: ' + (error.error || 'Une erreur est survenue'), true);
        }
    } catch (error) {
        hideLoading();
        showMessage('Erreur: ' + error.message, true);
    }
}

// Delete server
async function deleteServer(serverId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce serveur ?')) {
        return;
    }

    showLoading('Suppression du serveur...');

    try {
        const response = await fetch(`/api/servers/${serverId}`, {
            method: 'DELETE'
        });

        hideLoading();

        if (response.ok) {
            await loadServers();
            await loadStats();
            showMessage('Serveur supprimé avec succès !');
        } else {
            showMessage('Erreur lors de la suppression', true);
        }
    } catch (error) {
        hideLoading();
        showMessage('Erreur: ' + error.message, true);
    }
}

// Check updates
async function checkUpdates(serverId, securityOnly = false) {
    const message = securityOnly ? 'Vérification des mises à jour de sécurité...' : 'Vérification des mises à jour...';
    showLoading(message);

    try {
        const response = await fetch(`/api/servers/${serverId}/check`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ security_only: securityOnly })
        });

        const data = await response.json();
        hideLoading();

        if (response.ok) {
            await loadServers();
            await loadStats();
            await loadHistory();

            // Show detailed package list if available
            let output = data.output || 'Vérification terminée';
            if (data.packages && data.packages.length > 0) {
                output = `Mises à jour disponibles: ${data.packages.length}\n\n`;
                output += 'Liste des paquets:\n';
                data.packages.forEach(pkg => {
                    output += `\n- ${pkg.name}`;
                    if (pkg.old_version && pkg.new_version) {
                        output += ` (${pkg.old_version} → ${pkg.new_version})`;
                    } else if (pkg.new_version) {
                        output += ` (version: ${pkg.new_version})`;
                    }
                    if (pkg.is_security) {
                        output += ' [SÉCURITÉ]';
                    }
                });
            }

            showOutput('Résultat de la vérification', output);
        } else {
            showMessage('Erreur: ' + (data.error || data.message || 'Une erreur est survenue'), true);
        }
    } catch (error) {
        hideLoading();
        showMessage('Erreur: ' + error.message, true);
    }
}

// Apply updates
async function applyUpdates(serverId, securityOnly = false) {
    const confirmMsg = securityOnly
        ? 'Êtes-vous sûr de vouloir appliquer uniquement les mises à jour de sécurité ? Cette opération peut prendre plusieurs minutes.'
        : 'Êtes-vous sûr de vouloir appliquer toutes les mises à jour ? Cette opération peut prendre plusieurs minutes.';

    if (!confirm(confirmMsg)) {
        return;
    }

    const loadingMsg = securityOnly
        ? 'Application des mises à jour de sécurité en cours...'
        : 'Application des mises à jour en cours...';

    showLoading(loadingMsg);

    try {
        const response = await fetch(`/api/servers/${serverId}/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ security_only: securityOnly })
        });

        const data = await response.json();
        hideLoading();

        if (response.ok) {
            await loadServers();
            await loadStats();
            await loadHistory();

            // Show detailed package list if available
            let output = data.output || 'Mise à jour terminée';
            if (data.packages && data.packages.length > 0) {
                output = `${data.packages.length} paquet(s) installé(s)\n\n`;
                output += 'Paquets installés:\n';
                data.packages.forEach(pkg => {
                    output += `\n- ${pkg.name}`;
                    if (pkg.version) {
                        output += ` (${pkg.version})`;
                    }
                });
                output += '\n\n--- Détails complets ---\n\n' + data.output;
            }

            // Add reboot info if applicable
            if (data.reboot_scheduled) {
                output += '\n\n⚠️ REDÉMARRAGE PROGRAMMÉ\n' + data.reboot_message;
            } else if (data.reboot_required) {
                output += '\n\n⚠️ REDÉMARRAGE NÉCESSAIRE\nLe serveur doit être redémarré pour appliquer complètement les mises à jour.';
            }

            showOutput('Résultat de la mise à jour', output);
        } else {
            showMessage('Erreur: ' + (data.error || data.message || 'Une erreur est survenue'), true);
        }
    } catch (error) {
        hideLoading();
        showMessage('Erreur: ' + error.message, true);
    }
}

// Show loading modal
function showLoading(message) {
    const modal = document.getElementById('loading-modal');
    const text = document.getElementById('loading-text');
    text.textContent = message;
    modal.style.display = 'flex';
}

// Hide loading modal
function hideLoading() {
    document.getElementById('loading-modal').style.display = 'none';
}

// Show output modal
function showOutput(title, content) {
    const modal = document.getElementById('output-modal');
    const titleEl = document.getElementById('output-title');
    const contentEl = document.getElementById('output-content');

    titleEl.textContent = title;
    contentEl.textContent = content;
    modal.style.display = 'flex';
}

// Show message (simple alert for now)
function showMessage(message, isError = false) {
    alert(message);
}

// ========== Schedule Management ==========

let currentServerId = null;

// Open schedule modal
async function openScheduleModal(serverId) {
    currentServerId = serverId;
    const modal = document.getElementById('schedule-modal');
    const form = document.getElementById('schedule-form');

    // Reset form
    form.reset();
    document.getElementById('schedule-server-id').value = serverId;
    document.getElementById('schedule-id').value = '';
    document.getElementById('schedule-type').value = 'weekly';
    document.getElementById('day-of-week').value = '6'; // Sunday
    updateScheduleTypeFields();

    // Load existing schedules
    await loadServerSchedules(serverId);

    modal.style.display = 'flex';
}

// Close schedule modal
function closeScheduleModal() {
    document.getElementById('schedule-modal').style.display = 'none';
}

// Update schedule type fields visibility
function updateScheduleTypeFields() {
    const scheduleType = document.getElementById('schedule-type').value;
    const dayOfWeekGroup = document.getElementById('day-of-week-group');
    const dayOfMonthGroup = document.getElementById('day-of-month-group');

    dayOfWeekGroup.style.display = scheduleType === 'weekly' ? 'block' : 'none';
    dayOfMonthGroup.style.display = scheduleType === 'monthly' ? 'block' : 'none';

    // Set required attributes
    document.getElementById('day-of-week').required = scheduleType === 'weekly';
    document.getElementById('day-of-month').required = scheduleType === 'monthly';
}

// Load server schedules
async function loadServerSchedules(serverId) {
    try {
        const response = await fetch(`/api/servers/${serverId}/schedules`);
        const schedules = await response.json();
        renderExistingSchedules(schedules);
    } catch (error) {
        console.error('Error loading schedules:', error);
    }
}

// Render existing schedules
function renderExistingSchedules(schedules) {
    const container = document.getElementById('existing-schedules');

    if (schedules.length === 0) {
        container.innerHTML = '<p style="color: #666;">Aucune planification configurée.</p>';
        return;
    }

    container.innerHTML = '<h3>Planifications existantes</h3>' + schedules.map(schedule => {
        const scheduleDesc = getScheduleDescription(schedule);
        const updateTypeLabel = schedule.update_type === 'security' ? '🔐 Sécurité' : '📦 Toutes';
        const rebootLabel = schedule.auto_reboot ? ' + ♻️ Reboot' : '';
        const statusClass = schedule.enabled ? '' : 'disabled';

        return `
            <div class="schedule-item ${statusClass}">
                <div class="schedule-info">
                    <h4>${scheduleDesc}</h4>
                    <p>${updateTypeLabel}${rebootLabel} ${schedule.enabled ? '✓ Actif' : '✗ Inactif'}</p>
                </div>
                <div class="schedule-actions">
                    <button class="btn btn-danger" onclick="deleteSchedule(${schedule.id})">Supprimer</button>
                </div>
            </div>
        `;
    }).join('');
}

// Get schedule description
function getScheduleDescription(schedule) {
    const days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];
    const time = `${String(schedule.hour).padStart(2, '0')}:${String(schedule.minute).padStart(2, '0')}`;

    if (schedule.schedule_type === 'daily') {
        return `Quotidien à ${time}`;
    } else if (schedule.schedule_type === 'weekly') {
        return `Chaque ${days[schedule.day_of_week]} à ${time}`;
    } else if (schedule.schedule_type === 'monthly') {
        return `Le ${schedule.day_of_month} de chaque mois à ${time}`;
    }
    return 'Planification inconnue';
}

// Save schedule
async function saveSchedule(event) {
    event.preventDefault();

    const serverId = document.getElementById('schedule-server-id').value;
    const scheduleType = document.getElementById('schedule-type').value;

    const data = {
        schedule_type: scheduleType,
        hour: parseInt(document.getElementById('schedule-hour').value),
        minute: parseInt(document.getElementById('schedule-minute').value),
        update_type: document.getElementById('update-type').value,
        auto_reboot: document.getElementById('auto-reboot').checked,
        enabled: document.getElementById('schedule-enabled').checked
    };

    if (scheduleType === 'weekly') {
        data.day_of_week = parseInt(document.getElementById('day-of-week').value);
    } else if (scheduleType === 'monthly') {
        data.day_of_month = parseInt(document.getElementById('day-of-month').value);
    }

    showLoading('Configuration de la planification...');

    try {
        const response = await fetch(`/api/servers/${serverId}/schedules`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        hideLoading();

        if (response.ok) {
            showMessage('Planification créée avec succès !');
            await loadServerSchedules(serverId);
            document.getElementById('schedule-form').reset();
        } else {
            showMessage('Erreur: ' + (result.error || 'Une erreur est survenue'), true);
        }
    } catch (error) {
        hideLoading();
        showMessage('Erreur: ' + error.message, true);
    }
}

// Delete schedule
async function deleteSchedule(scheduleId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette planification ?')) {
        return;
    }

    showLoading('Suppression de la planification...');

    try {
        const response = await fetch(`/api/schedules/${scheduleId}`, {
            method: 'DELETE'
        });

        hideLoading();

        if (response.ok) {
            showMessage('Planification supprimée avec succès !');
            if (currentServerId) {
                await loadServerSchedules(currentServerId);
            }
        } else {
            showMessage('Erreur lors de la suppression', true);
        }
    } catch (error) {
        hideLoading();
        showMessage('Erreur: ' + error.message, true);
    }
}

// Setup schedule event listeners
document.addEventListener('DOMContentLoaded', () => {
    const scheduleForm = document.getElementById('schedule-form');
    const scheduleType = document.getElementById('schedule-type');
    const closeScheduleBtns = document.querySelectorAll('.close-schedule');
    const scheduleModal = document.getElementById('schedule-modal');

    scheduleForm.addEventListener('submit', saveSchedule);
    scheduleType.addEventListener('change', updateScheduleTypeFields);

    closeScheduleBtns.forEach(btn => {
        btn.addEventListener('click', closeScheduleModal);
    });

    window.addEventListener('click', (e) => {
        if (e.target === scheduleModal) {
            closeScheduleModal();
        }
    });
});
