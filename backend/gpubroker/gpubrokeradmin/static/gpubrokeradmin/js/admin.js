/**
 * GPUBROKER Admin Dashboard JavaScript
 * 
 * Handles dashboard data loading, charts, modals, and environment switching.
 */

// API Configuration
const API_BASE = window.location.origin;

// Environment state
let currentEnv = localStorage.getItem('admin_env') || 'live';

// ============================================
// AUTHENTICATION
// ============================================

function getHeaders() {
    const token = localStorage.getItem('admin_token') || sessionStorage.getItem('admin_token');
    if (!token) {
        window.location.href = '/admin/login/';
        return {};
    }
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Environment': currentEnv
    };
}

function logout() {
    localStorage.removeItem('admin_token');
    sessionStorage.removeItem('admin_token');
    window.location.href = '/admin/login/';
}

// ============================================
// ENVIRONMENT TOGGLE
// ============================================

function setEnv(env) {
    currentEnv = env;
    localStorage.setItem('admin_env', env);
    updateEnvUI();
    loadDashboard();
}

function updateEnvUI() {
    document.querySelectorAll('.env-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.classList.contains(currentEnv)) btn.classList.add('active');
    });
    document.body.classList.remove('env-sandbox', 'env-live');
    document.body.classList.add(`env-${currentEnv}`);
}

// ============================================
// MODAL FUNCTIONS
// ============================================

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Close modal on overlay click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
        document.body.style.overflow = '';
    }
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.active').forEach(modal => {
            modal.classList.remove('active');
        });
        document.body.style.overflow = '';
    }
});

// ============================================
// SECTION NAVIGATION
// ============================================

function showSection(section) {
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.dataset.section === section) tab.classList.add('active');
    });
}


// ============================================
// DASHBOARD DATA LOADING
// ============================================

async function loadDashboard() {
    try {
        const resp = await fetch(`${API_BASE}/api/v2/admin/dashboard`, { headers: getHeaders() });
        if (!resp.ok) {
            if (resp.status === 401) {
                logout();
                return;
            }
            throw new Error('Failed to load dashboard');
        }
        const data = await resp.json();
        updateDashboard(data);
    } catch (e) {
        console.error('Dashboard load error:', e);
        // Show error state but don't redirect
        document.getElementById('podsCount').textContent = '0';
        document.getElementById('revenueAmount').textContent = '$0';
        document.getElementById('customersCount').textContent = '0';
        document.getElementById('alertsCount').textContent = '0';
    }
}

function updateDashboard(data) {
    // Update KPI cards
    document.getElementById('podsCount').textContent = data.pods?.count || 0;
    document.getElementById('podsChange').textContent = `+${data.pods?.today || 0} hoy`;
    
    document.getElementById('revenueAmount').textContent = `$${data.revenue?.amount || 0}`;
    document.getElementById('revenueChange').textContent = `+${data.revenue?.growth || 0}%`;
    
    document.getElementById('customersCount').textContent = data.customers?.count || 0;
    document.getElementById('customersChange').textContent = `+${data.customers?.new || 0} nuevos`;
    
    document.getElementById('alertsCount').textContent = data.alerts?.count || 0;
    
    // Update modal data
    document.getElementById('modalRevenueAmount').textContent = `$${data.revenue?.amount || 0}`;
    document.getElementById('modalTxCount').textContent = data.revenue?.transactions || 0;
    document.getElementById('modalAvgOrder').textContent = `$${data.revenue?.average || 0}`;
    document.getElementById('modalGrowth').textContent = `+${data.revenue?.growth || 0}%`;
    
    // Update activity feed
    updateActivityFeed(data.activity || []);
    
    // Update pods table
    updatePodsTable(data.pods?.list || []);
    
    // Update customers list
    updateCustomersList(data.customers?.list || []);
    
    // Update charts
    updateCharts(data);
}

