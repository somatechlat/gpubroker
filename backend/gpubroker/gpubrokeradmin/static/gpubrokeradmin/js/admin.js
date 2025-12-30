/**
 * GPUBROKER Admin Dashboard JavaScript
 * 
 * Complete admin dashboard with full-screen modals, pod lifecycle management,
 * charts, and real-time data from Django Ninja API.
 */

// API Configuration
const API_BASE = window.location.origin;

// Environment state
let currentEnv = localStorage.getItem('admin_env') || 'live';

// ============================================
// AUTHENTICATION
// ============================================

function checkAuth() {
    const token = localStorage.getItem('admin_token') || sessionStorage.getItem('admin_token');
    if (!token) {
        window.location.href = '/admin/login/';
        return null;
    }
    return token;
}

function getHeaders() {
    const token = checkAuth();
    if (!token) return {};
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Environment': currentEnv
    };
}

function logout() {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    sessionStorage.removeItem('admin_token');
    sessionStorage.removeItem('admin_user');
    window.location.href = '/admin/login/';
}

// ============================================
// ENVIRONMENT TOGGLE (Sandbox/Live)
// ============================================

function getEnv() {
    return currentEnv;
}

function setEnv(env) {
    currentEnv = env;
    localStorage.setItem('admin_env', env);
    updateEnvUI();
    location.reload();
}

function updateEnvUI() {
    document.querySelectorAll('.env-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.classList.contains(currentEnv)) {
            btn.classList.add('active');
        }
    });
    document.body.classList.remove('env-sandbox', 'env-live');
    document.body.classList.add(`env-${currentEnv}`);
}

// ============================================
// NAVIGATION
// ============================================

function showSection(section) {
    document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
    document.querySelector(`[data-section="${section}"]`)?.classList.add('active');

    if (section === 'dashboard') {
        document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
        document.body.style.overflow = '';
    } else if (section === 'pods') {
        openFullModal('pods');
    } else if (section === 'customers') {
        openFullModal('customers');
    } else if (section === 'billing') {
        openFullModal('billing');
    }
}

