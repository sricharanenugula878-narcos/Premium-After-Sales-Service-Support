document.addEventListener('DOMContentLoaded', async () => {
    const user = await Auth.checkSession();
    if (!user) return;
    Auth.requireRole(['admin']);
    Auth.setupLogoutButton();
    Auth.updateUserInfo();
    UI.setupModals();

    const urlParams = new URLSearchParams(window.location.search);
    const ticketId = urlParams.get('id');

    if (!ticketId) {
        window.location.href = 'claims.html';
        return;
    }

    loadTicketData(ticketId);

    // Update Status
    document.getElementById('statusForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const newStatus = document.getElementById('newStatus').value;
        const notes = document.getElementById('statusNotes').value.trim();

        try {
            await API.patch(`/tickets/${ticketId}/status`, { status: newStatus, notes: notes });
            UI.showToast('Status updated successfully');
            UI.closeModal('statusModal');
            document.getElementById('statusForm').reset();
            loadTicketData(ticketId);
        } catch (error) {
            UI.showToast(error.message, 'error');
        }
    });
});

async function loadTicketData(id) {
    try {
        const ticket = await API.get(`/tickets/${id}`);
        
        // Header
        document.getElementById('claimNumber').textContent = ticket.ticket_id;
        document.getElementById('claimStatus').innerHTML = `<span class="badge badge-${ticket.status.replace(/\s+/g, '').toLowerCase()}">${ticket.status}</span>`;
        document.getElementById('newStatus').value = ticket.status;

        // Product/Ticket Info
        document.getElementById('infoProduct').textContent = ticket.product_name || 'General Complaint';
        document.getElementById('infoType').textContent = ticket.category || 'N/A';
        document.getElementById('infoComplaint').textContent = ticket.issue_type;
        document.getElementById('infoPriority').textContent = ticket.priority;
        document.getElementById('infoPurchase').textContent = ticket.purchase_date ? UI.formatDate(ticket.purchase_date) : 'N/A';
        document.getElementById('infoWarranty').textContent = ticket.warranty_end_date ? UI.formatDate(ticket.warranty_end_date) : 'N/A';
        document.getElementById('infoDescription').textContent = ticket.description;

        // Customer Info
        document.getElementById('infoCustomerName').textContent = ticket.customer_name || 'N/A';
        document.getElementById('infoCustomerPhone').textContent = ticket.customer_phone || 'N/A';
        document.getElementById('infoCustomerAddress').textContent = `${ticket.customer_address || ''}, ${ticket.customer_city || ''}, ${ticket.customer_state || ''} - ${ticket.customer_pincode || ''}`;

        // Tech Info
        // Check if there is an active technician assigned
        let techName = 'Unassigned';
        if (ticket.assignments && ticket.assignments.length > 0) {
            const activeAssign = ticket.assignments[0];
            techName = `${activeAssign.technician_name} (${activeAssign.status})`;
        }
        document.getElementById('infoTechName').textContent = techName;

        // Visual image if uploaded
        const rightCol = document.querySelector('.page-content > div > div:nth-child(2)');
        if (rightCol) {
            // Check if image card already exists
            let imgCard = document.getElementById('admin-image-card');
            if (!imgCard) {
                imgCard = document.createElement('div');
                imgCard.id = 'admin-image-card';
                imgCard.className = 'card';
                imgCard.style.marginTop = '1.5rem';
                rightCol.prepend(imgCard);
            }
            if (ticket.image_url) {
                imgCard.innerHTML = `
                    <div class="card-header"><h3>Attachment Image</h3></div>
                    <div class="card-body" style="display:flex; align-items:center; justify-content:center; max-height:220px; overflow:hidden;">
                        <img src="${ticket.image_url}" alt="Ticket Image" style="max-width:100%; max-height:100%; object-fit:contain;">
                    </div>
                `;
            } else {
                imgCard.innerHTML = `
                    <div class="card-header"><h3>Attachment Image</h3></div>
                    <div class="card-body text-muted" style="text-align:center;">No attachments uploaded</div>
                `;
            }
        }

        // Timeline History
        const timeline = document.getElementById('auditTimeline');
        timeline.innerHTML = '';
        
        if (ticket.status_history && ticket.status_history.length > 0) {
            ticket.status_history.forEach(log => {
                const item = document.createElement('div');
                item.className = 'timeline-item';
                
                const date = new Date(log.created_at);
                
                item.innerHTML = `
                    <div style="font-size: 0.8125rem; color: var(--text-secondary); margin-bottom: 0.125rem;">
                        ${date.toLocaleDateString()} ${date.toLocaleTimeString()} - by ${log.changed_by}
                    </div>
                    <div style="font-weight: 600; font-size:0.875rem;">Status: ${log.status}</div>
                    <div style="font-size: 0.8125rem; margin-top: 0.125rem; color: #475569;">${log.notes || ''}</div>
                `;
                timeline.appendChild(item);
            });
        } else {
            timeline.innerHTML = '<div class="text-muted">No history available</div>';
        }

    } catch (error) {
        console.error(error);
        UI.showToast('Failed to load ticket details', 'error');
    }
}
