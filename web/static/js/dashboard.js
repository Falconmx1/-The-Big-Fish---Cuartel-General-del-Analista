// ============================================
// THE BIG FISH - Dashboard JavaScript
// ============================================

let charts = {};
let refreshInterval = null;
let currentSection = 'dashboard';

// ============================================
// NAVIGATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const section = this.dataset.section;
            switchSection(section);
        });
    });
    
    // Enter key support for inputs
    document.querySelectorAll('.input-field').forEach(input => {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const section = this.closest('.section');
                if (section) {
                    const id = section.id.replace('section-', '');
                    if (id === 'recon') launchRecon();
                    else if (id === 'track') launchTrack();
                    else if (id === 'nmap') launchNmap();
                }
            }
        });
    });
    
    // Initial load
    refreshData();
    refreshInterval = setInterval(refreshData, 10000);
});

function switchSection(section) {
    currentSection = section;
    
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === section);
    });
    
    // Update sections
    document.querySelectorAll('.section').forEach(el => {
        el.classList.toggle('active', el.id === `section-${section}`);
    });
    
    // Update title
    const titles = {
        dashboard: 'Dashboard',
        recon: 'Fish-recon',
        wifi: 'WifiCannon',
        track: 'Fish-track',
        nmap: 'Fish-nmap',
        history: 'Historial'
    };
    document.getElementById('page-title').textContent = titles[section] || 'Dashboard';
    
    // Refresh data for the section
    if (section === 'history') {
        loadHistory();
    }
}

// ============================================
// API CALLS
// ============================================

async function apiCall(endpoint, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(endpoint, options);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return { error: error.message };
    }
}

// ============================================
// DASHBOARD
// ============================================

async function refreshData() {
    try {
        const data = await apiCall('/api/dashboard');
        if (data.error) {
            console.error('Error loading dashboard:', data.error);
            return;
        }
        
        updateStats(data);
        updateCharts(data);
        updateRunningProcesses(data);
        updateRecentActivity(data);
        
        document.getElementById('last-update').textContent = 
            `Última actualización: ${new Date().toLocaleTimeString()}`;
    } catch (error) {
        console.error('Refresh error:', error);
    }
}

function updateStats(data) {
    const stats = data.stats || {};
    document.getElementById('total-scans').textContent = stats.total_scans || 0;
    document.getElementById('total-handshakes').textContent = stats.total_handshakes || 0;
    document.getElementById('total-subdomains').textContent = stats.total_subdomains || 0;
    document.getElementById('total-locations').textContent = stats.total_locations || 0;
}

