let currentOpenTicketId = null;

document.addEventListener('DOMContentLoaded', async () => {
    // Authenticate and protect route
    const user = await Auth.checkSession();
    if (!user) return;
    Auth.requireRole(['technician']);
    Auth.updateUserInfo();
    Auth.setupLogoutButton();

    // Load initial data
    loadDashboardSummary();
    loadMyJobs();

    // Image upload handler for resolution proof
    const fileInput = document.getElementById('resolveImage');
    if (fileInput) {
        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const progress = document.getElementById('uploadProgress');
            const hiddenUrl = document.getElementById('resolvedImageUrl');
            
            progress.style.display = 'block';
            progress.textContent = 'Uploading resolution proof...';

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
                progress.textContent = 'Proof uploaded! ✅';
                progress.style.color = 'var(--status-completed)';
                
                // Show in display container
                document.getElementById('job-image-container').innerHTML = `<img src="${data.image_url}" alt="Resolution Proof" style="max-width:100%; max-height:100%; object-fit:contain;">`;
            } catch (err) {
                console.error(err);
                progress.style.display = 'block';
                progress.textContent = 'Upload failed. ❌';
                progress.style.color = 'var(--status-rejected)';
            }
        });
    }

    // Submit Resolution form
    const resolveForm = document.getElementById('resolveJobForm');
    if (resolveForm) {
        resolveForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!currentOpenTicketId) return;

            const notes = document.getElementById('resolveNotes').value.trim();
            const image_url = document.getElementById('resolvedImageUrl').value;

            try {
                // 1. Submit resolution notes
                await API.patch(`/tickets/${currentOpenTicketId}/resolution`, { notes });
                
                // 2. Set status to Resolved
                await API.patch(`/tickets/${currentOpenTicketId}/status`, { 
                    status: 'Resolved',
                    notes: `Job marked Resolved by Technician. Resolution Notes: ${notes}. Proof Image: ${image_url}` 
                });

                alert('Ticket resolved and submitted successfully!');
                resolveForm.reset();
                document.getElementById('uploadProgress').style.display = 'none';
                document.getElementById('resolvedImageUrl').value = '';
                
                closeJobAction();
                loadDashboardSummary();
                loadMyJobs();
            } catch (err) {
                alert('Error resolving ticket: ' + err.message);
            }
        });
    }

    // Submit comment form
    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        commentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const textEl = document.getElementById('commentText');
            const comment = textEl.value.trim();
            const isInternal = document.getElementById('commentInternal').checked ? 1 : 0;
            if (!comment || !currentOpenTicketId) return;

            try {
                await API.post(`/tickets/${currentOpenTicketId}/comments`, { 
                    comment,
                    is_internal: isInternal
                });
                textEl.value = '';
                viewJobAction(currentOpenTicketId); // refresh details
            } catch (err) {
                alert('Failed to send comment: ' + err.message);
            }
        });
    }
});

// Tab Switch
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(el => el.classList.remove('active'));
    
    const targetTab = document.getElementById(`tab-${tabId}`);
    if (targetTab) targetTab.style.display = 'block';

    const titles = {
        'overview': 'Work Overview',
        'jobs': 'Assigned Jobs'
    };
    document.getElementById('pageTitle').textContent = titles[tabId] || 'Technician Portal';

    const navItems = Array.from(document.querySelectorAll('.sidebar-nav .nav-item'));
    if (tabId === 'overview' && navItems[0]) navItems[0].classList.add('active');
    if (tabId === 'jobs' && navItems[1]) navItems[1].classList.add('active');

    // Close progress card
    closeJobAction();
}

// Load summary metrics
async function loadDashboardSummary() {
    try {
        const data = await API.get('/dashboard/summary');
        
        // Metrics
        document.getElementById('metric-active-jobs').textContent = data.metrics.assigned_tickets;
        document.getElementById('metric-pending-offers').textContent = data.metrics.pending_assignments;
        document.getElementById('metric-completed-jobs').textContent = data.metrics.completed_tickets;
        
        // Recent jobs table
        const recentTbody = document.getElementById('recent-jobs-table');
        recentTbody.innerHTML = '';
        if (data.recent_jobs.length === 0) {
            recentTbody.innerHTML = `<tr><td colspan="5" class="text-muted" style="text-align:center;">No jobs assigned.</td></tr>`;
        } else {
            data.recent_jobs.forEach(j => {
                recentTbody.innerHTML += `
                    <tr>
                        <td><strong>${j.ticket_id}</strong></td>
                        <td>${j.issue_type}</td>
                        <td>${j.customer_name}</td>
                        <td><span class="badge badge-${j.status.replace(/\s+/g, '').toLowerCase()}">${j.status}</span></td>
                        <td><button class="btn btn-secondary btn-sm" onclick="switchTab('jobs'); viewJobAction(${j.id});">Manage</button></td>
                    </tr>
                `;
            });
        }
    } catch (err) {
        console.error(err);
    }
}

