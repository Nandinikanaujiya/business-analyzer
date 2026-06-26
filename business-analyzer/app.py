import os, io, base64, json, uuid, random, string
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
import database
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
import warnings
warnings.filterwarnings('ignore')
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables from .env manually
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if not os.path.exists(env_path):
        env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ[key.strip()] = val.strip()

load_env()

def send_email_otp(to_email, otp_code):
    smtp_email = os.environ.get('SMTP_EMAIL')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    if not smtp_email or not smtp_password or smtp_email == 'your-email@gmail.com':
        print(f"[Simulated SMTP] Credentials missing. Code: {otp_code}")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_email
        msg['To'] = to_email
        msg['Subject'] = "🔐 OTP Verification - Business ERP Suite"
        
        body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #0f1117; color: #e0e0e0; padding: 24px;">
            <div style="max-width: 480px; margin: 0 auto; background-color: #1a1d27; border: 1px solid #2a2d3a; border-radius: 12px; padding: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
              <h2 style="color: #6c63ff; text-align: center; font-family: 'Syne', sans-serif;">Business ERP Suite</h2>
              <hr style="border: 0; border-top: 1px solid #2a2d3a; margin: 20px 0;"/>
              <p>Hello,</p>
              <p>Thank you for registering. Use the following One-Time Password (OTP) to complete your signup process:</p>
              <div style="background-color: #0d0f18; border: 1px solid #2a2d3a; padding: 16px; border-radius: 8px; text-align: center; margin: 24px 0;">
                <span style="font-size: 28px; letter-spacing: 4px; font-weight: bold; color: #00d4aa;">{otp_code}</span>
              </div>
              <p style="font-size: 12px; color: #888;">This OTP is valid for 10 minutes. If you did not request this code, please ignore this email.</p>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))
        
        # Connect and send via Gmail SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.sendmail(smtp_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

app = Flask(__name__)
app.secret_key = 'biz_analyzer_secure_secret_2026'
UPLOAD_FOLDER = 'uploads'
REPORTS_FOLDER = 'reports'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

# Initialize database
database.init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ────────────────────────────────────────────
#  AUTH ROUTES
# ────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Form values order: Email/Phone -> OTP -> Username -> Password -> CAPTCHA
        email_or_phone = request.form.get('email_or_phone', '').strip()
        otp = request.form.get('otp', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        captcha = request.form.get('captcha', '').strip()
        
        # Validations
        if not email_or_phone or not otp or not username or not password or not captcha:
            flash('Please fill all fields.', 'error')
            return redirect(url_for('register'))
            
        # Verify OTP
        if otp != session.get('otp'):
            flash('Invalid OTP code verification.', 'error')
            return redirect(url_for('register'))
            
        # Verify Captcha
        if captcha.upper() != session.get('captcha', '').upper():
            flash('Incorrect CAPTCHA code. Try again.', 'error')
            return redirect(url_for('register'))
            
        # Check Username
        existing = database.get_user_by_username(username)
        if existing:
            flash('Username already exists.', 'error')
            return redirect(url_for('register'))
            
        # Determine email vs phone
        email = email_or_phone if '@' in email_or_phone else None
        phone = email_or_phone if '@' not in email_or_phone else None
        
        # Save user
        pwd_hash = generate_password_hash(password)
        user_id = database.register_user(username, pwd_hash, email, phone)
        if user_id:
            # Clear sessions
            session.pop('otp', None)
            session.pop('captcha', None)
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Failed to register. Username might be taken.', 'error')
            return redirect(url_for('register'))
            
    # GET: Generate new Captcha
    captcha_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    session['captcha'] = captcha_chars
    return render_template('auth.html', mode='register', captcha=captcha_chars)

@app.route('/send_otp', methods=['POST'])
def send_otp():
    data = request.json or {}
    email_or_phone = data.get('email_or_phone', '').strip()
    if not email_or_phone:
        return jsonify({'error': 'Please provide Email or Phone Number.'}), 400
        
    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    
    is_email = '@' in email_or_phone
    email_sent = False
    
    if is_email:
        email_sent = send_email_otp(email_or_phone, otp)
        
    if is_email and email_sent:
        return jsonify({
            'success': True,
            'message': f'Verification OTP sent to {email_or_phone}!',
            'simulated': False
        })
    else:
        msg = 'OTP sent successfully! (Simulated)'
        if is_email:
            msg = 'SMTP credentials missing or incorrect. Falling back to simulated verification.'
        return jsonify({
            'success': True,
            'message': msg,
            'otp': otp,
            'simulated': True
        })

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = database.get_user_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            session['user'] = username
            session['user_id'] = user['id']
            return redirect(url_for('index'))
            
        flash('Invalid credentials.', 'error')
    return render_template('auth.html', mode='login')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    return redirect(url_for('login'))

# ────────────────────────────────────────────
#  DASHBOARD & DATA ROUTES
# ────────────────────────────────────────────
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user=session['user'])

