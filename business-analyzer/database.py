import sqlite3
import os
import pandas as pd
import numpy as np
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT,
        phone TEXT
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(user_id, name)
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        category_id INTEGER,
        sku TEXT,
        price REAL NOT NULL DEFAULT 0.0,
        cost REAL NOT NULL DEFAULT 0.0,
        stock INTEGER NOT NULL DEFAULT 0,
        threshold INTEGER NOT NULL DEFAULT 10,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
        UNIQUE(user_id, name)
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        notes TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(user_id, name)
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        customer_id INTEGER,
        date TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('Pending', 'Completed', 'Cancelled')),
        total_amount REAL NOT NULL DEFAULT 0.0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER,
        quantity INTEGER NOT NULL DEFAULT 1,
        price REAL NOT NULL DEFAULT 0.0,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
    );
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_user ON products(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_user ON customers(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);")
    
    conn.commit()
    conn.close()

# ── User Auth Helpers ──
def register_user(username, password_hash, email, phone):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO users (username, password_hash, email, phone)
        VALUES (?, ?, ?, ?)
        """, (username, password_hash, email, phone))
        user_id = cursor.lastrowid
        # Add default category
        cursor.execute("INSERT INTO categories (user_id, name) VALUES (?, 'General')", (user_id,))
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user

# ── Category Helpers ──
def get_categories(user_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM categories WHERE user_id = ? ORDER BY name ASC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_category(user_id, name):
    conn = get_db()
    try:
        conn.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)", (user_id, name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# ── Product Helpers ──
def get_products(user_id):
    conn = get_db()
    query = """
    SELECT p.*, c.name as category_name 
    FROM products p 
    LEFT JOIN categories c ON p.category_id = c.id 
    WHERE p.user_id = ? 
    ORDER BY p.name ASC
    """
    rows = conn.execute(query, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_product(user_id, name, category_id, sku, price, cost, stock, threshold):
    conn = get_db()
    try:
        conn.execute("""
        INSERT INTO products (user_id, name, category_id, sku, price, cost, stock, threshold)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, category_id, sku, price, cost, stock, threshold))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_product(user_id, product_id, name, category_id, sku, price, cost, stock, threshold):
    conn = get_db()
    try:
        conn.execute("""
        UPDATE products 
        SET name = ?, category_id = ?, sku = ?, price = ?, cost = ?, stock = ?, threshold = ?
        WHERE id = ? AND user_id = ?
        """, (name, category_id, sku, price, cost, stock, threshold, product_id, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_product(user_id, product_id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ? AND user_id = ?", (product_id, user_id))
    conn.commit()
    conn.close()

# ── Customer Helpers ──
def get_customers(user_id):
    conn = get_db()
    query = """
    SELECT c.*, 
           COALESCE(SUM(o.total_amount), 0) as total_spent,
           COUNT(o.id) as total_orders
    FROM customers c
    LEFT JOIN orders o ON c.id = o.customer_id AND o.status = 'Completed'
    WHERE c.user_id = ?
    GROUP BY c.id
    ORDER BY c.name ASC
    """
    rows = conn.execute(query, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_customer(user_id, name, email, phone, notes):
    conn = get_db()
    try:
        conn.execute("""
        INSERT INTO customers (user_id, name, email, phone, notes)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, name, email, phone, notes))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_customer(user_id, customer_id, name, email, phone, notes):
    conn = get_db()
    try:
        conn.execute("""
        UPDATE customers 
        SET name = ?, email = ?, phone = ?, notes = ?
        WHERE id = ? AND user_id = ?
        """, (name, email, phone, notes, customer_id, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_customer(user_id, customer_id):
    conn = get_db()
    conn.execute("DELETE FROM customers WHERE id = ? AND user_id = ?", (customer_id, user_id))
    conn.commit()
    conn.close()

def get_customer_history(user_id, customer_id):
    conn = get_db()
    # Check customer belongs to user
    cust = conn.execute("SELECT name FROM customers WHERE id = ? AND user_id = ?", (customer_id, user_id)).fetchone()
    if not cust:
        conn.close()
        return []
    
    query = """
    SELECT o.id as order_id, o.date, o.status, oi.quantity, oi.price, p.name as product_name
    FROM orders o
    JOIN order_items oi ON o.id = oi.order_id
    LEFT JOIN products p ON oi.product_id = p.id
    WHERE o.customer_id = ? AND o.user_id = ?
    ORDER BY o.date DESC
    """
    rows = conn.execute(query, (customer_id, user_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Order Helpers ──
def get_orders(user_id, status=None):
    conn = get_db()
    if status:
        query = """
        SELECT o.*, c.name as customer_name 
        FROM orders o 
        LEFT JOIN customers c ON o.customer_id = c.id 
        WHERE o.user_id = ? AND o.status = ?
        ORDER BY o.date DESC
        """
        rows = conn.execute(query, (user_id, status)).fetchall()
    else:
        query = """
        SELECT o.*, c.name as customer_name 
        FROM orders o 
        LEFT JOIN customers c ON o.customer_id = c.id 
        WHERE o.user_id = ?
        ORDER BY o.date DESC
        """
        rows = conn.execute(query, (user_id,)).fetchall()
        
    orders_list = []
    for r in rows:
        order = dict(r)
        items = conn.execute("""
        SELECT oi.*, p.name as product_name
        FROM order_items oi
        LEFT JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
        """, (order['id'],)).fetchall()
        order['items'] = [dict(i) for i in items]
        orders_list.append(order)
        
    conn.close()
    return orders_list

def add_order(user_id, customer_id, date, status, items):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION;")
        
        # Calculate total amount
        total_amount = sum(item['quantity'] * item['price'] for item in items)
        
        # Insert order
        cursor.execute("""
        INSERT INTO orders (user_id, customer_id, date, status, total_amount)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, customer_id, date, status, total_amount))
        order_id = cursor.lastrowid
        
        # Insert items and adjust stock if Completed
        for item in items:
            cursor.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (?, ?, ?, ?)
            """, (order_id, item['product_id'], item['quantity'], item['price']))
            
            if status == 'Completed':
                cursor.execute("""
                UPDATE products 
                SET stock = MAX(0, stock - ?) 
                WHERE id = ? AND user_id = ?
                """, (item['quantity'], item['product_id'], user_id))
                
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()

def update_order_status(user_id, order_id, new_status):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION;")
        
        # Fetch current order details
        cursor.execute("SELECT status FROM orders WHERE id = ? AND user_id = ?", (order_id, user_id))
        order_row = cursor.fetchone()
        if not order_row:
            conn.rollback()
            return False
        old_status = order_row[0]
        
        if old_status == new_status:
            conn.rollback()
            return True
            
        # Fetch order items to adjust stock
        cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = ?", (order_id,))
        items = cursor.fetchall()
        
        # Adjust stock depending on transitions
        # From Completed -> Cancelled/Pending: restore stock
        if old_status == 'Completed' and new_status in ('Pending', 'Cancelled'):
            for item in items:
                cursor.execute("""
                UPDATE products 
                SET stock = stock + ? 
                WHERE id = ? AND user_id = ?
                """, (item[1], item[0], user_id))
                
        # To Completed -> From Cancelled/Pending: deduct stock
        elif old_status in ('Pending', 'Cancelled') and new_status == 'Completed':
            for item in items:
                cursor.execute("""
                UPDATE products 
                SET stock = MAX(0, stock - ?) 
                WHERE id = ? AND user_id = ?
                """, (item[1], item[0], user_id))
                
        # Update order status
        cursor.execute("UPDATE orders SET status = ? WHERE id = ? AND user_id = ?", (new_status, order_id, user_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()

# ── Analytics & KPI Helpers ──
def get_dashboard_kpis(user_id):
    conn = get_db()
    
    # Total Revenue
    rev_row = conn.execute("SELECT SUM(total_amount) FROM orders WHERE user_id = ? AND status = 'Completed'", (user_id,)).fetchone()
    total_revenue = float(rev_row[0]) if rev_row[0] is not None else 0.0
    
    # Total Orders
    orders_row = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?", (user_id,)).fetchone()
    total_orders = int(orders_row[0]) if orders_row[0] is not None else 0
    
    # Unique Customers
    cust_row = conn.execute("SELECT COUNT(*) FROM customers WHERE user_id = ?", (user_id,)).fetchone()
    total_customers = int(cust_row[0]) if cust_row[0] is not None else 0
    
    # Net Profit
    profit_query = """
    SELECT SUM(oi.quantity * (oi.price - p.cost)) 
    FROM order_items oi 
    JOIN orders o ON oi.order_id = o.id 
    JOIN products p ON oi.product_id = p.id 
    WHERE o.user_id = ? AND o.status = 'Completed'
    """
    profit_row = conn.execute(profit_query, (user_id,)).fetchone()
    net_profit = float(profit_row[0]) if profit_row[0] is not None else 0.0
    
    # Margin
    profit_margin = float((net_profit / total_revenue * 100)) if total_revenue > 0 else 0.0
    
    # Top Product
    top_prod_query = """
    SELECT p.name, SUM(oi.quantity * oi.price) as revenue
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.id
    JOIN products p ON oi.product_id = p.id
    WHERE o.user_id = ? AND o.status = 'Completed'
    GROUP BY p.id
    ORDER BY revenue DESC
    LIMIT 1
    """
    top_prod_row = conn.execute(top_prod_query, (user_id,)).fetchone()
    top_product = top_prod_row[0] if top_prod_row else "N/A"
    
    # Low stock alerts count
    low_stock_row = conn.execute("SELECT COUNT(*) FROM products WHERE user_id = ? AND stock <= threshold", (user_id,)).fetchone()
    low_stock_alerts = int(low_stock_row[0]) if low_stock_row else 0
    
    conn.close()
    
    return {
        'total_revenue': round(total_revenue, 2),
        'total_orders': total_orders,
        'total_customers': total_customers,
        'net_profit': round(net_profit, 2),
        'profit_margin': round(profit_margin, 2),
        'top_product': top_product,
        'low_stock_alerts': low_stock_alerts
    }

def get_sales_trends(user_id):
    conn = get_db()
    
    # 1. Daily Sales
    daily_query = """
    SELECT date(o.date) as day, 
           SUM(o.total_amount) as revenue, 
           SUM(oi.quantity * (oi.price - p.cost)) as profit
    FROM orders o
    JOIN order_items oi ON o.id = oi.order_id
    JOIN products p ON oi.product_id = p.id
    WHERE o.user_id = ? AND o.status = 'Completed'
    GROUP BY day
    ORDER BY day ASC
    """
    daily = [dict(r) for r in conn.execute(daily_query, (user_id,)).fetchall()]
    
    # 2. Weekly Sales
    # SQLite strftime('%Y-%W', date) groups by week
    weekly_query = """
    SELECT strftime('%Y-W%W', o.date) as week, 
           SUM(o.total_amount) as revenue, 
           SUM(oi.quantity * (oi.price - p.cost)) as profit
    FROM orders o
    JOIN order_items oi ON o.id = oi.order_id
    JOIN products p ON oi.product_id = p.id
    WHERE o.user_id = ? AND o.status = 'Completed'
    GROUP BY week
    ORDER BY week ASC
    """
    weekly = [dict(r) for r in conn.execute(weekly_query, (user_id,)).fetchall()]
    
    # 3. Monthly Sales
    monthly_query = """
    SELECT strftime('%m-%Y', o.date) as month_val,
           strftime('%b %Y', o.date) as month, 
           SUM(o.total_amount) as revenue, 
           SUM(oi.quantity * (oi.price - p.cost)) as profit
    FROM orders o
    JOIN order_items oi ON o.id = oi.order_id
    JOIN products p ON oi.product_id = p.id
    WHERE o.user_id = ? AND o.status = 'Completed'
    GROUP BY month_val
    ORDER BY date(o.date) ASC
    """
    monthly = [dict(r) for r in conn.execute(monthly_query, (user_id,)).fetchall()]
    
    # 4. Yearly Sales
    yearly_query = """
    SELECT strftime('%Y', o.date) as year, 
           SUM(o.total_amount) as revenue, 
           SUM(oi.quantity * (oi.price - p.cost)) as profit
    FROM orders o
    JOIN order_items oi ON o.id = oi.order_id
    JOIN products p ON oi.product_id = p.id
    WHERE o.user_id = ? AND o.status = 'Completed'
    GROUP BY year
    ORDER BY year ASC
    """
    yearly = [dict(r) for r in conn.execute(yearly_query, (user_id,)).fetchall()]
    
    conn.close()
    
    return {
        'daily': daily,
        'weekly': weekly,
        'monthly': monthly,
        'yearly': yearly
    }

def import_csv_transactions(user_id, filepath):
    ext = filepath.rsplit('.', 1)[1].lower()
    df = pd.read_csv(filepath) if ext == 'csv' else pd.read_excel(filepath)
    
    # Normalize columns
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    col_map = {}
    for col in df.columns:
        if 'date' in col: col_map[col] = 'date'
        elif 'product' in col or 'name' in col: col_map[col] = 'product'
        elif 'qty' in col or 'quantity' in col: col_map[col] = 'quantity'
        elif 'price' in col or 'revenue' in col or 'sale' in col: col_map[col] = 'price'
        elif 'cost' in col: col_map[col] = 'cost'
        elif 'customer' in col or 'client' in col or 'buyer' in col: col_map[col] = 'customer'
        elif 'category' in col: col_map[col] = 'category'
        
    df = df.rename(columns=col_map)
    
    # Fill defaults
    if 'category' not in df.columns:
        df['category'] = 'General'
    if 'customer' not in df.columns:
        df['customer'] = 'Walk-in Customer'
        
    required = ['date', 'product', 'quantity', 'price', 'cost']
    for r in required:
        if r not in df.columns:
            raise ValueError(f"Missing column: '{r}'. Required: Date, Product, Quantity, Price, Cost")
            
    df['date'] = pd.to_datetime(df['date'], format='mixed').dt.strftime('%Y-%m-%d %H:%M:%S')
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0.0).astype(float)
    df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0.0).astype(float)
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN TRANSACTION;")
        
        # Ensure 'General' category exists
        cursor.execute("INSERT OR IGNORE INTO categories (user_id, name) VALUES (?, 'General')", (user_id,))
        
        for _, row in df.iterrows():
            customer_name = str(row['customer']).strip()
            product_name = str(row['product']).strip()
            category_name = str(row['category']).strip()
            
            # 1. Get or create category
            cursor.execute("INSERT OR IGNORE INTO categories (user_id, name) VALUES (?, ?)", (user_id, category_name))
            cursor.execute("SELECT id FROM categories WHERE user_id = ? AND name = ?", (user_id, category_name))
            cat_id = cursor.fetchone()[0]
            
            # 2. Get or create customer
            cursor.execute("INSERT OR IGNORE INTO customers (user_id, name) VALUES (?, ?)", (user_id, customer_name))
            cursor.execute("SELECT id FROM customers WHERE user_id = ? AND name = ?", (user_id, customer_name))
            cust_id = cursor.fetchone()[0]
            
            # 3. Get or create product
            cursor.execute("""
            INSERT OR IGNORE INTO products (user_id, name, category_id, sku, price, cost, stock, threshold)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, product_name, cat_id, f"SKU-{product_name[:3].upper()}", row['price'], row['cost'], 100, 10))
            
            cursor.execute("SELECT id, stock FROM products WHERE user_id = ? AND name = ?", (user_id, product_name))
            prod_row = cursor.fetchone()
            prod_id = prod_row[0]
            current_stock = prod_row[1]
            
            # Adjust product stock level
            new_stock = max(0, current_stock - row['quantity'])
            cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, prod_id))
            
            # 4. Insert completed order
            total_amount = row['quantity'] * row['price']
            cursor.execute("""
            INSERT INTO orders (user_id, customer_id, date, status, total_amount)
            VALUES (?, ?, ?, 'Completed', ?)
            """, (user_id, cust_id, row['date'], total_amount))
            order_id = cursor.lastrowid
            
            # 5. Insert order item
            cursor.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (?, ?, ?, ?)
            """, (order_id, prod_id, row['quantity'], row['price']))
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
