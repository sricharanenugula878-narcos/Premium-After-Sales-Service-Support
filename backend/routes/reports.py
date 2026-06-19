import io
import csv
from flask import Blueprint, jsonify, request, Response, g
from utils.db import execute_query
from utils.auth_middleware import jwt_required, role_required
from datetime import datetime

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/summary', methods=['GET'])
@jwt_required
@role_required(['admin'])
def get_report_summary():
    # 1. Monthly Trends (last 12 months)
    monthly = execute_query(
        """SELECT strftime('%Y-%m', created_at) as label, COUNT(*) as value
           FROM tickets 
           GROUP BY label 
           ORDER BY label ASC LIMIT 12""", 
        fetch_all=True
    )
    
    # 2. Status Distribution
    status_dist = execute_query(
        "SELECT status as label, COUNT(*) as value FROM tickets GROUP BY status", 
        fetch_all=True
    )
    
    # 3. Category/Issue Type Distribution
    category_dist = execute_query(
        "SELECT issue_type as label, COUNT(*) as value FROM tickets GROUP BY issue_type", 
        fetch_all=True
    )
    
    # 4. Priority Distribution
    priority_dist = execute_query(
        "SELECT priority as label, COUNT(*) as value FROM tickets GROUP BY priority", 
        fetch_all=True
    )
    
    # 5. Average Resolution Time in Days (on SQLite)
    res_time = execute_query(
        """SELECT AVG(julianday(updated_at) - julianday(created_at)) as avg_days 
           FROM tickets 
           WHERE status IN ('Resolved', 'Closed')""", 
        fetch_one=True
    )
    avg_days = round(res_time['avg_days'], 2) if res_time and res_time['avg_days'] is not None else 0.0

    # 6. Technician performance summary
    tech_performance = execute_query(
        """SELECT t.name as label, COUNT(tick.id) as value
           FROM technicians t
           JOIN assignments a ON t.id = a.technician_id
           JOIN tickets tick ON a.ticket_id = tick.id
           WHERE tick.status IN ('Resolved', 'Closed')
           GROUP BY t.id, t.name
           ORDER BY value DESC LIMIT 5""",
        fetch_all=True
    )

    return jsonify({
        "monthly": monthly,
        "status": status_dist,
        "category": category_dist,
        "priority": priority_dist,
        "average_resolution_days": avg_days,
        "technicians": tech_performance
    })

@reports_bp.route('/export', methods=['GET'])
@jwt_required
@role_required(['admin'])
def export_reports():
    # Filter options
    status_filter = request.args.get('status', '').strip()
    priority_filter = request.args.get('priority', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
    query = """
        SELECT t.ticket_id, c.full_name as customer_name, c.phone as customer_phone,
               p.product_name, t.issue_type, t.priority, t.status, t.admin_notes,
               t.created_at, t.updated_at
        FROM tickets t
        LEFT JOIN products p ON t.product_id = p.id
        JOIN customers c ON t.customer_id = c.id
        WHERE 1=1
    """
    
    params = []
    
    if status_filter:
        query += " AND t.status = %s"
        params.append(status_filter)
    if priority_filter:
        query += " AND t.priority = %s"
        params.append(priority_filter)
    if start_date:
        query += " AND t.created_at >= %s"
        params.append(f"{start_date} 00:00:00")
    if end_date:
        query += " AND t.created_at <= %s"
        params.append(f"{end_date} 23:59:59")
        
    query += " ORDER BY t.created_at DESC"
    tickets = execute_query(query, tuple(params), fetch_all=True)
    
    # Create CSV in-memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "Ticket ID", "Customer Name", "Customer Phone", "Product Name", 
        "Issue Type", "Priority", "Status", "Resolution/Admin Notes", 
        "Created At", "Updated At"
    ])
    
    for t in tickets:
        writer.writerow([
            t['ticket_id'], t['customer_name'], t['customer_phone'], t['product_name'] or 'N/A',
            t['issue_type'], t['priority'], t['status'], t['admin_notes'] or '',
            t['created_at'], t['updated_at']
        ])
        
    # Return response
    csv_data = output.getvalue()
    output.close()
    
    filename = f"tickets_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )
