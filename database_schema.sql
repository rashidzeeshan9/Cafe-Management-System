
-- Cafe Management System Database Schema
-- Based on PDF Requirements (Simplified for MCA Minor Project)

-- Users Table (Actors: Manager, Cashier, Waiter)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK(role IN ('Manager', 'Cashier', 'Waiter')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Menu Items Table
CREATE TABLE menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(50) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    is_available BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders Table
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_no VARCHAR(10) NOT NULL,
    status VARCHAR(20) DEFAULT 'Placed' CHECK(status IN ('Placed', 'Preparing', 'Completed', 'Cancelled')),
    total_amount DECIMAL(10, 2) DEFAULT 0,
    waiter_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (waiter_id) REFERENCES users(id)
);

-- Order Items Table (Many-to-Many relationship)
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price_each DECIMAL(10, 2) NOT NULL,
    line_total DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES menu_items(id)
);

-- Invoices Table
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL UNIQUE,
    subtotal DECIMAL(10, 2) NOT NULL,
    tax DECIMAL(10, 2) DEFAULT 0,
    discount DECIMAL(10, 2) DEFAULT 0,
    total DECIMAL(10, 2) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'Pending' CHECK(payment_status IN ('Pending', 'Paid', 'Failed')),
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

-- Insert default users (Manager, Cashier, Waiter)
INSERT INTO users (name, email, password, role) VALUES 
('Admin Manager', 'manager@cafe.com', 'manager123', 'Manager'),
('John Cashier', 'cashier@cafe.com', 'cashier123', 'Cashier'),
('Mary Waiter', 'waiter@cafe.com', 'waiter123', 'Waiter');

-- Insert sample menu items
INSERT INTO menu_items (name, description, price, category, stock_quantity) VALUES
('Cappuccino', 'Classic Italian coffee', 150.00, 'Beverages', 50),
('Espresso', 'Strong black coffee', 100.00, 'Beverages', 50),
('Latte', 'Milk coffee', 180.00, 'Beverages', 50),
('Sandwich', 'Veg sandwich with cheese', 120.00, 'Food', 30),
('Burger', 'Veg/Chicken burger', 200.00, 'Food', 25),
('Pasta', 'Italian pasta', 250.00, 'Food', 20),
('Cake', 'Chocolate cake slice', 150.00, 'Dessert', 15),
('Ice Cream', 'Vanilla ice cream', 80.00, 'Dessert', 40);
