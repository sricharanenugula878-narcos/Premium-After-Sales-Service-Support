let currentOpenTicketId = null;

document.addEventListener('DOMContentLoaded', async () => {
    // Authenticate and protect route
    const user = await Auth.checkSession();
    if (!user) return;
    Auth.requireRole(['customer']);
    Auth.updateUserInfo();
    Auth.setupLogoutButton();

    // Load tab-specific data
    loadDashboardSummary();
    loadMyProducts();
    loadMyTickets();
    setupProductSelect();

    // Image upload handler
    const fileInput = document.getElementById('ticketImage');
    if (fileInput) {
        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const progress = document.getElementById('uploadProgress');
            const hiddenUrl = document.getElementById('uploadedImageUrl');
            
            progress.style.display = 'block';
            progress.textContent = 'Uploading support image...';

            const formData = new FormData();
            formData.append('image', file);

            try {
                const res = await fetch('/api/tickets/upload', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                });
                
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Upload failed');
                
                hiddenUrl.value = data.image_url;
                progress.style.display = 'block';
                progress.textContent = 'Upload successful! ✅';
                progress.style.color = 'var(--status-completed)';
            } catch (err) {
                console.error(err);
                progress.style.display = 'block';
                progress.textContent = 'Upload failed. ❌';
                progress.style.color = 'var(--status-rejected)';
            }
        });
    }

    // Submit Support Ticket Form
    const ticketForm = document.getElementById('newTicketForm');
    if (ticketForm) {
        ticketForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorDiv = document.getElementById('newTicketError');
            errorDiv.style.display = 'none';

            const product_id = document.getElementById('ticketProduct').value;
            const issue_type = document.getElementById('ticketIssueType').value;
            const priority = document.getElementById('ticketPriority').value;
            const description = document.getElementById('ticketDescription').value.trim();
            const image_url = document.getElementById('uploadedImageUrl').value;

            try {
                const res = await API.post('/tickets', {
                    product_id: product_id ? parseInt(product_id) : null,
                    issue_type,
                    priority,
                    description,
                    image_url
                });

                alert(`Ticket created successfully! ID: ${res.ticket_id}`);
                ticketForm.reset();
                document.getElementById('uploadProgress').style.display = 'none';
                document.getElementById('uploadedImageUrl').value = '';
                
                loadDashboardSummary();
                loadMyTickets();
                switchTab('tickets');
            } catch (err) {
                errorDiv.textContent = err.message;
                errorDiv.style.display = 'block';
            }
        });
    }

    // Submit Register Product Form
    const regProductForm = document.getElementById('regProductForm');
    if (regProductForm) {
        regProductForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorDiv = document.getElementById('regProductError');
            errorDiv.style.display = 'none';

            const product_name = document.getElementById('prodName').value.trim();
            const category = document.getElementById('prodCategory').value;
            const invoice_number = document.getElementById('prodInvoice').value.trim();
            const purchase_date = document.getElementById('prodPurchaseDate').value;
            const warranty_years = document.getElementById('prodWarrantyYears').value;

            try {
                await API.post('/products', {
                    product_name,
                    category,
                    invoice_number,
                    purchase_date,
                    warranty_years: parseInt(warranty_years)
                });

                alert('Product registered successfully!');
                regProductForm.reset();
                
                loadDashboardSummary();
                loadMyProducts();
                setupProductSelect();
                switchTab('products');
            } catch (err) {
                errorDiv.textContent = err.message;
                errorDiv.style.display = 'block';
            }
        });
    }

    // Add ticket comment
    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        commentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const textEl = document.getElementById('commentText');
            const comment = textEl.value.trim();
            if (!comment || !currentOpenTicketId) return;

            try {
                await API.post(`/tickets/${currentOpenTicketId}/comments`, { comment });
                textEl.value = '';
                viewTicketDetails(currentOpenTicketId); // refresh
            } catch (err) {
                alert('Failed to send comment: ' + err.message);
            }
        });
    }
});

