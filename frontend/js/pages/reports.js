document.addEventListener('DOMContentLoaded', async () => {
    const user = await Auth.checkSession();
    if (!user) return;
    Auth.requireRole(['admin']);
    Auth.setupLogoutButton();
    Auth.updateUserInfo();

    loadReports();
});

async function loadReports() {
    try {
        const data = await API.get('/reports/summary');
        
        renderMonthlyChart(data.monthly);
        renderStatusChart(data.status);
        renderTechChart(data.technicians);

    } catch (error) {
        console.error(error);
        alert('Failed to load reports summary');
    }
}

function renderMonthlyChart(data) {
    const ctx = document.getElementById('monthlyChart').getContext('2d');
    const labels = data.map(d => d.label);
    const values = data.map(d => d.value);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Tickets Registered',
                data: values,
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1 } }
            }
        }
    });
}

function renderStatusChart(data) {
    const ctx = document.getElementById('statusChart').getContext('2d');
    const labels = data.map(d => d.label);
    const values = data.map(d => d.value);
    
    const colors = labels.map(status => {
        if (status === 'New') return '#3b82f6';
        if (status === 'Under Review') return '#8b5cf6';
        if (status === 'Assigned') return '#c084fc';
        if (status === 'In Progress') return '#f59e0b';
        if (status === 'Resolved') return '#10b981';
        if (status === 'Closed') return '#059669';
        if (status === 'Rejected') return '#ef4444';
        return '#cbd5e1';
    });

    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

function renderTechChart(data) {
    const ctx = document.getElementById('techChart').getContext('2d');
    const labels = data.map(d => d.label);
    const values = data.map(d => d.value);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Completed Jobs',
                data: values,
                backgroundColor: '#10b981'
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1 } }
            }
        }
    });
}

// Global Export Function
async function exportCSV() {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch('/api/reports/export', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) throw new Error('Export failed');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `svs_tickets_report_${new Date().toISOString().slice(0,10)}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        alert('Failed to export CSV: ' + error.message);
    }
}
