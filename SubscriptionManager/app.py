import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import mysql.connector
from werkzeug.security import check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET")

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

# --- AUTHENTICATION INTERFACES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid username or password credentials.")
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Gather structural parameters to compile frontend selections
    cursor.execute("SELECT * FROM Categories")
    categories = cursor.fetchall()
    
    cursor.execute("SELECT * FROM PaymentMethods WHERE user_id = %s", (session['user_id'],))
    methods = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('dashboard.html', categories=categories, methods=methods)


# =====================================================================
# RESTFUL JSON API ENDPOINTS (SUBSCRIPTION CRUD OPERATIONS)
# =====================================================================

@app.route('/api/subscriptions', methods=['GET'])
def get_subscriptions():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized endpoint access attempt"}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # READ: Join queries to enrich presentation metrics dynamically
    query = """
        SELECT s.*, c.category_name, p.method_name 
        FROM Subscriptions s
        LEFT JOIN Categories c ON s.category_id = c.category_id
        LEFT JOIN PaymentMethods p ON s.method_id = p.method_id
        WHERE s.user_id = %s
    """
    cursor.execute(query, (session['user_id'],))
    records = cursor.fetchall()
    
    # Process date classes into strings to prevent serialisation conflicts
    for r in records:
        if r['start_date']: r['start_date'] = r['start_date'].strftime('%Y-%m-%d')
        if r['next_billing_date']: r['next_billing_date'] = r['next_billing_date'].strftime('%Y-%m-%d')
        r['cost'] = float(r['cost'])
        
    cursor.close()
    conn.close()
    return jsonify(records)

@app.route('/api/subscriptions', methods=['POST'])
def create_subscription():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized operation"}), 401
        
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # CREATE: Safely parameterised insertion query matrix
    sql = """
        INSERT INTO Subscriptions (user_id, service_name, category_id, method_id, cost, billing_cycle, start_date, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        session['user_id'], data['service_name'], data['category_id'],
        data['method_id'], data['cost'], data['billing_cycle'], data['start_date'], 'Active'
    )
    cursor.execute(sql, values)
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True, "msg": "Resource generated successfully."}), 201

@app.route('/api/subscriptions/<int:sub_id>', methods=['PUT'])
def update_subscription(sub_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized operation"}), 401
        
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # UPDATE: Modify existing operational database states
    sql = """
        UPDATE Subscriptions 
        SET service_name=%s, category_id=%s, method_id=%s, cost=%s, billing_cycle=%s, start_date=%s, status=%s
        WHERE subscription_id=%s AND user_id=%s
    """
    values = (
        data['service_name'], data['category_id'], data['method_id'],
        data['cost'], data['billing_cycle'], data['start_date'], data['status'], sub_id, session['user_id']
    )
    cursor.execute(sql, values)
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True, "msg": "Resource state transitioned accurately."})

@app.route('/api/subscriptions/<int:sub_id>', methods=['DELETE'])
def delete_subscription(sub_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized operation"}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # DELETE: Erase target identity bounds cleanly
    cursor.execute("DELETE FROM Subscriptions WHERE subscription_id = %s AND user_id = %s", (sub_id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True, "msg": "Resource destroyed successfully."})

if __name__ == '__main__':
    app.run(debug=True, port=5000)