// Tab Switch Logic
function switchTab(tabId) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
    // Deactivate all sidebar items
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(el => el.classList.remove('active'));
    
    // Show selected content
    const targetTab = document.getElementById(`tab-${tabId}`);
    if (targetTab) targetTab.style.display = 'block';

    // Set page title
    const titles = {
        'dashboard': 'Dashboard Overview',
        'tickets': 'My Support Tickets',
        'new-ticket': 'Raise a support ticket',
        'products': 'My Registered Furniture',
        'register-product': 'Register Purchased Furniture'
    };
    document.getElementById('pageTitle').textContent = titles[tabId] || 'Portal';

    // Find and highlight active link based on click event or direct tag
    const navItems = Array.from(document.querySelectorAll('.sidebar-nav .nav-item'));
    const indexMap = { 'dashboard': 0, 'tickets': 1, 'new-ticket': 2, 'products': 3, 'register-product': 4 };
    const activeIndex = indexMap[tabId];
    if (activeIndex !== undefined && navItems[activeIndex]) {
        navItems[activeIndex].classList.add('active');
    }

    // Hide detailed ticket view when switching tabs
    const detailEl = document.getElementById('ticket-detail-card');
    if (detailEl) detailEl.style.display = 'none';
}

// Load Overview metrics
async function loadDashboardSummary() {
    try {
        const data = await API.get('/dashboard/summary');
        
        // Metrics
        document.getElementById('metric-total-tickets').textContent = data.metrics.total_tickets;
        document.getElementById('metric-active-tickets').textContent = data.metrics.active_tickets;
        document.getElementById('metric-registered-products').textContent = data.metrics.products_registered;
        
        // Recent Tickets Table
        const recentTbody = document.getElementById('recent-tickets-table');
        recentTbody.innerHTML = '';
        if (data.recent_tickets.length === 0) {
            recentTbody.innerHTML = `<tr><td colspan="3" class="text-muted" style="text-align:center;">No tickets raised yet.</td></tr>`;
        } else {
            data.recent_tickets.forEach(t => {
                recentTbody.innerHTML += `
                    <tr>
                        <td><strong>${t.ticket_id}</strong></td>
                        <td>${t.issue_type}</td>
                        <td><span class="badge badge-${t.status.replace(/\s+/g, '').toLowerCase()}">${t.status}</span></td>
                    </tr>
                `;
            });
        }

        // Render Notifications
        const listEl = document.getElementById('notifications-list');
        listEl.innerHTML = '';
        if (data.notifications.length === 0) {
            listEl.innerHTML = `<div class="text-muted" style="padding:1rem; text-align:center;">No notifications.</div>`;
        } else {
            data.notifications.forEach(n => {
                const date = new Date(n.created_at).toLocaleDateString();
                listEl.innerHTML += `
                    <div class="notification-item ${n.is_read ? '' : 'unread'}">
                        <div style="font-weight:600; font-size:0.875rem;">${n.title}</div>
                        <div style="font-size:0.8125rem; color:var(--text-secondary); margin-top:0.125rem;">${n.message}</div>
                        <div style="font-size:0.75rem; color:#cbd5e1; margin-top:0.25rem; text-align:right;">${date}</div>
                    </div>
                `;
            });
        }
    } catch (err) {
        console.error(err);
    }
}

// Load Registered Products
async function loadMyProducts() {
    try {
        const products = await API.get('/products');
        const tbody = document.getElementById('products-table-body');
        tbody.innerHTML = '';

        if (products.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-muted" style="text-align:center;">No products registered yet.</td></tr>`;
            return;
        }

        products.forEach(p => {
            const today = new Date();
            const expDate = new Date(p.warranty_end_date);
            const isActive = expDate >= today;
            const badgeClass = isActive ? 'badge-active' : 'badge-expired';
            const badgeText = isActive ? 'Active Warranty' : 'Expired';

            tbody.innerHTML += `
                <tr>
                    <td><strong>${p.product_name}</strong></td>
                    <td>${p.category}</td>
                    <td>${p.invoice_number}</td>
                    <td>${p.purchase_date}</td>
                    <td>${p.warranty_start_date} to ${p.warranty_end_date}</td>
                    <td><span class="status-badge ${badgeClass}">${badgeText}</span></td>
                </tr>
            `;
        });
    } catch (err) {
        console.error(err);
    }
}

// Populate product select dropdown in raise ticket tab
async function setupProductSelect() {
    try {
        const products = await API.get('/products');
        const select = document.getElementById('ticketProduct');
        select.innerHTML = '<option value="">-- Choose Product --</option>';
        products.forEach(p => {
            select.innerHTML += `<option value="${p.id}">${p.product_name} (Invoice: ${p.invoice_number})</option>`;
        });
    } catch (err) {
        console.error(err);
    }
}

