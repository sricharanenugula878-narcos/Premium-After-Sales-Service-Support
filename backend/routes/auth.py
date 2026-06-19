import jwt
import datetime
from flask import Blueprint, request, jsonify, g
from werkzeug.security import check_password_hash, generate_password_hash
from utils.db import execute_query
from utils.auth_middleware import jwt_required
from config import Config

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')
    phone = data.get('phone')
    address = data.get('address', '')
    city = data.get('city', '')
    state = data.get('state', '')
    pincode = data.get('pincode', '')

    if not all([username, email, password, full_name, phone]):
        return jsonify({"error": "Required fields: username, email, password, full_name, phone"}), 400

    # Check if username or email exists
    exist_check = execute_query("SELECT id FROM users WHERE username = %s OR email = %s", (username, email), fetch_one=True)
    if exist_check:
        return jsonify({"error": "Username or Email already exists"}), 409

    # Hash the password
    password_hash = generate_password_hash(password)

    # Get Customer role ID (seeded as 3)
    role_res = execute_query("SELECT id FROM roles WHERE name = 'customer'", fetch_one=True)
    role_id = role_res['id'] if role_res else 3

    # Generate customer code
    count_res = execute_query("SELECT COUNT(*) as count FROM customers", fetch_one=True)
    cust_count = count_res['count'] if count_res else 0
    customer_code = f"CUST-{1000 + cust_count + 1}"

    # Insert User and Customer record
    user_id = execute_query(
        "INSERT INTO users (username, email, password_hash, role_id) VALUES (%s, %s, %s, %s)",
        (username, email, password_hash, role_id),
        commit=True
    )
    
    if isinstance(user_id, dict) and 'error' in user_id:
        return jsonify({"error": "Failed to create user account", "details": user_id['error']}), 500

    cust_id = execute_query(
        """INSERT INTO customers (user_id, customer_code, full_name, phone, email, address, city, state, pincode)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (user_id, customer_code, full_name, phone, email, address, city, state, pincode),
        commit=True
    )

    # Log registration in Audit Logs
    execute_query("INSERT INTO audit_logs (user_id, action, description) VALUES (%s, %s, %s)",
                  (user_id, 'REGISTER', f"Customer account registered for {username}"), commit=True)

    return jsonify({
        "message": "Registration successful",
        "user": {
            "id": user_id,
            "username": username,
            "email": email,
            "role": "customer"
        }
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
        
    query = """
    SELECT u.id, u.username, u.password_hash, r.name as role 
    FROM users u
    JOIN roles r ON u.role_id = r.id
    WHERE u.username = %s OR u.email = %s
    """
    user = execute_query(query, (username, username), fetch_one=True)
    
    if user and check_password_hash(user['password_hash'], password):
        # Generate JWT Token
        payload = {
            'user_id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }
        token = jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')
        
        # Get customer_id or technician_id based on role to return in payload
        ref_id = None
        if user['role'] == 'customer':
            cust = execute_query("SELECT id FROM customers WHERE user_id = %s", (user['id'],), fetch_one=True)
            if cust: ref_id = cust['id']
        elif user['role'] == 'technician':
            tech = execute_query("SELECT id FROM technicians WHERE user_id = %s", (user['id'],), fetch_one=True)
            if tech: ref_id = tech['id']

        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "role": user['role'],
                "ref_id": ref_id
            }
        })
        
    return jsonify({"error": "Invalid username/email or password"}), 401

@auth_bp.route('/logout', methods=['POST'])
def logout():
    return jsonify({"message": "Logged out successfully (destroy token on client)"})

@auth_bp.route('/me', methods=['GET'])
@jwt_required
def get_current_user():
    response_data = {
        "id": g.user_id,
        "username": g.username,
        "role": g.role
    }
    
    if g.role == 'customer':
        cust = execute_query("SELECT id, customer_code, full_name, phone, email, address, city, state, pincode FROM customers WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if cust:
            response_data['customer'] = cust
            response_data['ref_id'] = cust['id']
    elif g.role == 'technician':
        tech = execute_query("SELECT id, technician_code, name, phone, email, skills, availability_status FROM technicians WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if tech:
            response_data['technician'] = tech
            response_data['ref_id'] = tech['id']
            
    return jsonify(response_data)
