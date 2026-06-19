from flask import Blueprint, request, jsonify, g
from utils.db import execute_query
from utils.auth_middleware import jwt_required, role_required
from datetime import datetime

products_bp = Blueprint('products', __name__)

@products_bp.route('', methods=['GET'])
@jwt_required
def get_products():
    if g.role == 'customer':
        # Retrieve customer ref_id
        cust = execute_query("SELECT id FROM customers WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if not cust:
            return jsonify([]), 200
        query = "SELECT * FROM products WHERE customer_id = %s ORDER BY purchase_date DESC"
        products = execute_query(query, (cust['id'],), fetch_all=True)
        return jsonify(products)
    else:
        # Admins or Technicians see all products
        query = """
        SELECT p.*, c.full_name as customer_name, c.customer_code 
        FROM products p
        JOIN customers c ON p.customer_id = c.id
        ORDER BY p.created_at DESC
        """
        products = execute_query(query, fetch_all=True)
        return jsonify(products)

@products_bp.route('', methods=['POST'])
@jwt_required
def register_product():
    data = request.json or {}
    product_name = data.get('product_name')
    category = data.get('category')
    purchase_date = data.get('purchase_date')
    invoice_number = data.get('invoice_number')
    
    # Optional explicitly provided dates, else calculated
    warranty_years = int(data.get('warranty_years', 3)) # Default 3 years warranty
    warranty_start_date = data.get('warranty_start_date', purchase_date)
    
    if not all([product_name, category, purchase_date, invoice_number]):
        return jsonify({"error": "Required fields: product_name, category, purchase_date, invoice_number"}), 400
        
    # Get customer ID
    if g.role == 'customer':
        cust = execute_query("SELECT id FROM customers WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if not cust:
            return jsonify({"error": "Customer profile not found"}), 404
        customer_id = cust['id']
    else:
        customer_id = data.get('customer_id')
        if not customer_id:
            return jsonify({"error": "customer_id is required for administrative registration"}), 400

    # Calculate warranty end date if not provided
    if not data.get('warranty_end_date'):
        try:
            p_date = datetime.strptime(purchase_date, "%Y-%m-%d")
            w_end = p_date.replace(year=p_date.year + warranty_years)
            warranty_end_date = w_end.strftime("%Y-%m-%d")
        except Exception as e:
            # Fallback if parse fails
            warranty_end_date = purchase_date
    else:
        warranty_end_date = data.get('warranty_end_date')

    query = """
    INSERT INTO products (customer_id, product_name, category, purchase_date, invoice_number, warranty_start_date, warranty_end_date)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    params = (customer_id, product_name, category, purchase_date, invoice_number, warranty_start_date, warranty_end_date)
    new_id = execute_query(query, params, commit=True)
    
    if isinstance(new_id, dict) and 'error' in new_id:
        return jsonify({"error": "Failed to register product", "details": new_id['error']}), 500

    # Add audit log
    execute_query("INSERT INTO audit_logs (user_id, action, description) VALUES (%s, %s, %s)",
                  (g.user_id, 'PRODUCT_REGISTER', f"Registered product {product_name} under customer ID {customer_id}"), commit=True)

    return jsonify({
        "message": "Product registered successfully",
        "id": new_id,
        "product": {
            "id": new_id,
            "product_name": product_name,
            "category": category,
            "purchase_date": purchase_date,
            "invoice_number": invoice_number,
            "warranty_start_date": warranty_start_date,
            "warranty_end_date": warranty_end_date
        }
    }), 201

@products_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_product(id):
    query = "SELECT * FROM products WHERE id = %s"
    product = execute_query(query, (id,), fetch_one=True)
    if not product:
        return jsonify({"error": "Product not found"}), 404
        
    # Check access for customer
    if g.role == 'customer':
        cust = execute_query("SELECT id FROM customers WHERE user_id = %s", (g.user_id,), fetch_one=True)
        if not cust or product['customer_id'] != cust['id']:
            return jsonify({"error": "Access forbidden"}), 403
            
    return jsonify(product)

@products_bp.route('/<int:id>', methods=['PUT'])
@jwt_required
@role_required(['admin'])
def update_product(id):
    data = request.json or {}
    query = """
    UPDATE products 
    SET product_name = %s, category = %s, purchase_date = %s, invoice_number = %s,
        warranty_start_date = %s, warranty_end_date = %s
    WHERE id = %s
    """
    params = (
        data.get('product_name'), data.get('category'), data.get('purchase_date'),
        data.get('invoice_number'), data.get('warranty_start_date'), data.get('warranty_end_date'),
        id
    )
    execute_query(query, params, commit=True)
    return jsonify({"message": "Product updated successfully"})

@products_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required
@role_required(['admin'])
def delete_product(id):
    execute_query("DELETE FROM products WHERE id = %s", (id,), commit=True)
    return jsonify({"message": "Product deleted successfully"})

@products_bp.route('/validate-warranty/<int:id>', methods=['GET'])
@jwt_required
def validate_warranty(id):
    product = execute_query("SELECT warranty_end_date FROM products WHERE id = %s", (id,), fetch_one=True)
    if not product:
        return jsonify({"error": "Product not found"}), 404
        
    end_date_str = product['warranty_end_date']
    try:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        today = datetime.utcnow().date()
        
        is_active = end_date >= today
        days_remaining = (end_date - today).days if is_active else 0
        
        return jsonify({
            "is_active": is_active,
            "days_remaining": max(0, days_remaining),
            "warranty_expiry": end_date_str
        })
    except Exception as e:
        return jsonify({"error": "Could not parse warranty dates", "details": str(e)}), 500