function updateNavCounts(data) {
    if (!data) return;
    const podsCount = document.getElementById('navPodsCount');
    const customersCount = document.getElementById('navCustomersCount');
    const billingCount = document.getElementById('navBillingCount');

    if (podsCount) podsCount.textContent = data.pods?.active || data.pods?.count || 0;
    if (customersCount) customersCount.textContent = data.customers?.total || data.customers?.count || 0;
    if (billingCount) billingCount.textContent = `$${Math.round(data.revenue?.amount || 0)}`;
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
// DASHBOARD DATA LOADING
// ============================================

async function fetchDashboardData() {
    try {
        const response = await fetch(`${API_BASE}/api/v2/admin/dashboard`, {
            headers: getHeaders()
        });

        if (!response.ok) {
            if (response.status === 401) {
                logout();
                return null;
            }
            console.error('Dashboard API failed:', response.status);
            return null;
        }

        const data = await response.json();
        console.log('[Dashboard] Real data from API:', data);
        return data;
    } catch (err) {
        console.error('Error fetching dashboard data:', err);
        return null;
    }
}

function updateKPICards(data) {
    if (!data) return;

    // Pods
    document.getElementById('podsCount').textContent = data.pods?.active || data.pods?.count || 0;
    document.getElementById('podsChange').textContent = `+${data.pods?.change || data.pods?.today || 0} hoy`;

    // Revenue
    document.getElementById('revenueAmount').textContent = `$${(data.revenue?.amount || 0).toLocaleString()}`;
    document.getElementById('revenueChange').textContent = `+${data.revenue?.change || data.revenue?.growth || 0}%`;
    document.getElementById('modalRevenueAmount').textContent = `$${(data.revenue?.amount || 0).toLocaleString()}`;
    document.getElementById('modalTxCount').textContent = data.revenue?.transactions || 0;
    document.getElementById('modalAvgOrder').textContent = `$${data.revenue?.average || 0}`;
    document.getElementById('modalGrowth').textContent = `+${data.revenue?.growth || 0}%`;

    // Customers
    document.getElementById('customersCount').textContent = data.customers?.total || data.customers?.count || 0;
    document.getElementById('customersChange').textContent = `+${data.customers?.change || data.customers?.new || 0} nuevos`;

    // Alerts
    document.getElementById('alertsCount').textContent = data.alerts?.count || 0;
    if ((data.alerts?.count || 0) === 0) {
        document.getElementById('alertsStatus').innerHTML = '<span style="color: var(--color-success);"><span class="material-symbols-rounded" style="font-size: 14px; vertical-align: middle;">check_circle</span> Sin alertas</span>';
        document.getElementById('alertsStatus').classList.remove('negative');
    }
}

// ============================================
// PODS TABLE
// ============================================

function populatePodsTable(pods) {
    const tbody = document.getElementById('podsTableBody');
    if (!pods || !pods.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--color-muted);">Sin pods activos</td></tr>';
        return;
    }

    tbody.innerHTML = pods.map(pod => `
        <tr class="table-row-clickable" onclick="viewPodDetail('${pod.id || pod.pod_id}')">
            <td><code style="background: var(--color-bg); padding: 2px 8px; border-radius: 4px;">${pod.id || pod.pod_id}</code></td>
            <td>${pod.email}</td>
            <td><span class="status-badge ${pod.plan === 'pro' ? 'running' : 'warning'}">${(pod.plan || 'trial').toUpperCase()}</span></td>
            <td><span class="status-dot ${pod.status}"></span> ${pod.status}</td>
            <td>
                <button class="btn btn-icon btn-ghost" title="Iniciar" ${pod.status === 'running' ? 'disabled' : ''} onclick="event.stopPropagation(); startPodById('${pod.id || pod.pod_id}')">
                    <span class="material-symbols-rounded">play_arrow</span>
                </button>
                <button class="btn btn-icon btn-ghost" title="Pausar" ${pod.status !== 'running' ? 'disabled' : ''} onclick="event.stopPropagation(); stopPodById('${pod.id || pod.pod_id}')">
                    <span class="material-symbols-rounded">pause</span>
                </button>
            </td>
        </tr>
    `).join('');
}

// ============================================
// CUSTOMERS LIST
// ============================================

function populateCustomersList(customers) {
    const container = document.getElementById('customersListModal');
    if (!customers || !customers.length) {
        container.innerHTML = '<p style="text-align: center; color: var(--color-muted); padding: 24px;">Sin clientes</p>';
        return;
    }

    container.innerHTML = customers.map(c => `
        <div class="activity-item" onclick="viewCustomerDetail('${c.email}')">
            <div class="user-avatar">${(c.name || c.email || 'U').charAt(0).toUpperCase()}</div>
            <div class="activity-content">
                <div class="activity-title">${c.name || c.email}</div>
                <div class="activity-time">${c.email} • ${(c.plan || 'trial').toUpperCase()}</div>
            </div>
            <span class="material-symbols-rounded" style="color: var(--color-muted);">chevron_right</span>
        </div>
    `).join('');
}

// ============================================
// ALERTS LIST
// ============================================

function populateAlertsList(alerts) {
    const container = document.getElementById('alertsList');
    if (!alerts || alerts.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: var(--color-muted); padding: 24px;"><span class="material-symbols-rounded">check_circle</span> No hay alertas</p>';
        return;
    }

    container.innerHTML = alerts.map(a => `
        <div class="activity-item">
            <div class="activity-icon" style="background: ${a.type === 'warning' ? '#FEF3C7' : '#DBEAFE'};">
                <span class="material-symbols-rounded" style="font-size: 18px; color: ${a.type === 'warning' ? 'var(--color-warning)' : 'var(--color-info)'};">
                    ${a.type === 'warning' ? 'warning' : 'info'}
                </span>
            </div>
            <div class="activity-content">
                <div class="activity-title">${a.message}</div>
                <div class="activity-time">${a.time}</div>
            </div>
        </div>
    `).join('');
}


// ============================================
// ACTIVITY FEED
// ============================================

let currentActivities = [];

