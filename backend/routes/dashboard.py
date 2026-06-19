from flask import Blueprint, jsonify, g
from utils.db import execute_query
from utils.auth_middleware import jwt_required, role_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/summary', methods=['GET'])
@jwt_required
def get_dashboard_summary():
    # If the user is a customer, return customer dashboard summary metrics
    if g.role == 'customer':
        cust = execute_query("SELECT id FROM customers WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if not cust:
            return jsonify({"error": "Customer profile not found"}), 404
        customer_id = cust['id']
        
        # Customer-specific counts
        total_tickets = execute_query("SELECT COUNT(*) as count FROM tickets WHERE customer_id = %s", (customer_id,), fetch_one=True)['count']
        active_tickets = execute_query("SELECT COUNT(*) as count FROM tickets WHERE customer_id = %s AND status NOT IN ('Resolved', 'Closed', 'Rejected')", (customer_id,), fetch_one=True)['count']
        resolved_tickets = execute_query("SELECT COUNT(*) as count FROM tickets WHERE customer_id = %s AND status IN ('Resolved', 'Closed')", (customer_id,), fetch_one=True)['count']
        products_registered = execute_query("SELECT COUNT(*) as count FROM products WHERE customer_id = %s", (customer_id,), fetch_one=True)['count']
        
        recent_tickets = execute_query(
            """SELECT id, ticket_id, issue_type, priority, status, created_at
               FROM tickets WHERE customer_id = %s
               ORDER BY created_at DESC LIMIT 5""",
            (customer_id,), fetch_all=True
        )
        
        recent_notifications = execute_query(
            "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT 5",
            (g.user_id,), fetch_all=True
        )
        
        return jsonify({
            "role": "customer",
            "metrics": {
                "total_tickets": total_tickets,
                "active_tickets": active_tickets,
                "resolved_tickets": resolved_tickets,
                "products_registered": products_registered
            },
            "recent_tickets": recent_tickets,
            "notifications": recent_notifications
        })
        
    # If the user is a technician, return technician-specific dashboard metrics
    elif g.role == 'technician':
        tech = execute_query("SELECT id FROM technicians WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if not tech:
            return jsonify({"error": "Technician profile not found"}), 404
        technician_id = tech['id']
        
        assigned_tickets = execute_query(
            """SELECT COUNT(*) as count FROM assignments a 
               JOIN tickets t ON a.ticket_id = t.id 
               WHERE a.technician_id = %s AND t.status IN ('Assigned', 'In Progress')""",
            (technician_id,), fetch_one=True
        )['count']
        
        completed_tickets = execute_query(
            """SELECT COUNT(*) as count FROM assignments a 
               JOIN tickets t ON a.ticket_id = t.id 
               WHERE a.technician_id = %s AND t.status IN ('Resolved', 'Closed')""",
            (technician_id,), fetch_one=True
        )['count']
        
        pending_assignments = execute_query(
            "SELECT COUNT(*) as count FROM assignments WHERE technician_id = %s AND status = 'Pending'",
            (technician_id,), fetch_one=True
        )['count']
        
        recent_jobs = execute_query(
            """SELECT t.id, t.ticket_id, t.issue_type, t.priority, t.status, a.status as assignment_status, cust.full_name as customer_name
               FROM tickets t
               JOIN assignments a ON t.id = a.ticket_id
               JOIN customers cust ON t.customer_id = cust.id
               WHERE a.technician_id = %s
               ORDER BY t.created_at DESC LIMIT 5""",
            (technician_id,), fetch_all=True
        )
        
        return jsonify({
            "role": "technician",
            "metrics": {
                "assigned_tickets": assigned_tickets,
                "completed_tickets": completed_tickets,
                "pending_assignments": pending_assignments
            },
            "recent_jobs": recent_jobs
        })

    # If the user is an admin, return complete system metrics
    else: # admin
        total_customers = execute_query("SELECT COUNT(*) as count FROM customers", fetch_one=True)['count']
        total_products = execute_query("SELECT COUNT(*) as count FROM products", fetch_one=True)['count']
        total_tickets = execute_query("SELECT COUNT(*) as count FROM tickets", fetch_one=True)['count']
        active_tickets = execute_query("SELECT COUNT(*) as count FROM tickets WHERE status NOT IN ('Resolved', 'Closed', 'Rejected')", fetch_one=True)['count']
        pending_tickets = execute_query("SELECT COUNT(*) as count FROM tickets WHERE status = 'New'", fetch_one=True)['count']
        resolved_tickets = execute_query("SELECT COUNT(*) as count FROM tickets WHERE status IN ('Resolved', 'Closed')", fetch_one=True)['count']
        warranty_claims = execute_query("SELECT COUNT(*) as count FROM warranty_claims", fetch_one=True)['count']
        
        recent_complaints = execute_query(
            """SELECT t.id, t.ticket_id, t.issue_type, t.status, t.priority, t.created_at, cust.full_name as customer_name
               FROM tickets t
               JOIN customers cust ON t.customer_id = cust.id
               ORDER BY t.created_at DESC LIMIT 5""",
            fetch_all=True
        )
        
        recent_activities = execute_query(
            """SELECT al.action, al.description, al.created_at, u.username
               FROM audit_logs al
               LEFT JOIN users u ON al.user_id = u.id
               ORDER BY al.created_at DESC LIMIT 5""",
            fetch_all=True
        )
        
        technicians_status = execute_query(
            """SELECT t.name, t.availability_status,
                      (SELECT COUNT(*) FROM assignments a JOIN tickets tick ON a.ticket_id = tick.id WHERE a.technician_id = t.id AND tick.status IN ('Assigned', 'In Progress')) as load
               FROM technicians t LIMIT 5""",
            fetch_all=True
        )
        
        return jsonify({
            "role": "admin",
            "metrics": {
                "total_customers": total_customers,
                "total_products": total_products,
                "total_tickets": total_tickets,
                "active_tickets": active_tickets,
                "pending_tickets": pending_tickets,
                "resolved_tickets": resolved_tickets,
                "warranty_claims": warranty_claims
            },
            "recent_complaints": recent_complaints,
            "recent_activities": recent_activities,
            "technicians_status": technicians_status
        })