function updateActivityFeed(activities) {
    const feed = document.getElementById('activityFeed');
    if (!activities.length) {
        feed.innerHTML = '<p style="text-align: center; color: var(--color-muted); padding: 2rem;">Sin actividad reciente</p>';
        return;
    }
    
    feed.innerHTML = activities.slice(0, 10).map(a => `
        <div class="activity-item">
            <div class="activity-icon ${a.type}">
                <span class="material-symbols-rounded">${getActivityIcon(a.type)}</span>
            </div>
            <div class="activity-content">
                <div class="activity-title">${a.title}</div>
                <div class="activity-time">${a.time}</div>
            </div>
        </div>
    `).join('');
}

function getActivityIcon(type) {
    const icons = {
        'payment': 'payments',
        'pod_start': 'play_arrow',
        'pod_stop': 'stop',
        'signup': 'person_add',
        'alert': 'warning',
        'default': 'info'
    };
    return icons[type] || icons.default;
}

function updatePodsTable(pods) {
    const tbody = document.getElementById('podsTableBody');
    if (!pods.length) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--color-muted);">Sin pods activos</td></tr>';
        return;
    }
    
    tbody.innerHTML = pods.map(p => `
        <tr>
            <td style="font-family: var(--font-mono);">${p.pod_id}</td>
            <td>${p.email}</td>
            <td>${(p.plan || 'pro').toUpperCase()}</td>
            <td><span class="status-badge ${p.status}">${p.status.toUpperCase()}</span></td>
        </tr>
    `).join('');
}

function updateCustomersList(customers) {
    const list = document.getElementById('customersListModal');
    if (!customers.length) {
        list.innerHTML = '<p style="text-align: center; color: var(--color-muted);">Sin clientes</p>';
        return;
    }
    
    list.innerHTML = customers.slice(0, 5).map(c => `
        <div class="activity-item" onclick="window.location='/admin/customers/?email=${encodeURIComponent(c.email)}'">
            <div class="activity-icon">
                <span class="material-symbols-rounded">person</span>
            </div>
            <div class="activity-content">
                <div class="activity-title">${c.name || c.email}</div>
                <div class="activity-time">${c.plan?.toUpperCase() || 'TRIAL'} • ${c.created_at || ''}</div>
            </div>
        </div>
    `).join('');
}


// ============================================
// CHARTS
// ============================================

let revenueChart = null;
let distributionChart = null;

function updateCharts(data) {
    // Revenue Chart
    const revenueCtx = document.getElementById('revenueChart');
    if (revenueCtx) {
        if (revenueChart) revenueChart.destroy();
        
        const months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
        const currentMonth = new Date().getMonth();
        const labels = months.slice(Math.max(0, currentMonth - 5), currentMonth + 1);
        const values = data.revenue?.monthly || [0, 0, 0, 0, 0, 0];
        
        revenueChart = new Chart(revenueCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Ingresos',
                    data: values.slice(-6),
                    borderColor: '#22C55E',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#22C55E',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.05)' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }
    
    // Distribution Chart
    const distCtx = document.getElementById('distributionChart');
    if (distCtx) {
        if (distributionChart) distributionChart.destroy();
        
        const plans = data.plans || { trial: 0, basic: 0, pro: 0, corp: 0, enterprise: 0 };
        
        distributionChart = new Chart(distCtx, {
            type: 'doughnut',
            data: {
                labels: ['Trial', 'Basic', 'Pro', 'Corp', 'Enterprise'],
                datasets: [{
                    data: [plans.trial, plans.basic, plans.pro, plans.corp, plans.enterprise],
                    backgroundColor: [
                        '#E5E7EB',
                        '#93C5FD',
                        '#22C55E',
                        '#F59E0B',
                        '#8B5CF6'
                    ],
                    borderWidth: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { boxWidth: 12, padding: 8 }
                    }
                },
                cutout: '60%'
            }
        });
    }
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    updateEnvUI();
    loadDashboard();
    
    // Auto-refresh every 60 seconds
    setInterval(loadDashboard, 60000);
});
