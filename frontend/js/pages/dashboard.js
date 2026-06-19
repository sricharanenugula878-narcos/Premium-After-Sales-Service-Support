document.addEventListener('DOMContentLoaded', async () => {
    // Authenticate and protect route
    const user = await Auth.checkSession();
    if (!user) return;
    Auth.requireRole(['admin']);
    Auth.setupLogoutButton();
    Auth.updateUserInfo();

    loadDashboardData();
});

async function loadDashboardData() {
    try {
        const data = await API.get('/dashboard/summary');
        
        // Update Metrics
        document.getElementById('metric-total').textContent = data.metrics.total_tickets;
        document.getElementById('metric-pending').textContent = data.metrics.pending_tickets;
        document.getElementById('metric-inprogress').textContent = data.metrics.active_tickets; // Active tickets
        document.getElementById('metric-completed').textContent = data.metrics.resolved_tickets;

        // Populate Recent Claims/Tickets
        const tbody = document.querySelector('#recentClaimsTable tbody');
        tbody.innerHTML = '';
        data.recent_complaints.forEach(ticket => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><a href="claim-details.html?id=${ticket.id}"><strong>${ticket.ticket_id}</strong></a></td>
                <td>${ticket.customer_name}</td>
                <td>${ticket.issue_type}</td>
                <td><span class="badge badge-${ticket.status.replace(/\s+/g, '').toLowerCase()}">${ticket.status}</span></td>
                <td>${new Date(ticket.created_at).toLocaleDateString()}</td>
            `;
            tbody.appendChild(tr);
        });

        if (data.recent_complaints.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center">No recent tickets</td></tr>';
        }

        // Render Chart
        renderChart(data.metrics);
        
    } catch (error) {
        console.error(error);
        alert('Failed to load dashboard data');
    }
}

function renderChart(metrics) {
    const ctx = document.getElementById('statusChart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['New', 'Active/In-Progress', 'Resolved/Closed', 'Warranty Claims'],
            datasets: [{
                data: [
                    metrics.pending_tickets,
                    metrics.active_tickets - metrics.pending_tickets, // active minus new
                    metrics.resolved_tickets,
                    metrics.warranty_claims
                ],
                backgroundColor: [
                    '#3b82f6', // New
                    '#f59e0b', // In Progress
                    '#10b981', // Resolved
                    '#8b5cf6'  // Warranty Claims
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}
