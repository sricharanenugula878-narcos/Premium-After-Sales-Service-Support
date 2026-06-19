import os
import jwt
from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename
from utils.db import execute_query
from utils.auth_middleware import jwt_required, role_required
from datetime import datetime

tickets_bp = Blueprint('tickets', __name__)

@tickets_bp.route('/upload', methods=['POST'])
@jwt_required
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
        
    filename = secure_filename(f"{datetime.utcnow().timestamp()}_{file.filename}")
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    
    return jsonify({"image_url": f"/uploads/{filename}"}), 200

@tickets_bp.route('', methods=['GET'])
@jwt_required
def get_tickets():
    # Fetch parameters for filter & search
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()
    priority_filter = request.args.get('priority', '').strip()
    
    params = []
    
    if g.role == 'customer':
        # Retrieve customer ref_id
        cust = execute_query("SELECT id FROM customers WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if not cust:
            return jsonify([]), 200
        query = """
            SELECT t.*, p.product_name, p.invoice_number, p.warranty_end_date 
            FROM tickets t
            LEFT JOIN products p ON t.product_id = p.id
            WHERE t.customer_id = %s
        """
        params.append(cust['id'])
    elif g.role == 'technician':
        # Retrieve tech ref_id
        tech = execute_query("SELECT id FROM technicians WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if not tech:
            return jsonify([]), 200
        query = """
            SELECT t.*, p.product_name, cust.full_name as customer_name, cust.phone as customer_phone
            FROM tickets t
            JOIN assignments a ON t.id = a.ticket_id
            LEFT JOIN products p ON t.product_id = p.id
            JOIN customers cust ON t.customer_id = cust.id
            WHERE a.technician_id = %s
        """
        params.append(tech['id'])
    else: # admin
        query = """
            SELECT t.*, p.product_name, cust.full_name as customer_name, cust.customer_code,
                   tech.name as technician_name
            FROM tickets t
            LEFT JOIN products p ON t.product_id = p.id
            JOIN customers cust ON t.customer_id = cust.id
            LEFT JOIN assignments a ON t.id = a.ticket_id AND a.status = 'Accepted'
            LEFT JOIN technicians tech ON a.technician_id = tech.id
            WHERE 1=1
        """
    
    # Filter/Search implementation (admins/techs)
    if search:
        query += " AND (t.ticket_id LIKE %s OR t.description LIKE %s OR cust.full_name LIKE %s)"
        search_val = f"%{search}%"
        params.extend([search_val, search_val, search_val])
        
    if status_filter:
        query += " AND t.status = %s"
        params.append(status_filter)
        
    if priority_filter:
        query += " AND t.priority = %s"
        params.append(priority_filter)
        
    query += " ORDER BY t.created_at DESC"
    tickets = execute_query(query, tuple(params), fetch_all=True)
    return jsonify(tickets)

@tickets_bp.route('', methods=['POST'])
@jwt_required
def create_ticket():
    data = request.json or {}
    product_id = data.get('product_id')
    product_name = data.get('product_name')
    issue_type = data.get('issue_type') or data.get('complaint_type') # Support both naming styles
    description = data.get('description')
    priority = data.get('priority', 'Medium')
    image_url = data.get('image_url')
    
    if not all([issue_type, description]):
        return jsonify({"error": "Required fields: issue_type, description"}), 400
        
    # Get Customer reference ID
    if g.role == 'customer':
        cust = execute_query("SELECT id, full_name FROM customers WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if not cust:
            return jsonify({"error": "Customer profile not found"}), 404
        customer_id = cust['id']
        customer_name = cust['full_name']
    else:
        customer_id = data.get('customer_id')
        if not customer_id:
            return jsonify({"error": "customer_id required"}), 400
        cust_profile = execute_query("SELECT full_name FROM customers WHERE id = %s", (customer_id,), fetch_one=True)
        customer_name = cust_profile['full_name'] if cust_profile else "Customer"

    # Auto-register product for admin panel
    if not product_id and product_name:
        category = data.get('furniture_type', 'Other')
        purchase_date = data.get('purchase_date') or datetime.utcnow().strftime("%Y-%m-%d")
        warranty_expiry_date = data.get('warranty_expiry_date') or purchase_date
        
        product_id = execute_query(
            """INSERT INTO products (customer_id, product_name, category, purchase_date, invoice_number, warranty_start_date, warranty_end_date)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (customer_id, product_name, category, purchase_date, 'ADMIN-ADD', purchase_date, warranty_expiry_date),
            commit=True
        )

    # Ticket sequence generation
    current_year = datetime.utcnow().year
    count_res = execute_query("SELECT COUNT(*) as count FROM tickets WHERE ticket_id LIKE %s", (f"TKT-{current_year}-%",), fetch_one=True)
    count = count_res['count'] if count_res else 0
    ticket_id = f"TKT-{current_year}-{count + 1:04d}"

    # Warranty claim automated rules engine
    initial_status = 'New'
    admin_notes = None
    
    if product_id:
        product = execute_query("SELECT warranty_end_date, product_name FROM products WHERE id = %s", (product_id,), fetch_one=True)
        if product:
            expiry_str = product['warranty_end_date']
            try:
                expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                today = datetime.utcnow().date()
                if expiry < today:
                    # RULE: IF warranty expired -> Auto Reject
                    initial_status = 'Rejected'
                    admin_notes = "Auto-rejected: Product warranty expired on " + expiry_str
                else:
                    # RULE: IF warranty active -> Move to Review (or New)
                    initial_status = 'Under Review'
                    admin_notes = "Warranty Active (Expires: " + expiry_str + "). Under review."
            except Exception as e:
                pass

    # If technician is assigned immediately, status becomes 'Assigned'
    technician_id = data.get('technician_id')
    if technician_id and initial_status != 'Rejected':
        initial_status = 'Assigned'

    query = """
    INSERT INTO tickets (ticket_id, customer_id, product_id, issue_type, description, priority, status, image_url, admin_notes)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (ticket_id, customer_id, product_id, issue_type, description, priority, initial_status, image_url, admin_notes)
    new_id = execute_query(query, params, commit=True)
    
    if isinstance(new_id, dict) and 'error' in new_id:
        return jsonify({"error": "Failed to create support ticket", "details": new_id['error']}), 500

    # Insert Warranty Claim entry if applicable
    if product_id:
        claim_status = 'Approved' if initial_status in ('Under Review', 'Assigned') else 'Rejected' if initial_status == 'Rejected' else 'Pending'
        reject_reason = admin_notes if claim_status == 'Rejected' else None
        execute_query(
            """INSERT INTO warranty_claims (ticket_id, product_id, claim_status, approved_by, reject_reason, processed_at) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (new_id, product_id, claim_status, 'System' if claim_status != 'Pending' else None, reject_reason, datetime.utcnow() if claim_status != 'Pending' else None),
            commit=True
        )

    # Insert Technician assignment if assigned immediately
    if technician_id and initial_status == 'Assigned':
        execute_query(
            "INSERT INTO assignments (ticket_id, technician_id, status) VALUES (%s, %s, 'Pending')",
            (new_id, technician_id), commit=True
        )

    # Log in audit logs and status history
    execute_query("INSERT INTO audit_logs (user_id, action, description) VALUES (%s, %s, %s)",
                  (g.user_id, 'TICKET_CREATE', f"Ticket {ticket_id} created with initial status {initial_status}"), commit=True)
    execute_query("INSERT INTO status_history (ticket_id, status, changed_by, notes) VALUES (%s, %s, %s, %s)",
                  (new_id, initial_status, g.username, "Ticket raised via portal" if not admin_notes else admin_notes), commit=True)

    # Send notification to user
    notify_user_id = g.user_id if g.role == 'customer' else execute_query("SELECT user_id FROM customers WHERE id = %s", (customer_id,), fetch_one=True)['user_id']
    if notify_user_id:
        execute_query("INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)",
                      (notify_user_id, "Ticket Raised Successfully", f"Ticket {ticket_id} has been registered and is '{initial_status}'."), commit=True)

    return jsonify({
        "message": "Ticket created successfully",
        "id": new_id,
        "ticket_id": ticket_id,
        "status": initial_status,
        "admin_notes": admin_notes
    }), 201

@tickets_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_ticket(id):
    query = """
        SELECT t.*, p.product_name, p.invoice_number, p.warranty_start_date, p.warranty_end_date,
               c.full_name as customer_name, c.phone as customer_phone, c.email as customer_email,
               c.address as customer_address, c.city as customer_city, c.state as customer_state, c.pincode as customer_pincode
        FROM tickets t
        LEFT JOIN products p ON t.product_id = p.id
        JOIN customers c ON t.customer_id = c.id
        WHERE t.id = %s
    """
    ticket = execute_query(query, (id,), fetch_one=True)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
        
    # Check access for customer
    if g.role == 'customer':
        cust = execute_query("SELECT id FROM customers WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if not cust or ticket['customer_id'] != cust['id']:
            return jsonify({"error": "Access forbidden"}), 403

    # Grab comments, assignments, status history
    comments = execute_query(
        """SELECT tc.*, u.username, r.name as role 
           FROM ticket_comments tc
           JOIN users u ON tc.user_id = u.id
           JOIN roles r ON u.role_id = r.id
           WHERE tc.ticket_id = %s 
           ORDER BY tc.created_at ASC""",
        (id,), fetch_all=True
    )
    
    # Hide internal comments from customers
    if g.role == 'customer':
        comments = [c for c in comments if not c['is_internal']]

    status_history = execute_query("SELECT * FROM status_history WHERE ticket_id = %s ORDER BY created_at DESC", (id,), fetch_all=True)
    
    assignments = execute_query(
        """SELECT a.*, tech.name as technician_name, tech.phone as technician_phone 
           FROM assignments a
           JOIN technicians tech ON a.technician_id = tech.id
           WHERE a.ticket_id = %s ORDER BY a.created_at DESC""",
        (id,), fetch_all=True
    )

    ticket['comments'] = comments
    ticket['status_history'] = status_history
    ticket['assignments'] = assignments

    return jsonify(ticket)

@tickets_bp.route('/<int:id>/status', methods=['PATCH'])
@jwt_required
def update_status(id):
    data = request.json or {}
    new_status = data.get('status')
    notes = data.get('notes', '')
    
    if not new_status:
        return jsonify({"error": "Status parameter is required"}), 400
        
    # Fetch current ticket
    ticket = execute_query("SELECT ticket_id, customer_id, status FROM tickets WHERE id = %s", (id,), fetch_one=True)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404

    # Authorization Check: Technicians can only change status for their assigned jobs to accepted/completed
    if g.role == 'technician':
        tech = execute_query("SELECT id FROM technicians WHERE user_id = %s", (g.user_id,), fetch_one=True)
        assigned = execute_query("SELECT id FROM assignments WHERE ticket_id = %s AND technician_id = %s", (id, tech['id']), fetch_one=True)
        if not assigned:
            return jsonify({"error": "Unauthorized to update this ticket status"}), 403
            
    execute_query("UPDATE tickets SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (new_status, id), commit=True)
    
    # Update assignments status if technician accept/complete
    if g.role == 'technician' and new_status == 'In Progress':
        tech = execute_query("SELECT id FROM technicians WHERE user_id = %s", (g.user_id,), fetch_one=True)
        execute_query("UPDATE assignments SET status = 'Accepted', updated_at = CURRENT_TIMESTAMP WHERE ticket_id = %s AND technician_id = %s", (id, tech['id']), commit=True)
    elif g.role == 'technician' and new_status == 'Resolved':
        tech = execute_query("SELECT id FROM technicians WHERE user_id = %s", (g.user_id,), fetch_one=True)
        execute_query("UPDATE assignments SET status = 'Completed', updated_at = CURRENT_TIMESTAMP WHERE ticket_id = %s AND technician_id = %s", (id, tech['id']), commit=True)
        
    # Record status history and audit log
    execute_query("INSERT INTO status_history (ticket_id, status, changed_by, notes) VALUES (%s, %s, %s, %s)",
                  (id, new_status, g.username, notes or f"Status changed from {ticket['status']} to {new_status}"), commit=True)
    execute_query("INSERT INTO audit_logs (user_id, action, description) VALUES (%s, %s, %s)",
                  (g.user_id, 'STATUS_UPDATE', f"Ticket {ticket['ticket_id']} status updated to {new_status}"), commit=True)

    # Notify customer of status update
    cust_user = execute_query("SELECT user_id FROM customers WHERE id = %s", (ticket['customer_id'],), fetch_one=True)
    if cust_user:
        execute_query("INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)",
                      (cust_user['user_id'], "Ticket Status Updated", f"Your ticket {ticket['ticket_id']} status has been changed to '{new_status}'."), commit=True)

    return jsonify({"message": "Status updated successfully", "status": new_status})

@tickets_bp.route('/<int:id>/assign', methods=['POST'])
@jwt_required
@role_required(['admin'])
def assign_technician(id):
    data = request.json or {}
    technician_id = data.get('technician_id')
    notes = data.get('notes', '')
    
    if not technician_id:
        return jsonify({"error": "technician_id required"}), 400
        
    ticket = execute_query("SELECT ticket_id, customer_id FROM tickets WHERE id = %s", (id,), fetch_one=True)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
        
    # Update assignments (close old assignments, create new)
    execute_query("UPDATE assignments SET status = 'Declined' WHERE ticket_id = %s AND status = 'Pending'", (id,), commit=True)
    
    assign_id = execute_query(
        "INSERT INTO assignments (ticket_id, technician_id, status, notes) VALUES (%s, %s, 'Pending', %s)",
        (id, technician_id, notes),
        commit=True
    )
    
    # Update ticket status to Assigned
    execute_query("UPDATE tickets SET status = 'Assigned', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (id,), commit=True)
    
    # Record history
    execute_query("INSERT INTO status_history (ticket_id, status, changed_by, notes) VALUES (%s, %s, %s, %s)",
                  (id, 'Assigned', g.username, f"Assigned to technician ID {technician_id}. Notes: {notes}"), commit=True)
    execute_query("INSERT INTO audit_logs (user_id, action, description) VALUES (%s, %s, %s)",
                  (g.user_id, 'TICKET_ASSIGN', f"Ticket {ticket['ticket_id']} assigned to technician {technician_id}"), commit=True)
                  
    # Notify technician and customer
    tech_user = execute_query("SELECT user_id FROM technicians WHERE id = %s", (technician_id,), fetch_one=True)
    if tech_user:
        execute_query("INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)",
                      (tech_user['user_id'], "New Job Assigned", f"You have been assigned a new job: {ticket['ticket_id']}"), commit=True)
                      
    cust_user = execute_query("SELECT user_id FROM customers WHERE id = %s", (ticket['customer_id'],), fetch_one=True)
    if cust_user:
        execute_query("INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)",
                      (cust_user['user_id'], "Technician Assigned", f"A technician has been assigned to your ticket {ticket['ticket_id']}."), commit=True)

    return jsonify({"message": "Technician assigned successfully", "assignment_id": assign_id})

@tickets_bp.route('/<int:id>/comments', methods=['POST'])
@jwt_required
def add_comment(id):
    data = request.json or {}
    comment = data.get('comment')
    is_internal = data.get('is_internal', 0)
    
    if not comment:
        return jsonify({"error": "Comment content cannot be empty"}), 400
        
    ticket = execute_query("SELECT ticket_id, customer_id FROM tickets WHERE id = %s", (id,), fetch_one=True)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
        
    # Check customer access
    if g.role == 'customer':
        is_internal = 0 # Customers cannot make internal notes
        cust = execute_query("SELECT id FROM customers WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if not cust or ticket['customer_id'] != cust['id']:
            return jsonify({"error": "Access forbidden"}), 403

    comment_id = execute_query(
        "INSERT INTO ticket_comments (ticket_id, user_id, comment, is_internal) VALUES (%s, %s, %s, %s)",
        (id, g.user_id, comment, is_internal),
        commit=True
    )
    
    # Notify customer if comment is public and made by admin/tech
    if g.role != 'customer' and not is_internal:
        cust_user = execute_query("SELECT user_id FROM customers WHERE id = %s", (ticket['customer_id'],), fetch_one=True)
        if cust_user:
            execute_query("INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)",
                          (cust_user['user_id'], "New Comment on Ticket", f"A comment was added to your ticket {ticket['ticket_id']}: '{comment[:40]}...'"), commit=True)
                          
    return jsonify({"message": "Comment added successfully", "comment_id": comment_id}), 201

@tickets_bp.route('/<int:id>/resolution', methods=['PATCH'])
@jwt_required
@role_required(['admin'])
def update_resolution_notes(id):
    data = request.json or {}
    notes = data.get('notes', '')
    
    ticket = execute_query("SELECT ticket_id FROM tickets WHERE id = %s", (id,), fetch_one=True)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
        
    execute_query("UPDATE tickets SET admin_notes = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (notes, id), commit=True)
    execute_query("INSERT INTO audit_logs (user_id, action, description) VALUES (%s, %s, %s)",
                  (g.user_id, 'TICKET_RESOLUTION_NOTE', f"Updated resolution notes for ticket {ticket['ticket_id']}"), commit=True)
                  
    return jsonify({"message": "Resolution notes updated successfully"})

@tickets_bp.route('/<int:id>', methods=['PUT'])
@jwt_required
@role_required(['admin'])
def update_ticket(id):
    data = request.json or {}
    product_name = data.get('product_name')
    category = data.get('furniture_type') # Map from HTML form
    purchase_date = data.get('purchase_date')
    warranty_end_date = data.get('warranty_expiry_date')
    
    ticket = execute_query("SELECT customer_id, product_id, ticket_id FROM tickets WHERE id = %s", (id,), fetch_one=True)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
        
    product_id = ticket['product_id']
    
    # Update or insert product
    if product_name:
        if product_id:
            execute_query(
                """UPDATE products SET product_name = %s, category = %s, purchase_date = %s, warranty_end_date = %s
                   WHERE id = %s""",
                (product_name, category, purchase_date, warranty_end_date, product_id),
                commit=True
            )
        else:
            product_id = execute_query(
                """INSERT INTO products (customer_id, product_name, category, purchase_date, invoice_number, warranty_start_date, warranty_end_date)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (ticket['customer_id'], product_name, category, purchase_date, 'ADMIN-ADD', purchase_date, warranty_end_date),
                commit=True
            )
            
    # Update ticket details
    query = """
    UPDATE tickets SET
        issue_type = %s, description = %s, priority = %s, product_id = %s
    WHERE id = %s
    """
    execute_query(query, (data.get('complaint_type'), data.get('description'), data.get('priority'), product_id, id), commit=True)
    
    # Handle technician assignment
    technician_id = data.get('technician_id')
    if technician_id:
        current_assign = execute_query("SELECT id FROM assignments WHERE ticket_id = %s AND technician_id = %s AND status = 'Accepted'", (id, technician_id), fetch_one=True)
        if not current_assign:
            # Decline old assignments
            execute_query("UPDATE assignments SET status = 'Declined' WHERE ticket_id = %s AND status = 'Pending'", (id,), commit=True)
            # Create new assignment
            execute_query("INSERT INTO assignments (ticket_id, technician_id, status) VALUES (%s, %s, 'Pending')", (id, technician_id), commit=True)
            # Update status to Assigned
            execute_query("UPDATE tickets SET status = 'Assigned', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (id,), commit=True)
            
    return jsonify({"message": "Ticket updated successfully"})

