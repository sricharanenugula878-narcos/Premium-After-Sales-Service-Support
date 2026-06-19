-- Insert Roles
INSERT INTO roles (id, name, description) VALUES
(1, 'admin', 'Administrator access'),
(2, 'technician', 'Field technician access'),
(3, 'customer', 'Customer access');

-- Insert Users
-- Default Password is 'admin123'
-- Hash: scrypt:32768:8:1$QpxGStNXhprXBIh0$080d12ca77fbeb8218f81aadcd3d89ff49f128ba8e0404f6299876df9b282b741cb6669a32f92a41baf2ccda54cb83b94b02fc494a37f0e7c67f24af8082c3be
INSERT INTO users (id, username, email, password_hash, role_id) VALUES
(1, 'admin', 'admin@svsfurniture.com', 'scrypt:32768:8:1$QpxGStNXhprXBIh0$080d12ca77fbeb8218f81aadcd3d89ff49f128ba8e0404f6299876df9b282b741cb6669a32f92a41baf2ccda54cb83b94b02fc494a37f0e7c67f24af8082c3be', 1),
(2, 'tech1', 'tech1@svsfurniture.com', 'scrypt:32768:8:1$QpxGStNXhprXBIh0$080d12ca77fbeb8218f81aadcd3d89ff49f128ba8e0404f6299876df9b282b741cb6669a32f92a41baf2ccda54cb83b94b02fc494a37f0e7c67f24af8082c3be', 2),
(3, 'customer1', 'customer1@example.com', 'scrypt:32768:8:1$QpxGStNXhprXBIh0$080d12ca77fbeb8218f81aadcd3d89ff49f128ba8e0404f6299876df9b282b741cb6669a32f92a41baf2ccda54cb83b94b02fc494a37f0e7c67f24af8082c3be', 3);

-- Insert Customers
INSERT INTO customers (id, user_id, customer_code, full_name, phone, email, address, city, state, pincode) VALUES
(1, 3, 'CUST-1001', 'John Doe', '9876543210', 'customer1@example.com', '123 Elm Street, Gachibowli', 'Hyderabad', 'Telangana', '500032');

-- Insert Products
INSERT INTO products (id, customer_id, product_name, category, purchase_date, invoice_number, warranty_start_date, warranty_end_date) VALUES
(1, 1, 'Teak Wood Dining Table', 'Dining Table', '2025-01-15', 'INV-2025-001', '2025-01-15', '2028-01-15'),
(2, 1, 'Ergonomic Office Chair', 'Chairs', '2023-05-10', 'INV-2023-142', '2023-05-10', '2024-05-10'); -- Expired

-- Insert Technicians
INSERT INTO technicians (id, user_id, technician_code, name, phone, email, skills, availability_status) VALUES
(1, 2, 'TECH-2001', 'Michael Carpenter', '9988776655', 'tech1@svsfurniture.com', 'Polishing, Carpentry, Fitment', 'Available');

-- Insert Tickets
INSERT INTO tickets (id, ticket_id, customer_id, product_id, issue_type, description, priority, status) VALUES
(1, 'TKT-2026-0001', 1, 1, 'Polishing Request', 'Table surface lost its shine due to liquid spill. Needs repolishing.', 'Medium', 'New'),
(2, 'TKT-2026-0002', 1, 2, 'Product Complaint', 'Chair height adjustment cylinder is not working properly.', 'High', 'Assigned');

-- Insert Ticket Comments
INSERT INTO ticket_comments (ticket_id, user_id, comment, is_internal) VALUES
(1, 3, 'Initial complaint submittal. Please check if this is covered under the 3-year warranty.', 0);

-- Insert Assignments
INSERT INTO assignments (ticket_id, technician_id, status, notes) VALUES
(2, 1, 'Pending', 'Please look into the chair height adjustments.');

-- Insert Notifications
INSERT INTO notifications (user_id, title, message, is_read) VALUES
(3, 'Ticket Submitted Successfully', 'Your ticket TKT-2026-0001 has been registered.', 0);

-- Insert Audit Logs
INSERT INTO audit_logs (user_id, action, description) VALUES
(3, 'REGISTER', 'User customer1 registered.'),
(3, 'TICKET_CREATE', 'Ticket TKT-2026-0001 created.');

-- Insert Status History
INSERT INTO status_history (ticket_id, status, changed_by, notes) VALUES
(1, 'New', 'customer1', 'Ticket created by customer'),
(2, 'New', 'customer1', 'Ticket created by customer'),
(2, 'Assigned', 'admin', 'Assigned to Technician Michael Carpenter');
