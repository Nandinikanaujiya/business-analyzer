import os
import sqlite3
import database
from werkzeug.security import generate_password_hash

TEST_DB = 'database.db'

def run_tests():
    print("[TEST] Running Database Integration Tests...")
    
    # 1. Clean and initialize database
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
            print("  [OK] Old test database cleared.")
        except PermissionError:
            print("  [INFO] database.db is currently locked, testing existing connection...")
            
    database.init_db()
    print("  [OK] Database initialized successfully.")
    
    # 2. Register test user
    pwd_hash = generate_password_hash("testpass")
    uid = database.register_user("testuser", pwd_hash, "test@example.com", "9876543210")
    assert uid is not None, "Failed to register test user."
    print(f"  [OK] User registered with ID: {uid}")
    
    # Duplicate username check
    dup_uid = database.register_user("testuser", pwd_hash, "another@example.com", "000000000")
    assert dup_uid is None, "Integrity constraint failed: duplicate user registered."
    print("  [OK] Duplicate username block verified.")
    
    # 3. Add Category
    cat_success = database.add_category(uid, "Electronics")
    assert cat_success, "Failed to add category."
    categories = database.get_categories(uid)
    assert len(categories) >= 2, "Default and custom categories not loaded."
    print(f"  [OK] Categories verified: {[c['name'] for c in categories]}")
    
    # Get Electronics ID
    cat_id = [c['id'] for c in categories if c['name'] == 'Electronics'][0]
    
    # 4. Add Product
    prod_success = database.add_product(uid, "Laptop Pro", cat_id, "SKU-LAP", 50000.0, 35000.0, 10, 5)
    assert prod_success, "Failed to add product."
    products = database.get_products(uid)
    assert len(products) == 1, "Product count mismatch."
    assert products[0]['stock'] == 10, "Initial stock mismatch."
    print(f"  [OK] Product 'Laptop Pro' added with stock: {products[0]['stock']}")
    
    prod_id = products[0]['id']
    
    # 5. Add Customer
    cust_success = database.add_customer(uid, "Devendra Kumar", "dev@example.com", "9998887776", "Regular customer")
    assert cust_success, "Failed to add customer."
    customers = database.get_customers(uid)
    assert len(customers) == 1, "Customer count mismatch."
    print(f"  [OK] Customer added: {customers[0]['name']}")
    
    cust_id = customers[0]['id']
    
    # 6. Place a Pending Order
    # Items: (product_id, quantity, price)
    order_items = [{'product_id': prod_id, 'quantity': 2, 'price': 50000.0}]
    order_success = database.add_order(uid, cust_id, "2026-06-26 10:00:00", "Pending", order_items)
    assert order_success, "Failed to add order."
    
    # Verify stock is unchanged for pending orders
    products = database.get_products(uid)
    assert products[0]['stock'] == 10, "Stock should not change for Pending orders."
    print("  [OK] Pending order placed. Stock level unchanged (remains 10).")
    
    # Find order ID
    orders = database.get_orders(uid)
    assert len(orders) == 1, "Order count mismatch."
    order_id = orders[0]['id']
    
    # 7. Complete the Order and verify stock deduction
    status_success = database.update_order_status(uid, order_id, "Completed")
    assert status_success, "Failed to update status."
    
    products = database.get_products(uid)
    assert products[0]['stock'] == 8, f"Stock mismatch after Completion. Expected 8, got {products[0]['stock']}"
    print(f"  [OK] Order completed. Stock decremented successfully (new stock: {products[0]['stock']}).")
    
    # 8. Cancel the Order and verify stock restoration
    status_success = database.update_order_status(uid, order_id, "Cancelled")
    assert status_success, "Failed to update status."
    
    products = database.get_products(uid)
    assert products[0]['stock'] == 10, f"Stock mismatch after Cancel. Expected 10, got {products[0]['stock']}"
    print(f"  [OK] Order cancelled. Stock restored successfully (new stock: {products[0]['stock']}).")
    
    # 9. Ingest test CSV validation
    print("  [OK] Database testing completed successfully!")

if __name__ == '__main__':
    run_tests()
