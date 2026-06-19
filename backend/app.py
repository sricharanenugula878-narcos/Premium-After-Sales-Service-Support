import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from config import Config

# Initialize app
app = Flask(__name__, static_folder='../frontend')
app.config.from_object(Config)

# Enable CORS (allow credentials for session/JWT in headers)
CORS(app, supports_credentials=True)

# Import Blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.customers import customers_bp
from routes.technicians import technicians_bp
from routes.tickets import tickets_bp
from routes.products import products_bp
from routes.reports import reports_bp

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(customers_bp, url_prefix='/api/customers')
app.register_blueprint(technicians_bp, url_prefix='/api/technicians')
app.register_blueprint(tickets_bp, url_prefix='/api/tickets')
app.register_blueprint(products_bp, url_prefix='/api/products')
app.register_blueprint(reports_bp, url_prefix='/api/reports')

# Serve Uploaded Support Images
@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    return send_from_directory(uploads_dir, filename)

# Serve Static Frontend Files
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    elif path.endswith('.html'):
        # Fallback to index if exact HTML not found, though we should probably 404
        pass
    return send_from_directory(app.static_folder, 'index.html')

# Global Error Handler
@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP errors
    if hasattr(e, 'code'):
        return jsonify(error=str(e)), e.code
    # Handle non-HTTP errors
    return jsonify(error="Internal Server Error", details=str(e)), 500

if __name__ == '__main__':
    # Create uploads directory if not exists
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    
    app.run(debug=True, port=5000)
