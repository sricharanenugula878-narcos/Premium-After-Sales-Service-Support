from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash
from utils.db import execute_query
from utils.auth_middleware import jwt_required, role_required

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('', methods=['GET'])
@jwt_required
@role_required(['admin'])
def get_customers():
    query = "SELECT * FROM customers ORDER BY created_at DESC"
    customers = execute_query(query, fetch_all=True)
    return jsonify(customers)

@customers_bp.route('', methods=['POST'])
@jwt_required
@role_required(['admin'])
def create_customer():
    data = request.json or {}
    full_name = data.get('full_name')
    phone = data.get('phone')
    email = data.get('email')
    address = data.get('address', '')
    city = data.get('city', '')
    state = data.get('state', '')
    pincode = data.get('pincode', '')
    
    if not all([full_name, phone, email]):
        return jsonify({"error": "Required fields: full_name, phone, email"}), 400
        
    # Check if user already exists
    exist_check = execute_query("SELECT id FROM users WHERE email = %s", (email,), fetch_one=True)
    if exist_check:
        return jsonify({"error": "A user with this email already exists"}), 409

    # Generate customer code
    count_query = "SELECT COUNT(*) as count FROM customers"
    count = execute_query(count_query, fetch_one=True)['count']
    customer_code = f"CUST-{1000 + count + 1}"

    # Auto-create user login account (default password is 'customer123')
    password_hash = generate_password_hash("customer123")
    role_res = execute_query("SELECT id FROM roles WHERE name = 'customer'", fetch_one=True)
    role_id = role_res['id'] if role_res else 3

    # Generate username from full_name or email
    username = email.split('@')[0]
    user_id = execute_query(
        "INSERT INTO users (username, email, password_hash, role_id) VALUES (%s, %s, %s, %s)",
        (username, email, password_hash, role_id),
        commit=True
    )

    if isinstance(user_id, dict) and 'error' in user_id:
        return jsonify({"error": "Failed to create customer user account", "details": user_id['error']}), 500

    query = """
    INSERT INTO customers (user_id, customer_code, full_name, phone, email, address, city, state, pincode)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (user_id, customer_code, full_name, phone, email, address, city, state, pincode)
    new_id = execute_query(query, params, commit=True)
    
    if isinstance(new_id, dict) and 'error' in new_id:
        # Rollback user
        execute_query("DELETE FROM users WHERE id = %s", (user_id,), commit=True)
        return jsonify({"error": "Failed to create customer profile", "details": new_id['error']}), 500
        
    return jsonify({
        "message": "Customer created successfully",
        "id": new_id,
        "customer_code": customer_code,
        "default_credentials": {
            "username": username,
            "password": "customer123"
        }
    }), 201

@customers_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_customer(id):
    query = "SELECT * FROM customers WHERE id = %s"
    customer = execute_query(query, (id,), fetch_one=True)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
        
    # Check access for customer
    if g.role == 'customer':
        cust = execute_query("SELECT id FROM customers WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if not cust or cust['id'] != id:
            return jsonify({"error": "Access forbidden"}), 403
            
    return jsonify(customer)

@customers_bp.route('/<int:id>', methods=['PUT'])
@jwt_required
def update_customer(id):
    data = request.json or {}
    
    # Check access for customer
    if g.role == 'customer':
        cust = execute_query("SELECT id FROM customers WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if not cust or cust['id'] != id:
            return jsonify({"error": "Access forbidden"}), 403
    elif g.role != 'admin':
        return jsonify({"error": "Access forbidden"}), 403

    query = """
    UPDATE customers 
    SET full_name = %s, phone = %s, email = %s, address = %s, city = %s, state = %s, pincode = %s
    WHERE id = %s
    """
    params = (
        data.get('full_name'), data.get('phone'), data.get('email'),
        data.get('address'), data.get('city'), data.get('state'), data.get('pincode'),
        id
    )
    execute_query(query, params, commit=True)
    
    # Update corresponding user record email if changed
    cust = execute_query("SELECT user_id, email FROM customers WHERE id = %s", (id,), fetch_one=True)
    if cust and cust['user_id']:
        execute_query("UPDATE users SET email = %s WHERE id = %s", (data.get('email'), cust['user_id']), commit=True)

    return jsonify({"message": "Customer profile updated successfully"})

@customers_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required
@role_required(['admin'])
def delete_customer(id):
    # Fetch user_id to delete user login too
    cust = execute_query("SELECT user_id FROM customers WHERE id = %s", (id,), fetch_one=True)
    
    execute_query("DELETE FROM customers WHERE id = %s", (id,), commit=True)
    if cust and cust['user_id']:
        execute_query("DELETE FROM users WHERE id = %s", (cust['user_id'],), commit=True)
        
    return jsonify({"message": "Customer deleted successfully"})
