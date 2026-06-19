import jwt
from functools import wraps
from flask import request, jsonify, g
from config import Config

def jwt_required(f):
    """Decorator to require valid JWT token in Authorization header"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({"error": "Token is missing. Authorization required."}), 401
            
        try:
            # Decode using Config.SECRET_KEY
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            g.user_id = payload['user_id']
            g.username = payload['username']
            g.role = payload['role']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired. Please log in again."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token. Please log in again."}), 401
            
        return f(*args, **kwargs)
    return decorated

def role_required(roles):
    """Decorator to require specific user roles"""
    if isinstance(roles, str):
        roles = [roles]
        
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(g, 'role'):
                return jsonify({"error": "Authentication required."}), 401
            if g.role not in roles:
                return jsonify({"error": f"Access forbidden. Required role: {', '.join(roles)}"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# Backward compatibility wrappers
def login_required(f):
    return jwt_required(f)

def admin_required(f):
    @wraps(f)
    @jwt_required
    def decorated(*args, **kwargs):
        if g.role != 'admin':
            return jsonify({"error": "Forbidden. Admin access required."}), 403
        return f(*args, **kwargs)
    return decorated