function populateActivityFeed(activities) {
    currentActivities = activities || [];
    const container = document.getElementById('activityFeed');

    if (!activities || activities.length === 0) {
        container.innerHTML = `
            <div class="activity-empty" style="text-align: center; padding: 48px; color: var(--color-muted);">
                <div style="font-size: 3rem; opacity: 0.3; margin-bottom: 16px;">📭</div>
                <p>No hay actividad reciente</p>
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
            ${activities.slice(0, 6).map((a, index) => {
                const amount = a.details?.amount || 0;
                const email = a.details?.email || 'N/A';
                const podId = a.details?.pod_id || 'N/A';
                const status = a.details?.status || 'active';
                const isPayment = a.type === 'payment';

                const statusColors = {
                    'running': { bg: '#dcfce7', fg: '#22c55e' },
                    'active': { bg: '#dcfce7', fg: '#22c55e' },
                    'provisioning': { bg: '#dbeafe', fg: '#3b82f6' },
                    'pending': { bg: '#dbeafe', fg: '#3b82f6' },
                    'stopped': { bg: '#fee2e2', fg: '#ef4444' },
                    'paused': { bg: '#fef3c7', fg: '#f59e0b' },
                };
                const podColor = statusColors[status] || statusColors['active'];

                const icons = {
                    'payment': 'payments',
                    'pod_start': 'play_circle',
                    'pod_stop': 'stop_circle',
                    'new_customer': 'person_add',
                    'signup': 'how_to_reg',
                    'error': 'error',
                    'default': 'info'
                };
                const icon = icons[a.type] || a.icon || icons.default;

                return `
                    <div class="card" style="padding: 14px; cursor: pointer; border-left: 3px solid ${podColor.fg};" onclick="showActivityDetail(${index})">
                        <div style="display: flex; align-items: flex-start; gap: 12px;">
                            <div style="width: 40px; height: 40px; border-radius: 10px; background: ${podColor.bg}; color: ${podColor.fg}; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                                <span class="material-symbols-rounded">${icon}</span>
                            </div>
                            <div style="flex: 1; min-width: 0;">
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                                    <div>
                                        <div style="font-weight: 600; font-size: 0.95rem;">${isPayment ? `$${amount} USD` : a.title}</div>
                                        <div style="font-size: 0.75rem; color: var(--color-muted);">${a.time}</div>
                                    </div>
                                    <span style="font-size: 9px; flex-shrink: 0; padding: 2px 6px; border-radius: 4px; background: ${podColor.bg}; color: ${podColor.fg}; font-weight: 600;">${isPayment ? 'PAGADO' : status.toUpperCase()}</span>
                                </div>
                                <div style="font-size: 0.8rem; display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
                                    <div><span style="color: var(--color-muted);">Email:</span> <span style="font-weight: 500;">${email.length > 15 ? email.slice(0, 15) + '...' : email}</span></div>
                                    <div><span style="color: var(--color-muted);">Pod:</span> <span style="font-weight: 500; font-family: var(--font-mono); font-size: 0.75rem;">${podId !== 'N/A' ? podId.slice(4, 12) : 'N/A'}</span></div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

function showActivityDetail(index) {
    const activity = currentActivities[index];
    if (!activity) return;

    document.getElementById('activityDetailIcon').textContent = activity.icon || 'info';

    let detailsHtml = `
        <div style="margin-bottom: 16px;">
            <p style="font-size: 14px; color: var(--color-muted); margin-bottom: 8px;">Descripción</p>
            <p style="font-size: 16px;">${activity.description || activity.title}</p>
        </div>
        <div style="margin-bottom: 16px;">
            <p style="font-size: 14px; color: var(--color-muted); margin-bottom: 8px;">Tiempo</p>
            <p style="font-size: 16px;">${activity.time}</p>
        </div>
    `;

    if (activity.details) {
        detailsHtml += `<div style="background: var(--color-bg); padding: 16px; border-radius: 12px;">`;
        for (const [key, value] of Object.entries(activity.details)) {
            const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            const displayValue = Array.isArray(value) ? value.join(', ') : value;
            detailsHtml += `
                <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--color-border);">
                    <span style="color: var(--color-muted); font-size: 13px;">${label}</span>
                    <span style="font-size: 13px; font-family: var(--font-mono);">${displayValue}</span>
                </div>
            `;
        }
        detailsHtml += `</div>`;
    }

    document.getElementById('activityDetailBody').innerHTML = detailsHtml;

    const actionBtn = document.getElementById('activityDetailAction');
    if (activity.type === 'pod_start' || activity.type === 'pod_stop') {
        actionBtn.style.display = 'inline-flex';
        actionBtn.textContent = 'Ver Pod';
        actionBtn.onclick = () => { openFullModal('pods'); selectPod(activity.details?.pod_id); };
    } else if (activity.type === 'payment') {
        actionBtn.style.display = 'inline-flex';
        actionBtn.textContent = 'Ver Transacción';
        actionBtn.onclick = () => { openFullModal('billing'); };
    } else if (activity.type === 'new_customer' || activity.type === 'signup') {
        actionBtn.style.display = 'inline-flex';
        actionBtn.textContent = 'Ver Cliente';
        actionBtn.onclick = () => { openFullModal('customers'); selectCustomer(activity.details?.email); };
    } else {
        actionBtn.style.display = 'none';
    }

    openModal('activityDetailModal');
}

// ============================================
// CHARTS
// ============================================

let revenueChart = null;
let distributionChart = null;

function initCharts(data) {
    const monthlyRevenue = data?.revenue?.monthly || [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];

    const revenueCtx = document.getElementById('revenueChart')?.getContext('2d');
    if (revenueCtx) {
        if (revenueChart) revenueChart.destroy();
        revenueChart = new Chart(revenueCtx, {
            type: 'line',
            data: {
                labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
                datasets: [{
                    label: 'Ingresos',
                    data: monthlyRevenue,
                    borderColor: '#0A0A0A',
                    backgroundColor: 'rgba(10, 10, 10, 0.05)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: '#0A0A0A'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: '#737373', font: { size: 11 } } },
                    y: {
                        grid: { color: '#E5E5E5' },
                        ticks: { color: '#737373', font: { size: 11 }, callback: (v) => '$' + v }
                    }
                },
                interaction: { intersect: false, mode: 'index' }
            }
        });
    }

    const planCounts = data?.plans || { trial: 0, basic: 0, pro: 0, corp: 0, enterprise: 0 };

    const distCtx = document.getElementById('distributionChart')?.getContext('2d');
    if (distCtx) {
        if (distributionChart) distributionChart.destroy();
        distributionChart = new Chart(distCtx, {
            type: 'doughnut',
            data: {
                labels: ['Trial', 'Basic', 'Pro', 'Corp', 'Enterprise'],
                datasets: [{
                    data: [planCounts.trial || 0, planCounts.basic || 0, planCounts.pro || 0, planCounts.corp || 0, planCounts.enterprise || 0],
                    backgroundColor: ['#E5E5E5', '#93C5FD', '#22C55E', '#F59E0B', '#8B5CF6'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { padding: 16, usePointStyle: true, pointStyle: 'circle', font: { size: 12 } }
                    }
                },
                cutout: '70%'
            }
        });
    }
}


// ============================================
// FULL-SCREEN MODAL FUNCTIONS
// ============================================

let fullModalData = {
    pods: [],
    customers: [],
    transactions: []
};

function populateModalDataFromAPI(data) {
    if (!data) return;

    const pods = data.pods?.list || [];
    fullModalData.pods = pods.map(p => ({
        id: p.id || p.pod_id || 'N/A',
        email: p.email || 'N/A',
        name: p.name || p.email?.split('@')[0] || 'N/A',
        plan: p.plan || 'trial',
        status: p.status || 'pending',
        created_at: p.created_at || p.date || new Date().toISOString().split('T')[0],
        tokens_used: p.tokens_used || 0,
        token_limit: p.plan === 'corp' ? 50000 : p.plan === 'pro' ? 10000 : 5000,
        ip: p.ip || '0.0.0.0',
        region: p.region || 'us-east-1',
        ruc: p.ruc || 'N/A'
    }));

    const customers = data.customers?.recent || data.customers?.list || [];
    fullModalData.customers = customers.map(c => ({
        name: c.name || c.email?.split('@')[0] || 'N/A',
        email: c.email || 'N/A',
        ruc: c.ruc || 'N/A',
        plan: c.plan || 'trial',
        status: c.status || 'active',
        created_at: c.date || c.created_at || new Date().toISOString().split('T')[0],
        pod_id: c.pod_id || fullModalData.pods.find(p => p.email === c.email)?.id || 'N/A',
        total_paid: c.total_paid || 0
    }));

    fullModalData.transactions = fullModalData.pods.map((p, i) => ({
        id: `TXN-${p.id?.slice(-6) || i}`.toUpperCase(),
        date: p.created_at + ' ' + new Date().toLocaleTimeString('es-EC', { hour: '2-digit', minute: '2-digit' }),
        customer: fullModalData.customers.find(c => c.email === p.email)?.name || p.name,
        email: p.email,
        plan: p.plan,
        amount: p.plan === 'corp' ? 199.00 : p.plan === 'pro' ? 49.00 : p.plan === 'enterprise' ? 499.00 : 0,
        method: 'PayPal',
        status: 'completed',
        order_id: `ORD-${Date.now().toString().slice(-5)}${i}`,
        pod_id: p.id
    }));

    console.log('Modal data populated from API:', fullModalData);
}

function openFullModal(type) {
    const modalId = `${type}FullModal`;
    openModal(modalId);
    populateFullModalList(type);
}

function closeFullModal(type) {
    const modalId = `${type}FullModal`;
    closeModal(modalId);
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelector('[data-section="dashboard"]')?.classList.add('active');
}

function populateFullModalList(type) {
    if (type === 'pods') {
        const container = document.getElementById('podsListItems');
        if (!container) return;
        container.innerHTML = fullModalData.pods.map((pod, i) => `
            <div class="master-item ${i === 0 ? 'active' : ''}" onclick="selectPod('${pod.id}')">
                <span class="status-dot ${pod.status}"></span>
                <div style="flex:1;">
                    <div style="font-weight: 500;">${pod.id}</div>
                    <div style="font-size: 12px; color: var(--color-muted);">${pod.email}</div>
                </div>
                <span class="status-badge ${pod.plan === 'pro' ? 'running' : 'warning'}">${pod.plan.toUpperCase()}</span>
            </div>
        `).join('');
        if (fullModalData.pods.length > 0) selectPod(fullModalData.pods[0].id);
    }
    else if (type === 'customers') {
        const container = document.getElementById('customersListItems');
        if (!container) return;
        container.innerHTML = fullModalData.customers.map((c, i) => `
            <div class="master-item ${i === 0 ? 'active' : ''}" onclick="selectCustomer('${c.email}')">
                <div class="user-avatar" style="width:36px;height:36px;font-size:14px;">${c.name.charAt(0)}</div>
                <div style="flex:1;">
                    <div style="font-weight: 500;">${c.name}</div>
                    <div style="font-size: 12px; color: var(--color-muted);">${c.email}</div>
                </div>
                <span class="status-dot ${c.status === 'active' ? 'running' : 'stopped'}"></span>
            </div>
        `).join('');
        if (fullModalData.customers.length > 0) selectCustomer(fullModalData.customers[0].email);
    }
    else if (type === 'billing') {
        const container = document.getElementById('billingListItems');
        if (!container) return;
        container.innerHTML = fullModalData.transactions.map((tx, i) => `
            <div class="master-item ${i === 0 ? 'active' : ''}" onclick="selectTransaction('${tx.id}')">
                <div style="flex:1;">
                    <div style="font-weight: 500;">$${tx.amount.toFixed(2)}</div>
                    <div style="font-size: 12px; color: var(--color-muted);">${tx.customer}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size: 12px; font-family: var(--font-mono);">${tx.id}</div>
                    <div style="font-size: 11px; color: var(--color-muted);">${tx.date.split(' ')[0]}</div>
                </div>
            </div>
        `).join('');
        if (fullModalData.transactions.length > 0) selectTransaction(fullModalData.transactions[0].id);
        
        // Update billing KPIs
        const totalRevenue = fullModalData.transactions.reduce((sum, tx) => sum + tx.amount, 0);
        document.getElementById('billingTotalRevenue').textContent = `$${totalRevenue.toFixed(0)}`;
        document.getElementById('billingTxCount').textContent = fullModalData.transactions.length;
        document.getElementById('billingAvgOrder').textContent = `$${fullModalData.transactions.length ? (totalRevenue / fullModalData.transactions.length).toFixed(0) : 0}`;
    }
}

// ============================================
// POD LIFECYCLE ACTIONS
// ============================================

let selectedPodId = null;

function selectPod(podId) {
    selectedPodId = podId;
    const pod = fullModalData.pods.find(p => p.id === podId);
    if (!pod) return;

    document.querySelectorAll('#podsListItems .master-item').forEach(el => el.classList.remove('active'));
    event?.target?.closest('.master-item')?.classList.add('active');

    document.getElementById('detailPodId').textContent = pod.id;
    document.getElementById('detailPodRegion').textContent = pod.region || 'us-east-1';
    document.getElementById('detailPodIP').textContent = 'Cargando...';
    document.getElementById('detailPodCreated').textContent = pod.created_at?.split('T')[0] || 'N/A';
    document.getElementById('detailPodEmail').textContent = pod.email;
    document.getElementById('detailPodPlan').textContent = (pod.plan || 'trial').toUpperCase();
    document.getElementById('detailPodRUC').textContent = pod.ruc || 'N/A';

    document.getElementById('detailTokensUsed').textContent = (pod.tokens_used || 0).toLocaleString();
    document.getElementById('detailTokensLimit').textContent = (pod.token_limit || 5000).toLocaleString();
    document.getElementById('detailTokensProgress').style.width = `${((pod.tokens_used || 0) / (pod.token_limit || 5000)) * 100}%`;

    const badge = document.getElementById('podStatusBadge');
    badge.textContent = (pod.status || 'pending').toUpperCase();
    const statusClass = pod.status === 'running' || pod.status === 'active' ? 'running' :
        pod.status === 'destroyed' || pod.status === 'error' ? 'error' : 'warning';
    badge.className = `status-badge ${statusClass}`;

    const isRunning = pod.status === 'running' || pod.status === 'active' || pod.status === 'provisioning';
    document.getElementById('btnStartPod').style.display = isRunning ? 'none' : 'flex';
    document.getElementById('btnStopPod').style.display = isRunning ? 'flex' : 'none';
    document.getElementById('btnRestartPod').style.display = isRunning ? 'flex' : 'none';

    fetchPodMetrics(podId);
}

async function fetchPodMetrics(podId) {
    try {
        const resp = await fetch(`${API_BASE}/api/v2/admin/pod/${podId}/metrics`, {
            headers: getHeaders()
        });
        const data = await resp.json();

        if (data.success) {
            document.getElementById('detailPodIP').textContent = data.public_ip || 'Sin IP pública';
            const cpuEl = document.getElementById('detailPodCPU');
            const memEl = document.getElementById('detailPodMemory');
            const costEl = document.getElementById('detailPodCost');
            const uptimeEl = document.getElementById('detailPodUptime');

            if (cpuEl) cpuEl.textContent = `${data.cpu_utilization || 0}%`;
            if (memEl) memEl.textContent = `${data.memory_utilization || 0}%`;
            if (costEl) costEl.textContent = `$${data.cost_usd || '0.00'}`;
            if (uptimeEl) uptimeEl.textContent = `${data.uptime_hours || 0}h`;
        }
    } catch (e) {
        console.error('Error fetching pod metrics:', e);
        document.getElementById('detailPodIP').textContent = 'Error al cargar';
    }
}

async function startPod() {
    if (!selectedPodId) return alert('Selecciona un pod primero');

    const btn = document.getElementById('btnStartPod');
    btn.disabled = true;
    btn.innerHTML = '<span class="material-symbols-rounded">hourglass_empty</span> Iniciando...';

    try {
        const resp = await fetch(`${API_BASE}/api/v2/admin/pod/start`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ pod_id: selectedPodId })
        });

        const data = await resp.json();
        if (data.success) {
            alert(`Pod ${selectedPodId} iniciado correctamente`);
            document.getElementById('podStatusBadge').textContent = 'PROVISIONING';
            document.getElementById('podStatusBadge').className = 'status-badge warning';
            const dashData = await fetchDashboardData();
            if (dashData) populateModalDataFromAPI(dashData);
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    }

    btn.disabled = false;
    btn.innerHTML = '<span class="material-symbols-rounded">play_arrow</span> Iniciar';
}

async function stopPod() {
    if (!selectedPodId) return alert('Selecciona un pod primero');
    if (!confirm(`¿Detener pod ${selectedPodId}?`)) return;

    const btn = document.getElementById('btnStopPod');
    btn.disabled = true;
    btn.innerHTML = '<span class="material-symbols-rounded">hourglass_empty</span> Deteniendo...';

    try {
        const resp = await fetch(`${API_BASE}/api/v2/admin/pod/destroy`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ pod_id: selectedPodId })
        });

        const data = await resp.json();
        if (data.success) {
            alert(`Pod ${selectedPodId} detenido`);
            document.getElementById('podStatusBadge').textContent = 'STOPPED';
            document.getElementById('podStatusBadge').className = 'status-badge error';
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    }

    btn.disabled = false;
    btn.innerHTML = '<span class="material-symbols-rounded">pause</span> Detener';
}