// Load Task List
async function loadMyJobs() {
    try {
        const tickets = await API.get('/tickets');
        const tbody = document.getElementById('jobs-table-body');
        tbody.innerHTML = '';

        if (tickets.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-muted" style="text-align:center;">No assigned tasks found.</td></tr>`;
            return;
        }

        tickets.forEach(t => {
            // Find active assignment status
            let assignStatus = 'Assigned';
            if (t.assignments && t.assignments.length > 0) {
                assignStatus = t.assignments[0].status;
            }

            tbody.innerHTML += `
                <tr>
                    <td><strong>${t.ticket_id}</strong></td>
                    <td>${t.product_name || 'General Product'}</td>
                    <td>${t.customer_name}</td>
                    <td><span class="priority-${t.priority.toLowerCase()}">${t.priority}</span></td>
                    <td><span class="status-badge" style="background:#f1f5f9; color:#475569;">${assignStatus}</span></td>
                    <td><span class="badge badge-${t.status.replace(/\s+/g, '').toLowerCase()}">${t.status}</span></td>
                    <td><button class="btn btn-secondary btn-sm" onclick="viewJobAction(${t.id})">Open Panel</button></td>
                </tr>
            `;
        });
    } catch (err) {
        console.error(err);
    }
}

// View details and manage task actions
async function viewJobAction(id) {
    try {
        currentOpenTicketId = id;
        const t = await API.get(`/tickets/${id}`);
        
        document.getElementById('action-ticket-id').textContent = `Manage Job Details: ${t.ticket_id}`;
        document.getElementById('job-client-name').textContent = t.customer_name;
        document.getElementById('job-client-phone').textContent = t.customer_phone;
        document.getElementById('job-client-address').textContent = `${t.customer_address}, ${t.customer_city}, ${t.customer_state} - ${t.customer_pincode}`;
        document.getElementById('job-product-name').textContent = t.product_name || 'General Product';
        document.getElementById('job-description').textContent = t.description;
        
        const badge = document.getElementById('job-status-badge');
        badge.textContent = t.status;
        badge.className = `badge badge-${t.status.replace(/\s+/g, '').toLowerCase()}`;

        // Reset display areas
        document.getElementById('offer-actions').style.display = 'none';
        document.getElementById('work-actions').style.display = 'none';
        document.getElementById('resolve-form-area').style.display = 'none';
        
        // Show support image if uploaded by customer
        const imgContainer = document.getElementById('job-image-container');
        if (t.image_url) {
            imgContainer.innerHTML = `<img src="${t.image_url}" alt="Support Ticket Image" style="max-width:100%; max-height:100%; object-fit:contain;">`;
        } else {
            imgContainer.innerHTML = `<span class="text-muted">No Image Uploaded</span>`;
        }

        // Get assignment status
        let activeAssignment = null;
        if (t.assignments && t.assignments.length > 0) {
            activeAssignment = t.assignments[0];
        }

        if (activeAssignment && activeAssignment.status === 'Pending') {
            document.getElementById('offer-actions').style.display = 'block';
        } else {
            document.getElementById('work-actions').style.display = 'block';
            
            // Adjust buttons based on current state
            const startBtn = document.getElementById('btn-start-job');
            if (t.status === 'In Progress') {
                startBtn.disabled = true;
                startBtn.textContent = 'Started';
            } else {
                startBtn.disabled = false;
                startBtn.textContent = 'Start Job';
            }
        }

        // Populate Comments
        const commentsList = document.getElementById('comments-list');
        commentsList.innerHTML = '';
        if (t.comments.length === 0) {
            commentsList.innerHTML = '<span class="text-muted" style="font-size:0.875rem;">No notes or comments yet.</span>';
        } else {
            t.comments.forEach(c => {
                const date = new Date(c.created_at).toLocaleString();
                commentsList.innerHTML += `
                    <div style="margin-bottom: 0.5rem; border-bottom: 1px solid #eef2f6; padding-bottom: 0.25rem;">
                        <div class="d-flex justify-content-between" style="font-size: 0.75rem; color: var(--text-secondary);">
                            <strong>${c.username} (${c.role}) ${c.is_internal ? '🔒 [INTERNAL]' : ''}</strong>
                            <span>${date}</span>
                        </div>
                        <div style="font-size: 0.8125rem; margin-top: 0.125rem; color: #334155;">${c.comment}</div>
                    </div>
                `;
            });
        }

        document.getElementById('job-action-card').style.display = 'block';
        document.getElementById('job-action-card').scrollIntoView({ behavior: 'smooth' });

    } catch (err) {
        alert('Failed to load job details: ' + err.message);
    }
}

// Accept or decline assignment
async function updateAssignment(status, notes) {
    if (!currentOpenTicketId) return;
    try {
        if (status === 'In Progress') {
            // Accept the offer
            await API.patch(`/tickets/${currentOpenTicketId}/status`, { 
                status: 'In Progress', 
                notes: 'Technician accepted job offer and started work.'
            });
            alert('Job accepted!');
        } else {
            // Decline the offer
            await API.post(`/tickets/${currentOpenTicketId}/comments`, {
                comment: 'Job assignment declined by technician.',
                is_internal: 1
            });
            alert('Job declined!');
        }
        
        closeJobAction();
        loadDashboardSummary();
        loadMyJobs();
    } catch (err) {
        alert('Failed to update assignment: ' + err.message);
    }
}

// Start job
async function updateWorkStatus(status, notes) {
    if (!currentOpenTicketId) return;
    try {
        await API.patch(`/tickets/${currentOpenTicketId}/status`, { status, notes });
        alert('Job started!');
        viewJobAction(currentOpenTicketId);
        loadDashboardSummary();
        loadMyJobs();
    } catch (err) {
        alert('Error updating status: ' + err.message);
    }
}

// Show resolve form
function showResolveForm() {
    document.getElementById('work-actions').style.display = 'none';
    document.getElementById('resolve-form-area').style.display = 'block';
}

function closeJobAction() {
    document.getElementById('job-action-card').style.display = 'none';
    currentOpenTicketId = null;
}