function updateCharts(data) {
    const stats = data.stats || {};
    const scansByTool = stats.scans_by_tool || {};
    
    // Tools Chart
    const toolsCtx = document.getElementById('toolsChart');
    if (toolsCtx) {
        if (charts.tools) {
            charts.tools.destroy();
        }
        
        const labels = Object.keys(scansByTool);
        const values = Object.values(scansByTool);
        
        const colors = ['#4a9eff', '#4ae0a0', '#a78bfa', '#fbbf24'];
        const bgColors = labels.map((_, i) => colors[i % colors.length] + '33');
        const borderColors = labels.map((_, i) => colors[i % colors.length]);
        
        charts.tools = new Chart(toolsCtx, {
            type: 'doughnut',
            data: {
                labels: labels.map(l => l.replace('fish_', '').replace('_', ' ')),
                datasets: [{
                    data: values,
                    backgroundColor: bgColors,
                    borderColor: borderColors,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#8899bb',
                            padding: 12
                        }
                    }
                }
            }
        });
    }
    
    // Activity Chart
    const activityCtx = document.getElementById('activityChart');
    if (activityCtx) {
        if (charts.activity) {
            charts.activity.destroy();
        }
        
        const activity = data.activity || [];
        const last7Days = [];
        const counts = [];
        
        for (let i = 6; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            const dateStr = date.toISOString().split('T')[0];
            last7Days.push(dateStr);
            
            const count = activity.filter(a => {
                const aDate = new Date(a.time).toISOString().split('T')[0];
                return aDate === dateStr;
            }).length;
            counts.push(count);
        }
        
        charts.activity = new Chart(activityCtx, {
            type: 'bar',
            data: {
                labels: last7Days.map(d => {
                    const parts = d.split('-');
                    return `${parts[2]}/${parts[1]}`;
                }),
                datasets: [{
                    label: 'Actividad',
                    data: counts,
                    backgroundColor: '#4a9eff66',
                    borderColor: '#4a9eff',
                    borderWidth: 2,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#556688',
                            stepSize: 1
                        },
                        grid: {
                            color: '#1e2d42'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#556688'
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
}

function updateRunningProcesses(data) {
    const container = document.getElementById('running-processes');
    const running = data.running_tools || [];
    
    if (running.length === 0) {
        container.innerHTML = '<p class="empty-message">No hay procesos activos</p>';
        return;
    }
    
    container.innerHTML = running.map(proc => `
        <div class="process-item" style="display:flex;justify-content:space-between;padding:8px 12px;border-bottom:1px solid var(--border-color);">
            <div>
                <span style="color:var(--green);">●</span>
                <strong>${proc.tool.replace('_', ' ')}</strong>
                <span style="color:var(--text-secondary);margin-left:12px;">${proc.target || 'N/A'}</span>
            </div>
            <div style="color:var(--text-secondary);font-size:13px;">
                <span>PID: ${proc.pid}</span>
                <span style="margin-left:12px;">${new Date(proc.start_time).toLocaleTimeString()}</span>
                <button onclick="stopProcess(${proc.scan_id})" style="margin-left:12px;background:var(--red);color:white;border:none;border-radius:4px;padding:2px 10px;cursor:pointer;">Detener</button>
            </div>
        </div>
    `).join('');
}

function updateRecentActivity(data) {
    const container = document.getElementById('recent-activity');
    const activity = data.recent_scans || [];
    
    if (activity.length === 0) {
        container.innerHTML = '<p class="empty-message">No hay actividad reciente</p>';
        return;
    }
    
    container.innerHTML = activity.slice(0, 10).map(scan => {
        const statusBadge = {
            'completed': '<span class="badge badge-success">Completado</span>',
            'running': '<span class="badge badge-info">Ejecutando</span>',
            'failed': '<span class="badge badge-danger">Fallido</span>',
            'stopped': '<span class="badge badge-warning">Detenido</span>'
        }[scan.status] || '<span class="badge badge-info">Desconocido</span>';
        
        return `
            <div style="display:flex;justify-content:space-between;padding:8px 12px;border-bottom:1px solid var(--border-color);">
                <div>
                    <strong>${scan.tool.replace('_', ' ')}</strong>
                    <span style="color:var(--text-secondary);margin-left:12px;">${scan.target}</span>
                </div>
                <div>
                    ${statusBadge}
                    <span style="color:var(--text-muted);margin-left:12px;font-size:13px;">
                        ${new Date(scan.start_time).toLocaleString()}
                    </span>
                    <button onclick="viewDetails(${scan.id})" style="margin-left:12px;background:var(--blue);color:white;border:none;border-radius:4px;padding:2px 10px;cursor:pointer;font-size:12px;">Ver</button>
                </div>
            </div>
        `;
    }).join('');
}

// ============================================
// TOOL LAUNCHERS
// ============================================

async function launchRecon() {
    const target = document.getElementById('recon-target').value.trim();
    if (!target) {
        showNotification('Por favor, ingresa un dominio', 'warning');
        return;
    }
    
    const options = {
        use_dns: document.getElementById('recon-dns').checked,
        use_bruteforce: document.getElementById('recon-bruteforce').checked,
        threads: parseInt(document.getElementById('recon-threads').value) || 10
    };
    
    showNotification(`Iniciando Fish-recon para ${target}...`, 'info');
    
    const result = await apiCall('/api/launch', 'POST', {
        tool: 'fish_recon',
        target: target,
        options: options
    });
    
    if (result.success) {
        showNotification(`Fish-recon iniciado (ID: ${result.scan_id})`, 'success');
        refreshData();
    } else {
        showNotification(`Error: ${result.error}`, 'error');
    }
}

async function launchWifi(mode) {
    const bssid = document.getElementById('wifi-bssid').value.trim();
    const channel = document.getElementById('wifi-channel').value;
    const interface_ = document.getElementById('wifi-interface').value.trim() || 'wlan0';
    
    if (mode !== 'scan' && !bssid) {
        showNotification('Por favor, ingresa un BSSID', 'warning');
        return;
    }
    
    const options = {
        mode: mode,
        interface: interface_
    };
    if (channel) options.channel = parseInt(channel);
    
    const modeLabels = { scan: 'Escaneo', capture: 'Captura', wps: 'Ataque WPS' };
    showNotification(`Iniciando WifiCannon (${modeLabels[mode]})...`, 'info');
    
    const result = await apiCall('/api/launch', 'POST', {
        tool: 'wifi_cannon',
        target: bssid || 'all',
        options: options
    });
    
    if (result.success) {
        showNotification(`WifiCannon iniciado (ID: ${result.scan_id})`, 'success');
        refreshData();
    } else {
        showNotification(`Error: ${result.error}`, 'error');
    }
}

async function launchTrack() {
    const target = document.getElementById('track-target').value.trim();
    if (!target) {
        showNotification('Por favor, ingresa un objetivo', 'warning');
        return;
    }
    
    const options = {
        use_ip: document.getElementById('track-ip').checked,
        use_url: document.getElementById('track-url').checked
    };
    
    showNotification(`Iniciando Fish-track para ${target}...`, 'info');
    
    const result = await apiCall('/api/launch', 'POST', {
        tool: 'fish_track',
        target: target,
        options: options
    });
    
    if (result.success) {
        showNotification(`Fish-track iniciado (ID: ${result.scan_id})`, 'success');
        refreshData();
    } else {
        showNotification(`Error: ${result.error}`, 'error');
    }
}

async function launchNmap() {
    const target = document.getElementById('nmap-target').value.trim();
    if (!target) {
        showNotification('Por favor, ingresa un objetivo', 'warning');
        return;
    }
    
    const scanType = document.getElementById('nmap-type').value;
    const ports = document.getElementById('nmap-ports').value.trim();
    
    const options = {
        scan_type: scanType
    };
    if (ports) options.ports = ports;
    
    const typeLabels = {
        basic: 'Básico',
        full: 'Completo',
        stealth: 'Sigiloso',
        vuln: 'Vulnerabilidades'
    };
    
    showNotification(`Iniciando Fish-nmap (${typeLabels[scanType]}) para ${target}...`, 'info');
    
    const result = await apiCall('/api/launch', 'POST', {
        tool: 'fish_nmap',
        target: target,
        options: options
    });
    
    if (result.success) {
        showNotification(`Fish-nmap iniciado (ID: ${result.scan_id})`, 'success');
        refreshData();
    } else {
        showNotification(`Error: ${result.error}`, 'error');
    }
}

async function stopProcess(scanId) {
    if (!confirm(`¿Detener el proceso ${scanId}?`)) return;
    
    const result = await apiCall(`/api/stop/${scanId}`, 'POST');
    if (result.success) {
        showNotification(`Proceso ${scanId} detenido`, 'success');
        refreshData();
    } else {
        showNotification(`Error: ${result.error}`, 'error');
    }
}

async function viewDetails(scanId) {
    const data = await apiCall(`/api/scan/${scanId}`);
    if (data.error) {
        showNotification(`Error: ${data.error}`, 'error');
        return;
    }
    
    const modal = document.getElementById('modal-details');
    const body = document.getElementById('modal-body');
    
    body.innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div><strong>ID:</strong> ${data.id}</div>
            <div><strong>Herramienta:</strong> ${data.tool}</div>
            <div><strong>Objetivo:</strong> ${data.target}</div>
            <div><strong>Estado:</strong> ${data.status}</div>
            <div><strong>Inicio:</strong> ${new Date(data.start_time).toLocaleString()}</div>
            <div><strong>Fin:</strong> ${data.end_time ? new Date(data.end_time).toLocaleString() : '--'}</div>
        </div>
        <div style="margin-top:16px;background:var(--bg-primary);border-radius:8px;padding:12px;max-height:300px;overflow-y:auto;">
            <pre style="color:var(--text-secondary);font-size:13px;white-space:pre-wrap;word-break:break-all;">${JSON.stringify(data.results || {}, null, 2)}</pre>
        </div>
    `;
    
    modal.style.display = 'block';
}

function closeModal() {
    document.getElementById('modal-details').style.display = 'none';
}

// ============================================
// HISTORY
// ============================================

async function loadHistory() {
    const data = await apiCall('/api/history');
    const tbody = document.getElementById('history-body');
    
    if (data.error || !data.scans || data.scans.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-message">No hay registros en el historial</td></tr>';
        return;
    }
    
    const statusMap = {
        'completed': '<span class="badge badge-success">Completado</span>',
        'running': '<span class="badge badge-info">Ejecutando</span>',
        'failed': '<span class="badge badge-danger">Fallido</span>',
        'stopped': '<span class="badge badge-warning">Detenido</span>'
    };
    
    tbody.innerHTML = data.scans.map(scan => `
        <tr>
            <td>#${scan.id}</td>
            <td>${scan.tool.replace('_', ' ')}</td>
            <td>${scan.target}</td>
            <td>${statusMap[scan.status] || '<span class="badge badge-info">Desconocido</span>'}</td>
            <td>${new Date(scan.start_time).toLocaleString()}</td>
            <td>
                <button onclick="viewDetails(${scan.id})" class="btn-secondary" style="padding:4px 12px;font-size:12px;">Ver</button>
            </td>
        </tr>
    `).join('');
}

function filterHistory() {
    const filter = document.getElementById('history-filter').value.toLowerCase();
    const rows = document.querySelectorAll('#history-body tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(filter) ? '' : 'none';
    });
}

async function clearHistory() {
    if (!confirm('¿Eliminar todo el historial? Esta acción no se puede deshacer.')) return;
    
    const result = await apiCall('/api/history/clear', 'POST');
    if (result.success) {
        showNotification('Historial limpiado', 'success');
        loadHistory();
    } else {
        showNotification(`Error: ${result.error}`, 'error');
    }
}

// ============================================
// NOTIFICATIONS
// ============================================

function showNotification(message, type = 'info') {
    const colors = {
        info: '#4a9eff',
        success: '#4ae0a0',
        warning: '#fbbf24',
        error: '#f87171'
    };
    
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: var(--bg-card);
        border: 1px solid ${colors[type]};
        border-left: 4px solid ${colors[type]};
        color: var(--text-primary);
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        z-index: 9999;
        max-width: 400px;
        animation: slideIn 0.3s ease;
        font-size: 14px;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transition = 'opacity 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

// Add keyframe for notification
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);

// ============================================
// KEYBOARD SHORTCUTS
// ============================================

document.addEventListener('keydown', function(e) {
    // Ctrl+1-5 for navigation
    if (e.ctrlKey && e.key >= '1' && e.key <= '5') {
        e.preventDefault();
        const sections = ['dashboard', 'recon', 'wifi', 'track', 'nmap'];
        const idx = parseInt(e.key) - 1;
        if (idx < sections.length) {
            switchSection(sections[idx]);
        }
    }
    // Escape to close modal
    if (e.key === 'Escape') {
        closeModal();
    }
    // Ctrl+R to refresh
    if (e.ctrlKey && e.key === 'r') {
        e.preventDefault();
        refreshData();
        document.querySelector('.btn-refresh').classList.add('spinning');
        setTimeout(() => {
            document.querySelector('.btn-refresh').classList.remove('spinning');
        }, 1000);
    }
});

// ============================================
// AUTO-REFRESH TOGGLE
// ============================================

// Click on refresh button toggles spinning
document.querySelector('.btn-refresh')?.addEventListener('click', function() {
    this.classList.add('spinning');
    setTimeout(() => {
        this.classList.remove('spinning');
    }, 1000);
});

console.log('🐟 The Big Fish Dashboard loaded successfully!');
console.log('📌 Shortcuts: Ctrl+1-5 (nav), Ctrl+R (refresh), ESC (close modal)');