async function restartPod() {
    if (!selectedPodId) return alert('Selecciona un pod primero');
    if (!confirm(`¿Reiniciar pod ${selectedPodId}?`)) return;
    await stopPod();
    await startPod();
}

async function destroyPod() {
    if (!selectedPodId) return alert('Selecciona un pod primero');
    if (!confirm(`¿DESTRUIR pod ${selectedPodId}? Esta acción es permanente.`)) return;

    const btn = document.getElementById('btnDestroyPod');
    btn.disabled = true;
    btn.innerHTML = '<span class="material-symbols-rounded">hourglass_empty</span> Destruyendo...';

    try {
        const resp = await fetch(`${API_BASE}/api/v2/admin/pod/destroy`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ pod_id: selectedPodId })
        });

        const data = await resp.json();
        if (data.success) {
            alert(`Pod ${selectedPodId} destruido permanentemente`);
            document.getElementById('podStatusBadge').textContent = 'DESTROYED';
            document.getElementById('podStatusBadge').className = 'status-badge error';
            const dashData = await fetchDashboardData();
            if (dashData) populateModalDataFromAPI(dashData);
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    }

    btn.disabled = false;
    btn.innerHTML = '<span class="material-symbols-rounded">delete_forever</span> Destruir';
}

function startPodById(podId) {
    selectedPodId = podId;
    startPod();
}