@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    f = request.files['file']
    if not f.filename or not allowed_file(f.filename):
        return jsonify({'error': 'Invalid file type. Use CSV or Excel.'}), 400
        
    filename = f"{uuid.uuid4().hex}_{secure_filename(f.filename)}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    f.save(filepath)
    
    try:
        user_id = session['user_id']
        database.import_csv_transactions(user_id, filepath)
        
        # Load aggregates and return JSON
        result = get_dashboard_data(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

def secure_filename(filename):
    return filename.replace(' ', '_').replace('/', '_').replace('\\', '_')

def get_dashboard_data(user_id):
    kpis = database.get_dashboard_kpis(user_id)
    trends = database.get_sales_trends(user_id)
    products = database.get_products(user_id)
    
    # Generate Suggestions
    suggestions = generate_suggestions(trends['monthly'], products, kpis['net_profit'], kpis['profit_margin'])
    
    return {
        'summary': kpis,
        'trends': trends,
        'products': products[:10], # Top 10 for table display
        'top_product': kpis['top_product'],
        'suggestions': suggestions
    }

def generate_suggestions(monthly, products, net_profit, margin):
    tips = []
    
    # Growth checks
    if len(monthly) >= 2:
        prev_profit = monthly[-2]['profit']
        curr_profit = monthly[-1]['profit']
        if prev_profit > 0:
            growth = ((curr_profit - prev_profit) / prev_profit) * 100
            if growth > 10:
                tips.append(f"🚀 Great momentum! Your profit grew by <b>{growth:.1f}%</b> last month. Keep the strategy going!")
            elif growth > 0:
                tips.append(f"📈 Steady progress — profit increased by <b>{growth:.1f}%</b>. There's room to push harder.")
            else:
                tips.append(f"⚠️ Profit dipped by <b>{abs(growth):.1f}%</b> last month. Review your pricing and high-cost items.")
                
    # Product checks
    if len(products) >= 1:
        top = products[0]
        tips.append(f"🏆 <b>{top['name']}</b> is your star performer with a price of ₹{top['price']:,.0f}. Keep stock levels optimized.")
        
    if len(products) >= 2:
        # Find low performing product
        low = products[-1]
        tips.append(f"🔍 <b>{low['name']}</b> has lower sales traction. Consider a promotion or bundle deal.")
        
    # Margin checks
    if margin < 20:
        tips.append(f"💡 Your profit margin is <b>{margin:.1f}%</b> — consider reducing operational costs or adjusting pricing.")
    elif margin > 40:
        tips.append(f"✅ Excellent margin of <b>{margin:.1f}%</b>! You have headroom to invest in growth.")
        
    return tips

# ────────────────────────────────────────────
#  PRODUCT MANAGEMENT APIs
# ────────────────────────────────────────────
@app.route('/api/categories', methods=['GET', 'POST'])
def api_categories():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    if request.method == 'POST':
        data = request.json or {}
        name = data.get('name', '').strip()
        if not name: return jsonify({'error': 'Name is required'}), 400
        success = database.add_category(user_id, name)
        if success: return jsonify({'success': True})
        return jsonify({'error': 'Category already exists'}), 400
    return jsonify(database.get_categories(user_id))

@app.route('/api/products', methods=['GET', 'POST'])
def api_products():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    if request.method == 'POST':
        data = request.json or {}
        name = data.get('name', '').strip()
        category_id = data.get('category_id')
        sku = data.get('sku', '').strip()
        price = float(data.get('price', 0.0))
        cost = float(data.get('cost', 0.0))
        stock = int(data.get('stock', 0))
        threshold = int(data.get('threshold', 10))
        
        if not name: return jsonify({'error': 'Product name is required'}), 400
        success = database.add_product(user_id, name, category_id, sku, price, cost, stock, threshold)
        if success: return jsonify({'success': True})
        return jsonify({'error': 'Product name already exists'}), 400
        
    return jsonify(database.get_products(user_id))

@app.route('/api/products/<int:pid>', methods=['PUT', 'DELETE'])
def api_product_detail(pid):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    
    if request.method == 'DELETE':
        database.delete_product(user_id, pid)
        return jsonify({'success': True})
        
    # PUT
    data = request.json or {}
    name = data.get('name', '').strip()
    category_id = data.get('category_id')
    sku = data.get('sku', '').strip()
    price = float(data.get('price', 0.0))
    cost = float(data.get('cost', 0.0))
    stock = int(data.get('stock', 0))
    threshold = int(data.get('threshold', 10))
    
    if not name: return jsonify({'error': 'Product name is required'}), 400
    success = database.update_product(user_id, pid, name, category_id, sku, price, cost, stock, threshold)
    if success: return jsonify({'success': True})
    return jsonify({'error': 'Failed to update. Name might conflict.'}), 400

# ────────────────────────────────────────────
#  CUSTOMER MANAGEMENT APIs
# ────────────────────────────────────────────
@app.route('/api/customers', methods=['GET', 'POST'])
def api_customers():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    
    if request.method == 'POST':
        data = request.json or {}
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        notes = data.get('notes', '').strip()
        
        if not name: return jsonify({'error': 'Customer name is required'}), 400
        success = database.add_customer(user_id, name, email, phone, notes)
        if success: return jsonify({'success': True})
        return jsonify({'error': 'Customer name already exists'}), 400
        
    return jsonify(database.get_customers(user_id))

@app.route('/api/customers/<int:cid>', methods=['PUT', 'DELETE'])
def api_customer_detail(cid):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    
    if request.method == 'DELETE':
        database.delete_customer(user_id, cid)
        return jsonify({'success': True})
        
    # PUT
    data = request.json or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    notes = data.get('notes', '').strip()
    
    if not name: return jsonify({'error': 'Customer name is required'}), 400
    success = database.update_customer(user_id, cid, name, email, phone, notes)
    if success: return jsonify({'success': True})
    return jsonify({'error': 'Failed to update. Name might conflict.'}), 400

@app.route('/api/customers/<int:cid>/history', methods=['GET'])
def api_customer_history(cid):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    return jsonify(database.get_customer_history(user_id, cid))

# ────────────────────────────────────────────
#  ORDER MANAGEMENT APIs
# ────────────────────────────────────────────
@app.route('/api/orders', methods=['GET', 'POST'])
def api_orders():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    
    if request.method == 'POST':
        data = request.json or {}
        customer_id = data.get('customer_id')
        date = data.get('date') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = data.get('status', 'Pending')
        items = data.get('items', [])
        
        if not customer_id: return jsonify({'error': 'Customer is required'}), 400
        if not items: return jsonify({'error': 'At least one product is required'}), 400
        
        success = database.add_order(user_id, customer_id, date, status, items)
        if success: return jsonify({'success': True})
        return jsonify({'error': 'Failed to place order. Check stock availability.'}), 400
        
    status = request.args.get('status')
    return jsonify(database.get_orders(user_id, status))

@app.route('/api/orders/<int:oid>/status', methods=['PUT'])
def api_order_status(oid):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    
    data = request.json or {}
    status = data.get('status')
    if status not in ('Pending', 'Completed', 'Cancelled'):
        return jsonify({'error': 'Invalid status'}), 400
        
    success = database.update_order_status(user_id, oid, status)
    if success: return jsonify({'success': True})
    return jsonify({'error': 'Failed to update order status'}), 400

@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(get_dashboard_data(session['user_id']))

# ────────────────────────────────────────────
#  PDF REPORT GENERATION
# ────────────────────────────────────────────
CHART_STYLE = {
    'bg': '#0f1117', 'surface': '#1a1d27', 'accent': '#6c63ff',
    'green': '#00d4aa', 'red': '#ff6b6b', 'text': '#e0e0e0', 'muted': '#888'
}

def fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=130, facecolor=CHART_STYLE['bg'])
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return b64