// Load My Tickets
async function loadMyTickets() {
    try {
        const tickets = await API.get('/tickets');
        const tbody = document.getElementById('tickets-table-body');
        tbody.innerHTML = '';

        if (tickets.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-muted" style="text-align:center;">No tickets raised yet.</td></tr>`;
            return;
        }

        tickets.forEach(t => {
            const created = new Date(t.created_at).toLocaleDateString();
            tbody.innerHTML += `
                <tr>
                    <td><strong>${t.ticket_id}</strong></td>
                    <td>${t.product_name || 'General Product'}</td>
                    <td>${t.issue_type}</td>
                    <td><span class="priority-${t.priority.toLowerCase()}">${t.priority}</span></td>
                    <td><span class="badge badge-${t.status.replace(/\s+/g, '').toLowerCase()}">${t.status}</span></td>
                    <td>${created}</td>
                    <td><button class="btn btn-secondary btn-sm" onclick="viewTicketDetails(${t.id})">Track Status</button></td>
                </tr>
            `;
        });
    } catch (err) {
        console.error(err);
    }
}

// View details + visual timeline progress
async function viewTicketDetails(id) {
    try {
        currentOpenTicketId = id;
        const t = await API.get(`/tickets/${id}`);
        
        document.getElementById('detail-ticket-id').textContent = `Tracking Ticket: ${t.ticket_id}`;
        document.getElementById('detail-product-name').textContent = t.product_name || 'General Product';
        document.getElementById('detail-issue-type').textContent = t.issue_type;
        document.getElementById('detail-priority').textContent = t.priority;
        document.getElementById('detail-description').textContent = t.description;
        document.getElementById('detail-resolution-notes').textContent = t.admin_notes || 'No resolution notes yet.';

        // Support Image display
        const imgContainer = document.getElementById('detail-image-container');
        if (t.image_url) {
            imgContainer.innerHTML = `<img src="${t.image_url}" alt="Support Ticket Image" style="max-width:100%; max-height:100%; object-fit:contain;">`;
        } else {
            imgContainer.innerHTML = `<span class="text-muted">No Image Uploaded</span>`;
        }

        // Timeline highlighting
        const statuses = ['New', 'Under Review', 'Assigned', 'In Progress', 'Resolved', 'Closed', 'Rejected'];
        // Reset timeline classes
        document.querySelectorAll('.timeline-step').forEach(step => {
            step.classList.remove('active', 'completed');
        });

        // Set current active status step
        // We translate complex status codes to timeline steps
        let currentStepId = 'step-New';
        if (t.status === 'Under Review') currentStepId = 'step-UnderReview';
        else if (t.status === 'Assigned') currentStepId = 'step-Assigned';
        else if (t.status === 'In Progress') currentStepId = 'step-InProgress';
        else if (t.status === 'Resolved' || t.status === 'Closed') currentStepId = 'step-Resolved';
        else if (t.status === 'Rejected') {
            // Adjust step label to show Rejected
            document.getElementById('step-UnderReview').querySelector('.step-label').textContent = 'Rejected';
            currentStepId = 'step-UnderReview';
        }

        const currentStep = document.getElementById(currentStepId);
        if (currentStep) {
            currentStep.classList.add('active');
            
            // Mark previous steps as completed
            let sibling = currentStep.previousElementSibling;
            while(sibling) {
                sibling.classList.add('completed');
                sibling = sibling.previousElementSibling;
            }
        }

        // Populate Comments
        const commentsList = document.getElementById('comments-list');
        commentsList.innerHTML = '';
        if (t.comments.length === 0) {
            commentsList.innerHTML = '<span class="text-muted" style="font-size:0.875rem;">No updates or comments yet.</span>';
        } else {
            t.comments.forEach(c => {
                const date = new Date(c.created_at).toLocaleString();
                const isUser = c.username === localStorage.getItem('user') ? 'user' : 'other';
                commentsList.innerHTML += `
                    <div style="margin-bottom: 0.75rem; border-bottom: 1px solid #eef2f6; padding-bottom: 0.5rem;">
                        <div class="d-flex justify-content-between" style="font-size: 0.75rem; color: var(--text-secondary);">
                            <strong>${c.username} (${c.role})</strong>
                            <span>${date}</span>
                        </div>
                        <div style="font-size: 0.875rem; margin-top: 0.25rem; color: #334155;">${c.comment}</div>
                    </div>
                `;
            });
        }

        // Show card
        document.getElementById('ticket-detail-card').style.display = 'block';
        document.getElementById('ticket-detail-card').scrollIntoView({ behavior: 'smooth' });

    } catch (err) {
        alert('Failed to load ticket details: ' + err.message);
    }
}

function closeTicketDetails() {
    document.getElementById('ticket-detail-card').style.display = 'none';
    currentOpenTicketId = null;
}