function stopPodById(podId) {
    selectedPodId = podId;
    stopPod();
}

function viewPodDetail(podId) {
    closeModal('podsModal');
    openFullModal('pods');
    setTimeout(() => selectPod(podId), 100);
}

function viewCustomerDetail(email) {
    closeModal('customersModal');
    openFullModal('customers');
    setTimeout(() => selectCustomer(email), 100);
}


// ============================================
// CUSTOMER SELECTION
// ============================================

function selectCustomer(email) {
    const c = fullModalData.customers.find(x => x.email === email);
    if (!c) return;

    document.querySelectorAll('#customersListItems .master-item').forEach(el => el.classList.remove('active'));
    event?.target?.closest('.master-item')?.classList.add('active');

    document.getElementById('customerAvatar').textContent = c.name.charAt(0);
    document.getElementById('detailCustomerName').textContent = c.name;
    document.getElementById('detailCustomerEmail').textContent = c.email;
    document.getElementById('detailCustomerRUC').textContent = c.ruc;
    document.getElementById('detailCustomerPlan').textContent = c.plan.toUpperCase();
    document.getElementById('detailCustomerCreated').textContent = c.created_at;
    document.getElementById('detailCustomerPodId').textContent = c.pod_id;
    document.getElementById('detailCustomerTotalPaid').textContent = `$${c.total_paid || 0}`;
}