def generate_pdf_charts(trends, products):
    charts = {}
    
    # 1. Bar Chart: Product Revenue
    if products:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        fig.patch.set_facecolor(CHART_STYLE['bg'])
        ax.set_facecolor(CHART_STYLE['surface'])
        names = [str(p['name'])[:12] for p in products[:8]]
        revs = [p['price'] * p['stock'] for p in products[:8]] # proxy revenue or pricing
        colors_list = [CHART_STYLE['accent']] + ['#4a90d9'] * (len(names)-1)
        ax.bar(names, revs, color=colors_list, width=0.6)
        ax.set_title('Products Valuation (Price * Stock)', color=CHART_STYLE['text'], fontweight='bold')
        ax.tick_params(colors=CHART_STYLE['muted'])
        ax.spines[:].set_visible(False)
        plt.xticks(rotation=30, ha='right')
        plt.tight_layout()
        charts['bar'] = fig_to_b64(fig)
        
    # 2. Line Chart: Monthly Profit
    monthly = trends.get('monthly', [])
    if monthly:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        fig.patch.set_facecolor(CHART_STYLE['bg'])
        ax.set_facecolor(CHART_STYLE['surface'])
        x = range(len(monthly))
        profits = [m['profit'] for m in monthly]
        ax.plot(x, profits, color=CHART_STYLE['green'], marker='o', linewidth=2.5)
        ax.set_xticks(list(x))
        ax.set_xticklabels([m['month'] for m in monthly], rotation=30, ha='right')
        ax.set_title('Monthly Profit Trend', color=CHART_STYLE['text'], fontweight='bold')
        ax.tick_params(colors=CHART_STYLE['muted'])
        ax.spines[:].set_visible(False)
        plt.tight_layout()
        charts['line'] = fig_to_b64(fig)
        
    return charts

