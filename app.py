from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change in production

# Database configuration
DATABASE = 'cafe.db'

# Database helper functions
def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with schema"""
    conn = get_db_connection()
    with open('database_schema.sql', 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Role-based access decorator
def role_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session['role'] not in roles:
                flash('Access denied! Insufficient permissions.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/')
def index():
    """Landing page"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', 
                           (email, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('login'))

# ==================== DASHBOARD ROUTE ====================

@app.route('/dashboard')
@login_required
def dashboard():
    """Role-based dashboard"""
    conn = get_db_connection()
    
    # Get statistics based on role
    stats = {}
    
    if session['role'] == 'Manager':
        # Manager sees everything
        stats['total_orders'] = conn.execute('SELECT COUNT(*) as count FROM orders').fetchone()['count']
        stats['total_revenue'] = conn.execute('SELECT SUM(total_amount) as total FROM orders WHERE status = "Completed"').fetchone()['total'] or 0
        stats['menu_items'] = conn.execute('SELECT COUNT(*) as count FROM menu_items').fetchone()['count']
        stats['pending_orders'] = conn.execute('SELECT COUNT(*) as count FROM orders WHERE status != "Completed"').fetchone()['count']
        
        # Recent orders
        recent_orders = conn.execute('''
            SELECT o.*, u.name as waiter_name 
            FROM orders o 
            JOIN users u ON o.waiter_id = u.id 
            ORDER BY o.created_at DESC LIMIT 5
        ''').fetchall()
        
    elif session['role'] == 'Cashier':
        # Cashier sees billing info
        stats['pending_payments'] = conn.execute('SELECT COUNT(*) as count FROM invoices WHERE payment_status = "Pending"').fetchone()['count']
        stats['today_revenue'] = conn.execute('SELECT SUM(total) as total FROM invoices WHERE DATE(created_at) = DATE("now") AND payment_status = "Paid"').fetchone()['total'] or 0
        
        # Pending bills
        recent_orders = conn.execute('''
            SELECT o.*, u.name as waiter_name 
            FROM orders o 
            JOIN users u ON o.waiter_id = u.id 
            WHERE o.status = "Completed"
            ORDER BY o.created_at DESC LIMIT 5
        ''').fetchall()
        
    else:  # Waiter
        # Waiter sees their orders
        stats['my_orders'] = conn.execute('SELECT COUNT(*) as count FROM orders WHERE waiter_id = ?', (session['user_id'],)).fetchone()['count']
        stats['active_orders'] = conn.execute('SELECT COUNT(*) as count FROM orders WHERE waiter_id = ? AND status != "Completed"', (session['user_id'],)).fetchone()['count']
        
        # My recent orders
        recent_orders = conn.execute('''
            SELECT * FROM orders 
            WHERE waiter_id = ? 
            ORDER BY created_at DESC LIMIT 5
        ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', stats=stats, recent_orders=recent_orders)

# ==================== MENU MANAGEMENT ROUTES ====================

@app.route('/menu')
@login_required
def menu():
    """View menu items"""
    conn = get_db_connection()
    menu_items = conn.execute('SELECT * FROM menu_items ORDER BY category, name').fetchall()
    conn.close()
    return render_template('menu.html', menu_items=menu_items)

@app.route('/menu/add', methods=['GET', 'POST'])
@login_required
@role_required('Manager')
def add_menu_item():
    """Add new menu item (Manager only)"""
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        category = request.form['category']
        stock_quantity = int(request.form['stock_quantity'])
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO menu_items (name, description, price, category, stock_quantity)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, description, price, category, stock_quantity))
        conn.commit()
        conn.close()
        
        flash('Menu item added successfully!', 'success')
        return redirect(url_for('menu'))
    
    return render_template('add_menu_item.html')

@app.route('/menu/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
@role_required('Manager')
def edit_menu_item(item_id):
    """Edit menu item (Manager only)"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        category = request.form['category']
        stock_quantity = int(request.form['stock_quantity'])
        is_available = 1 if 'is_available' in request.form else 0
        
        conn.execute('''
            UPDATE menu_items 
            SET name=?, description=?, price=?, category=?, stock_quantity=?, is_available=?
            WHERE id=?
        ''', (name, description, price, category, stock_quantity, is_available, item_id))
        conn.commit()
        conn.close()
        
        flash('Menu item updated successfully!', 'success')
        return redirect(url_for('menu'))
    
    item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    conn.close()
    
    return render_template('edit_menu_item.html', item=item)

@app.route('/menu/delete/<int:item_id>')
@login_required
@role_required('Manager')
def delete_menu_item(item_id):
    """Delete menu item (Manager only)"""
    conn = get_db_connection()
    conn.execute('DELETE FROM menu_items WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()
    
    flash('Menu item deleted successfully!', 'success')
    return redirect(url_for('menu'))

# ==================== ORDER MANAGEMENT ROUTES ====================

@app.route('/orders')
@login_required
def orders():
    """View all orders"""
    conn = get_db_connection()
    
    if session['role'] == 'Waiter':
        # Waiters see only their orders
        orders_list = conn.execute('''
            SELECT o.*, u.name as waiter_name 
            FROM orders o 
            JOIN users u ON o.waiter_id = u.id 
            WHERE o.waiter_id = ?
            ORDER BY o.created_at DESC
        ''', (session['user_id'],)).fetchall()
    else:
        # Manager and Cashier see all orders
        orders_list = conn.execute('''
            SELECT o.*, u.name as waiter_name 
            FROM orders o 
            JOIN users u ON o.waiter_id = u.id 
            ORDER BY o.created_at DESC
        ''').fetchall()
    
    conn.close()
    return render_template('orders.html', orders=orders_list)

@app.route('/orders/create', methods=['GET', 'POST'])
@login_required
@role_required('Waiter', 'Manager')
def create_order():
    """Create new order"""
    if request.method == 'POST':
        table_no = request.form['table_no']
        item_ids = request.form.getlist('item_ids[]')
        quantities = request.form.getlist('quantities[]')
        
        if not item_ids:
            flash('Please select at least one item!', 'error')
            return redirect(url_for('create_order'))
        
        conn = get_db_connection()
        
        # Create order
        cursor = conn.execute('''
            INSERT INTO orders (table_no, waiter_id, status)
            VALUES (?, ?, 'Placed')
        ''', (table_no, session['user_id']))
        order_id = cursor.lastrowid
        
        total_amount = 0
        
        # Add order items
        for item_id, quantity in zip(item_ids, quantities):
            if quantity and int(quantity) > 0:
                # Get item price
                item = conn.execute('SELECT price FROM menu_items WHERE id = ?', (item_id,)).fetchone()
                price = item['price']
                quantity = int(quantity)
                line_total = price * quantity
                total_amount += line_total
                
                conn.execute('''
                    INSERT INTO order_items (order_id, item_id, quantity, price_each, line_total)
                    VALUES (?, ?, ?, ?, ?)
                ''', (order_id, item_id, quantity, price, line_total))
        
        # Update order total
        conn.execute('UPDATE orders SET total_amount = ? WHERE id = ?', (total_amount, order_id))
        
        conn.commit()
        conn.close()
        
        flash(f'Order #{order_id} created successfully!', 'success')
        return redirect(url_for('orders'))
    
    # GET request - show menu for ordering
    conn = get_db_connection()
    menu_items = conn.execute('SELECT * FROM menu_items WHERE is_available = 1 ORDER BY category, name').fetchall()
    conn.close()
    
    return render_template('create_order.html', menu_items=menu_items)

@app.route('/orders/view/<int:order_id>')
@login_required
def view_order(order_id):
    """View order details"""
    conn = get_db_connection()
    
    order = conn.execute('''
        SELECT o.*, u.name as waiter_name 
        FROM orders o 
        JOIN users u ON o.waiter_id = u.id 
        WHERE o.id = ?
    ''', (order_id,)).fetchone()
    
    order_items = conn.execute('''
        SELECT oi.*, mi.name as item_name 
        FROM order_items oi 
        JOIN menu_items mi ON oi.item_id = mi.id 
        WHERE oi.order_id = ?
    ''', (order_id,)).fetchall()
    
    conn.close()
    
    return render_template('view_order.html', order=order, order_items=order_items)

@app.route('/orders/update_status/<int:order_id>/<status>')
@login_required
def update_order_status(order_id, status):
    """Update order status"""
    conn = get_db_connection()
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()
    
    flash(f'Order status updated to {status}!', 'success')
    return redirect(url_for('orders'))

# ==================== BILLING ROUTES ====================

@app.route('/billing')
@login_required
@role_required('Cashier', 'Manager')
def billing():
    """View completed orders for billing"""
    conn = get_db_connection()
    
    completed_orders = conn.execute('''
        SELECT o.*, u.name as waiter_name,
               COALESCE(i.payment_status, 'Pending') as payment_status,
               i.id as invoice_id
        FROM orders o 
        JOIN users u ON o.waiter_id = u.id 
        LEFT JOIN invoices i ON o.id = i.order_id
        WHERE o.status = 'Completed'
        ORDER BY o.created_at DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('billing.html', orders=completed_orders)

@app.route('/billing/generate/<int:order_id>', methods=['GET', 'POST'])
@login_required
@role_required('Cashier', 'Manager')
def generate_bill(order_id):
    """Generate bill/invoice for order"""
    conn = get_db_connection()
    
    # Check if invoice already exists
    existing_invoice = conn.execute('SELECT * FROM invoices WHERE order_id = ?', (order_id,)).fetchone()
    
    if existing_invoice:
        flash('Invoice already generated for this order!', 'info')
        return redirect(url_for('view_invoice', invoice_id=existing_invoice['id']))
    
    if request.method == 'POST':
        discount = float(request.form.get('discount', 0))
        
        # Get order total
        order = conn.execute('SELECT total_amount FROM orders WHERE id = ?', (order_id,)).fetchone()
        subtotal = order['total_amount']
        
        # Calculate tax (5% GST)
        tax = subtotal * 0.05
        
        # Calculate total
        total = subtotal + tax - discount
        
        # Create invoice
        conn.execute('''
            INSERT INTO invoices (order_id, subtotal, tax, discount, total, payment_status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
        ''', (order_id, subtotal, tax, discount, total))
        
        conn.commit()
        invoice_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()
        
        flash('Invoice generated successfully!', 'success')
        return redirect(url_for('view_invoice', invoice_id=invoice_id))
    
    # GET request
    order = conn.execute('''
        SELECT o.*, u.name as waiter_name 
        FROM orders o 
        JOIN users u ON o.waiter_id = u.id 
        WHERE o.id = ?
    ''', (order_id,)).fetchone()
    
    order_items = conn.execute('''
        SELECT oi.*, mi.name as item_name 
        FROM order_items oi 
        JOIN menu_items mi ON oi.item_id = mi.id 
        WHERE oi.order_id = ?
    ''', (order_id,)).fetchall()
    
    conn.close()
    
    return render_template('generate_bill.html', order=order, order_items=order_items)

@app.route('/billing/invoice/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    """View invoice details"""
    conn = get_db_connection()
    
    invoice = conn.execute('''
        SELECT i.*, o.table_no, o.created_at as order_date, u.name as waiter_name
        FROM invoices i
        JOIN orders o ON i.order_id = o.id
        JOIN users u ON o.waiter_id = u.id
        WHERE i.id = ?
    ''', (invoice_id,)).fetchone()
    
    order_items = conn.execute('''
        SELECT oi.*, mi.name as item_name 
        FROM order_items oi 
        JOIN menu_items mi ON oi.item_id = mi.id 
        WHERE oi.order_id = ?
    ''', (invoice['order_id'],)).fetchall()
    
    conn.close()
    
    return render_template('invoice.html', invoice=invoice, order_items=order_items)

@app.route('/billing/payment/<int:invoice_id>')
@login_required
@role_required('Cashier', 'Manager')
def mark_paid(invoice_id):
    """Mark invoice as paid"""
    conn = get_db_connection()
    conn.execute('''
        UPDATE invoices 
        SET payment_status = 'Paid', paid_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (invoice_id,))
    conn.commit()
    conn.close()
    
    flash('Payment received successfully!', 'success')
    return redirect(url_for('billing'))

# ==================== REPORTS ROUTE ====================

@app.route('/reports')
@login_required
@role_required('Manager')
def reports():
    """View sales reports (Manager only)"""
    conn = get_db_connection()
    
    # Today's sales
    today_sales = conn.execute('''
        SELECT SUM(total) as total 
        FROM invoices 
        WHERE DATE(created_at) = DATE('now') AND payment_status = 'Paid'
    ''').fetchone()['total'] or 0
    
    # This week's sales
    week_sales = conn.execute('''
        SELECT SUM(total) as total 
        FROM invoices 
        WHERE DATE(created_at) >= DATE('now', '-7 days') AND payment_status = 'Paid'
    ''').fetchone()['total'] or 0
    
    # Top selling items
    top_items = conn.execute('''
        SELECT mi.name, SUM(oi.quantity) as total_quantity, SUM(oi.line_total) as revenue
        FROM order_items oi
        JOIN menu_items mi ON oi.item_id = mi.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status = 'Completed'
        GROUP BY mi.id
        ORDER BY total_quantity DESC
        LIMIT 5
    ''').fetchall()
    
    # Recent transactions
    recent_transactions = conn.execute('''
        SELECT i.*, o.table_no 
        FROM invoices i 
        JOIN orders o ON i.order_id = o.id 
        ORDER BY i.created_at DESC 
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template('reports.html', 
                         today_sales=today_sales, 
                         week_sales=week_sales,
                         top_items=top_items,
                         recent_transactions=recent_transactions)

# ==================== RUN APPLICATION ====================

if __name__ == '__main__':
    # Initialize database if not exists
    import os
    if not os.path.exists(DATABASE):
        init_db()
        print("Database initialized!")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
