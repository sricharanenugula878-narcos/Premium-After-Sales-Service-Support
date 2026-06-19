import unittest
import os
import json
import tempfile
import sqlite3
from werkzeug.security import generate_password_hash

# Ensure we import from backend
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from utils.db import init_db

class TestCustomerServiceSystem(unittest.TestCase):
    def setUp(self):
        # Set up a test client
        self.app = app.test_client()
        self.app.testing = True
        
        # Point to a temporary database file
        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        
        # Override DB_PATH in utils.db for unit tests
        import utils.db
        self.old_db_path = utils.db.DB_PATH
        utils.db.DB_PATH = app.config['DATABASE']
        
        # Initialize test schema and seed data
        utils.db.init_db()

    def tearDown(self):
        # Close and unlink database
        os.close(self.db_fd)
        os.unlink(app.config['DATABASE'])
        import utils.db
        utils.db.DB_PATH = self.old_db_path

    def get_jwt_token(self, username, password):
        response = self.app.post('/api/login', json={
            'username': username,
            'password': password
        })
        data = json.loads(response.data)
        return data.get('token')

    def test_admin_login(self):
        # Seeded admin password is 'admin123'
        response = self.app.post('/api/login', json={
            'username': 'admin',
            'password': 'admin123'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('token', data)
        self.assertEqual(data['user']['role'], 'admin')

    def test_customer_registration_and_login(self):
        # Register a new customer
        reg_response = self.app.post('/api/register', json={
            'username': 'newcustomer',
            'email': 'newcustomer@example.com',
            'password': 'custpassword',
            'full_name': 'New Customer Doe',
            'phone': '1234567890',
            'address': 'Test Road',
            'city': 'TestCity',
            'state': 'TestState',
            'pincode': '123456'
        })
        self.assertEqual(reg_response.status_code, 201)
        
        # Try logging in
        token = self.get_jwt_token('newcustomer', 'custpassword')
        self.assertIsNotNone(token)
        
        # Check profiles
        me_response = self.app.get('/api/me', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(me_response.status_code, 200)
        me_data = json.loads(me_response.data)
        self.assertEqual(me_data['username'], 'newcustomer')
        self.assertEqual(me_data['role'], 'customer')
        self.assertIn('customer', me_data)

    def test_warranty_claim_automated_rules(self):
        # Log in as customer
        token = self.get_jwt_token('customer1', 'admin123')
        
        # Ticket creation under active product (product_id = 1, Teak Wood Dining Table)
        response_active = self.app.post('/api/tickets', json={
            'product_id': 1,
            'issue_type': 'Warranty Claim',
            'description': 'Polishing is peeling off'
        }, headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(response_active.status_code, 201)
        data_active = json.loads(response_active.data)
        self.assertEqual(data_active['status'], 'Under Review') # Move to review
        
        # Ticket creation under expired product (product_id = 2, Ergonomic Office Chair)
        response_expired = self.app.post('/api/tickets', json={
            'product_id': 2,
            'issue_type': 'Warranty Claim',
            'description': 'Chair base broke'
        }, headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(response_expired.status_code, 201)
        data_expired = json.loads(response_expired.data)
        self.assertEqual(data_expired['status'], 'Rejected') # Auto Reject

    def test_admin_ticket_assignments(self):
        admin_token = self.get_jwt_token('admin', 'admin123')
        
        # Assign ticket 1 to technician 1
        assign_response = self.app.post('/api/tickets/1/assign', json={
            'technician_id': 1,
            'notes': 'Please resolve fitting issue'
        }, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(assign_response.status_code, 200)
        
        # Check if status updated to Assigned
        ticket_response = self.app.get('/api/tickets/1', headers={'Authorization': f'Bearer {admin_token}'})
        ticket_data = json.loads(ticket_response.data)
        self.assertEqual(ticket_data['status'], 'Assigned')

if __name__ == '__main__':
    unittest.main()
