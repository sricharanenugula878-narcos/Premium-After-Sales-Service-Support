from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash
from utils.db import execute_query
from utils.auth_middleware import jwt_required, role_required

technicians_bp = Blueprint('technicians', __name__)

@technicians_bp.route('', methods=['GET'])
@jwt_required
def get_technicians():
    # Admins or customers can query technicians (customers might need it to see who is coming, admins to allocate jobs)
    # Include the current count of assigned active tickets for workload monitoring
    query = """
        SELECT t.*, 
               (SELECT COUNT(*) FROM assignments a JOIN tickets tick ON a.ticket_id = tick.id WHERE a.technician_id = t.id AND tick.status IN ('Assigned', 'In Progress')) as active_jobs
        FROM technicians t 
        ORDER BY t.created_at DESC
    """
    technicians = execute_query(query, fetch_all=True)
    return jsonify(technicians)

@technicians_bp.route('', methods=['POST'])
@jwt_required
@role_required(['admin'])
def create_technician():
    data = request.json or {}
    name = data.get('name')
    phone = data.get('phone')
    email = data.get('email')
    skills = data.get('skills', '')
    availability_status = data.get('availability_status', 'Available')
    
    if not all([name, phone, email]):
        return jsonify({"error": "Required fields: name, phone, email"}), 400

    # Check if user already exists
    exist_check = execute_query("SELECT id FROM users WHERE email = %s", (email,), fetch_one=True)
    if exist_check:
        return jsonify({"error": "A user with this email already exists"}), 409

    # Generate tech code
    count_query = "SELECT COUNT(*) as count FROM technicians"
    count = execute_query(count_query, fetch_one=True)['count']
    technician_code = f"TECH-{2000 + count + 1}"

    # Auto-create user login account (default password is 'technician123')
    password_hash = generate_password_hash("technician123")
    role_res = execute_query("SELECT id FROM roles WHERE name = 'technician'", fetch_one=True)
    role_id = role_res['id'] if role_res else 2

    # Generate username
    username = email.split('@')[0]
    user_id = execute_query(
        "INSERT INTO users (username, email, password_hash, role_id) VALUES (%s, %s, %s, %s)",
        (username, email, password_hash, role_id),
        commit=True
    )

    if isinstance(user_id, dict) and 'error' in user_id:
        return jsonify({"error": "Failed to create technician user account", "details": user_id['error']}), 500

    query = """
    INSERT INTO technicians (user_id, technician_code, name, phone, email, skills, availability_status)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    params = (user_id, technician_code, name, phone, email, skills, availability_status)
    new_id = execute_query(query, params, commit=True)
    
    if isinstance(new_id, dict) and 'error' in new_id:
        # Rollback user
        execute_query("DELETE FROM users WHERE id = %s", (user_id,), commit=True)
        return jsonify({"error": "Failed to create technician profile", "details": new_id['error']}), 500

    return jsonify({
        "message": "Technician created successfully",
        "id": new_id,
        "technician_code": technician_code,
        "default_credentials": {
            "username": username,
            "password": "technician123"
        }
    }), 201

@technicians_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_technician(id):
    query = "SELECT * FROM technicians WHERE id = %s"
    technician = execute_query(query, (id,), fetch_one=True)
    if not technician:
        return jsonify({"error": "Technician not found"}), 404
        
    # Check access for technician (technicians can only view their own profile)
    if g.role == 'technician':
        tech = execute_query("SELECT id FROM technicians WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if not tech or tech['id'] != id:
            return jsonify({"error": "Access forbidden"}), 403
            
    return jsonify(technician)

@technicians_bp.route('/<int:id>', methods=['PUT'])
@jwt_required
def update_technician(id):
    data = request.json or {}
    
    # Check access for technician (technicians can only update their own profile details)
    if g.role == 'technician':
        tech = execute_query("SELECT id FROM technicians WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if not tech or tech['id'] != id:
            return jsonify({"error": "Access forbidden"}), 403
    elif g.role != 'admin':
        return jsonify({"error": "Access forbidden"}), 403

    query = """
    UPDATE technicians 
    SET name = %s, phone = %s, email = %s, skills = %s, availability_status = %s
    WHERE id = %s
    """
    params = (
        data.get('name'), data.get('phone'), data.get('email'),
        data.get('skills'), data.get('availability_status'),
        id
    )
    execute_query(query, params, commit=True)
    
    # Update user record email if changed
    tech = execute_query("SELECT user_id FROM technicians WHERE id = %s", (id,), fetch_one=True)
    if tech and tech['user_id']:
        execute_query("UPDATE users SET email = %s WHERE id = %s", (data.get('email'), tech['user_id']), commit=True)

    return jsonify({"message": "Technician profile updated successfully"})

@technicians_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required
@role_required(['admin'])
def delete_technician(id):
    tech = execute_query("SELECT user_id FROM technicians WHERE id = %s", (id,), fetch_one=True)
    
    execute_query("DELETE FROM technicians WHERE id = %s", (id,), commit=True)
    if tech and tech['user_id']:
        execute_query("DELETE FROM users WHERE id = %s", (tech['user_id'],), commit=True)
        
    return jsonify({"message": "Technician deleted successfully"})