@app.route('/download_report', methods=['POST'])
def download_report():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    kpis = database.get_dashboard_kpis(user_id)
    trends = database.get_sales_trends(user_id)
    products = database.get_products(user_id)
    suggestions = generate_suggestions(trends['monthly'], products, kpis['net_profit'], kpis['profit_margin'])
    
    # Generate charts dynamically for the PDF
    charts = generate_pdf_charts(trends, products)
    
    path = os.path.join(REPORTS_FOLDER, f'report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=22, textColor=colors.HexColor('#6c63ff'), spaceAfter=6)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#333'), spaceBefore=16, spaceAfter=6)
    body = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#444'), spaceAfter=4)
    
    story.append(Paragraph("📊 Business Growth Analyzer", title_style))
    story.append(Paragraph(f"Report generated for <b>{session['user']}</b> — {datetime.now().strftime('%d %B %Y, %H:%M')}", body))
    story.append(Spacer(1, 0.2*inch))
    
    # Financial Summary Table
    story.append(Paragraph("Financial Summary", h2))
    tdata = [
        ['Metric', 'Value'],
        ['Total Revenue', f"₹{kpis['total_revenue']:,.2f}"],
        ['Total Orders', str(kpis['total_orders'])],
        ['Customers', str(kpis['total_customers'])],
        ['Net Profit', f"₹{kpis['net_profit']:,.2f}"],
        ['Profit Margin', f"{kpis['profit_margin']:.2f}%"],
    ]
    t = Table(tdata, colWidths=[3*inch, 3*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#6c63ff')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f5f5ff'), colors.white]),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#dddddd')),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.2*inch))
    
    # AI Suggestions
    story.append(Paragraph("AI Business Insights", h2))
    for tip in suggestions:
        clean_tip = tip.replace('<b>', '').replace('</b>', '')
        story.append(Paragraph(f"• {clean_tip}", body))
    story.append(Spacer(1, 0.2*inch))
    
    # Charts
    story.append(Paragraph("Visual Analytics", h2))
    for chart_key in ['bar', 'line']:
        b64 = charts.get(chart_key)
        if b64:
            img_data = base64.b64decode(b64)
            buf = io.BytesIO(img_data)
            img = RLImage(buf, width=5.5*inch, height=3.1*inch)
            story.append(img)
            story.append(Spacer(1, 0.1*inch))
            
    doc.build(story)
    return send_file(path, as_attachment=True, download_name='business_report.pdf')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