// ============================================
// TRANSACTION SELECTION
// ============================================

function selectTransaction(txId) {
    const tx = fullModalData.transactions.find(t => t.id === txId);
    if (!tx) return;

    document.querySelectorAll('#billingListItems .master-item').forEach(el => el.classList.remove('active'));
    event?.target?.closest('.master-item')?.classList.add('active');

    document.getElementById('detailTxAmount').textContent = `$${tx.amount.toFixed(2)}`;
    document.getElementById('detailTxId').textContent = tx.id;
    document.getElementById('detailOrderId').textContent = tx.order_id;
    document.getElementById('detailTxDate').textContent = tx.date;
    document.getElementById('detailTxMethod').textContent = tx.method;
    document.getElementById('detailTxCustomer').textContent = tx.customer;
    document.getElementById('detailTxEmail').textContent = tx.email;
    document.getElementById('detailTxPlan').textContent = tx.plan.toUpperCase();
    document.getElementById('detailTxPodId').textContent = tx.pod_id;
}

// ============================================
// RESEND RECEIPT
// ============================================

async function resendReceipt() {
    const email = document.getElementById('detailTxEmail')?.textContent;
    const amount = document.getElementById('detailTxAmount')?.textContent;
    const txId = document.getElementById('detailTxId')?.textContent;

    if (!email || email === '--') {
        alert('Selecciona una transacción primero');
        return;
    }

    try {
        const resp = await fetch(`${API_BASE}/api/v2/admin/resend-receipt`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ email, amount, transaction_id: txId })
        });

        const data = await resp.json();
        if (data.success) {
            alert(`Recibo enviado a ${email}`);
        } else {
            alert(`Error: ${data.error || 'No se pudo enviar'}`);
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

// ============================================
// SETTINGS
// ============================================

function saveSettings() {
    alert('Configuración guardada');
    closeModal('settingsModal');
}

// ============================================
// INITIALIZATION
// ============================================

async function initDashboard() {
    if (!checkAuth()) return;

    const user = JSON.parse(localStorage.getItem('admin_user') || sessionStorage.getItem('admin_user') || '{}');
    if (user.email) {
        document.getElementById('userAvatar').textContent = user.email.charAt(0).toUpperCase();
        document.getElementById('userAvatar').title = user.name || user.email;
        document.getElementById('accountAvatar').textContent = user.email.charAt(0).toUpperCase();
        document.getElementById('accountName').textContent = user.name || 'Admin User';
        document.getElementById('accountEmail').textContent = user.email;
    }

    const data = await fetchDashboardData();
    if (data) {
        updateKPICards(data);
        populatePodsTable(data.pods?.list || []);
        populateCustomersList(data.customers?.recent || data.customers?.list || []);
        populateAlertsList(data.alerts?.items || []);
        populateActivityFeed(data.activity || []);
        initCharts(data);
        populateModalDataFromAPI(data);
        updateNavCounts(data);
        window.dashboardData = data;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    updateEnvUI();
    initDashboard();

    // Auto-refresh every 60 seconds
    setInterval(initDashboard, 60000);

    // Check for URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const sectionParam = urlParams.get('section');
    const podParam = urlParams.get('pod');

    if (sectionParam) {
        showSection(sectionParam);
    } else if (podParam) {
        showSection('pods');
        let attempts = 0;
        const maxAttempts = 50;
        const checkInterval = setInterval(() => {
            attempts++;
            if (typeof fullModalData !== 'undefined' && fullModalData.pods && fullModalData.pods.length > 0) {
                clearInterval(checkInterval);
                selectPod(podParam);
            } else if (attempts >= maxAttempts) {
                clearInterval(checkInterval);
                console.warn('Pod data not loaded after 5 seconds');
            }
        }, 100);
    }
});
