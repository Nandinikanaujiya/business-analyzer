import os, io, base64, json, uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
app.secret_key = 'biz_analyzer_secret_2024'
UPLOAD_FOLDER = 'uploads'
REPORTS_FOLDER = 'reports'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

# ── Simple in-memory user store ──
USERS = {}
USER_REPORTS = {}  # username -> list of report metadata

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ────────────────────────────────────────────
#  AUTH ROUTES
# ────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('Please fill all fields.', 'error')
        elif username in USERS:
            flash('Username already exists.', 'error')
        else:
            USERS[username] = generate_password_hash(password)
            USER_REPORTS[username] = []
            flash('Account created! Please login.', 'success')
            return redirect(url_for('login'))
    return render_template('auth.html', mode='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if username in USERS and check_password_hash(USERS[username], password):
            session['user'] = username
            if username not in USER_REPORTS:
                USER_REPORTS[username] = []
            return redirect(url_for('index'))
        flash('Invalid credentials.', 'error')
    return render_template('auth.html', mode='login')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# ────────────────────────────────────────────
#  MAIN ROUTES
# ────────────────────────────────────────────
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    user = session['user']
    reports = USER_REPORTS.get(user, [])[-5:][::-1]
    return render_template('index.html', user=user, reports=reports)

@app.route('/upload', methods=['POST'])
def upload():
    if 'user' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    f = request.files['file']
    if not f.filename or not allowed_file(f.filename):
        return jsonify({'error': 'Invalid file type. Use CSV or Excel.'}), 400

    filename = secure_filename(f.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    f.save(filepath)

    try:
        result = analyze(filepath)
        result['filename'] = filename

        # Save report record
        user = session['user']
        rid = str(uuid.uuid4())[:8]
        meta = {'id': rid, 'file': filename, 'date': datetime.now().strftime('%d %b %Y, %H:%M'),
                'revenue': result['summary']['total_revenue'], 'profit': result['summary']['net_profit']}
        USER_REPORTS.setdefault(user, []).append(meta)
        session['last_result'] = rid
        session['last_file'] = filepath
        result['report_id'] = rid
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/download_report', methods=['POST'])
def download_report():
    if 'user' not in session:
        return redirect(url_for('login'))
    data = request.json
    filepath = generate_pdf(data, session.get('user', 'User'))
    return send_file(filepath, as_attachment=True, download_name='business_report.pdf')

# ────────────────────────────────────────────
#  ANALYSIS ENGINE
# ────────────────────────────────────────────
def analyze(filepath):
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
    df = df.rename(columns=col_map)

    required = ['date', 'product', 'quantity', 'price', 'cost']
    for r in required:
        if r not in df.columns:
            raise ValueError(f"Missing column: '{r}'. Required: Date, Product, Quantity, Price, Cost")

    df['date'] = pd.to_datetime(df['date'], format='mixed')
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
    df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0)
    df['revenue'] = df['quantity'] * df['price']
    df['total_cost'] = df['quantity'] * df['cost']
    df['profit'] = df['revenue'] - df['total_cost']
    df['month'] = df['date'].dt.to_period('M')
    df['month_str'] = df['date'].dt.strftime('%b %Y')

    # ── Summary ──
    total_revenue = float(np.round(df['revenue'].sum(), 2))
    total_cost = float(np.round(df['total_cost'].sum(), 2))
    net_profit = float(np.round(df['profit'].sum(), 2))
    profit_margin = float(np.round((net_profit / total_revenue * 100) if total_revenue else 0, 2))

    # ── Monthly summary ──
    monthly = df.groupby('month_str').agg(
        revenue=('revenue', 'sum'), cost=('total_cost', 'sum'), profit=('profit', 'sum')
    ).reset_index()
    monthly = monthly.sort_values('month_str')
    monthly['growth'] = monthly['profit'].pct_change().fillna(0) * 100
    monthly['growth'] = monthly['growth'].round(2)

    # ── Next month prediction (linear regression) ──
    if len(monthly) >= 2:
        x = np.arange(len(monthly))
        y = monthly['profit'].values
        slope, intercept = np.polyfit(x, y, 1)
        predicted = float(np.round(intercept + slope * len(monthly), 2))
        trend = 'up' if slope > 0 else 'down'
    else:
        predicted = float(monthly['profit'].iloc[-1]) if len(monthly) else 0
        trend = 'stable'

    # ── Product analysis ──
    products = df.groupby('product').agg(
        quantity=('quantity', 'sum'), revenue=('revenue', 'sum'), profit=('profit', 'sum')
    ).reset_index().sort_values('revenue', ascending=False)
    top_product = products.iloc[0]['product'] if len(products) else 'N/A'

    # ── AI Suggestions ──
    suggestions = generate_suggestions(monthly, products, net_profit, profit_margin, trend)

    # ── Charts ──
    charts = {}
    charts['bar'] = make_bar_chart(products)
    charts['line'] = make_line_chart(monthly)
    charts['pie'] = make_pie_chart(products)

    return {
        'summary': {
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'net_profit': net_profit,
            'profit_margin': profit_margin,
            'total_transactions': len(df),
        },
        'monthly': monthly.to_dict(orient='records'),
        'products': products.head(10).to_dict(orient='records'),
        'top_product': top_product,
        'prediction': {'next_month': predicted, 'trend': trend},
        'suggestions': suggestions,
        'charts': charts,
    }

def generate_suggestions(monthly, products, net_profit, margin, trend):
    tips = []
    if len(monthly) >= 2:
        last_growth = float(monthly['growth'].iloc[-1])
        if last_growth > 10:
            tips.append(f"🚀 Great momentum! Your profit grew by <b>{last_growth:.1f}%</b> last month. Keep the strategy going!")
        elif last_growth > 0:
            tips.append(f"📈 Steady progress — profit increased by <b>{last_growth:.1f}%</b>. There's room to push harder.")
        else:
            tips.append(f"⚠️ Profit dipped by <b>{abs(last_growth):.1f}%</b> last month. Review your pricing and high-cost items.")

    if len(products) >= 1:
        top = products.iloc[0]
        tips.append(f"🏆 <b>{top['product']}</b> is your star performer with ₹{top['revenue']:,.0f} revenue. Invest more in its marketing.")

    if len(products) >= 2:
        low = products.iloc[-1]
        tips.append(f"🔍 <b>{low['product']}</b> has the lowest sales. Consider a promotion or review its pricing.")

    if margin < 20:
        tips.append(f"💡 Your profit margin is <b>{margin:.1f}%</b> — consider reducing operational costs or adjusting pricing.")
    elif margin > 40:
        tips.append(f"✅ Excellent margin of <b>{margin:.1f}%</b>! You have headroom to invest in growth.")

    if trend == 'up':
        tips.append("📊 Sales trend is <b>upward</b> — your predicted next-month profit looks positive. Scale up inventory.")
    elif trend == 'down':
        tips.append("📉 Sales trend is <b>declining</b>. Identify underperforming products and cut unnecessary costs.")

    return tips

# ────────────────────────────────────────────
#  CHART GENERATORS
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

def make_bar_chart(products):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.patch.set_facecolor(CHART_STYLE['bg'])
    ax.set_facecolor(CHART_STYLE['surface'])
    names = [str(p)[:12] for p in products['product'].head(8)]
    revs = products['revenue'].head(8).values
    colors_list = [CHART_STYLE['accent']] + ['#4a90d9'] * (len(names)-1)
    bars = ax.bar(names, revs, color=colors_list, edgecolor='none', width=0.6)
    for bar, val in zip(bars, revs):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(revs)*0.01,
                f'₹{val:,.0f}', ha='center', va='bottom', color=CHART_STYLE['text'], fontsize=8)
    ax.set_xlabel('Product', color=CHART_STYLE['muted'], fontsize=10)
    ax.set_ylabel('Revenue (₹)', color=CHART_STYLE['muted'], fontsize=10)
    ax.set_title('Revenue by Product', color=CHART_STYLE['text'], fontsize=13, fontweight='bold', pad=15)
    ax.tick_params(colors=CHART_STYLE['muted'], labelsize=9)
    ax.spines[:].set_visible(False)
    ax.yaxis.grid(True, color='#2a2d3a', linewidth=0.5)
    ax.set_axisbelow(True)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    return fig_to_b64(fig)

def make_line_chart(monthly):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.patch.set_facecolor(CHART_STYLE['bg'])
    ax.set_facecolor(CHART_STYLE['surface'])
    x = range(len(monthly))
    profits = monthly['profit'].values
    ax.fill_between(x, profits, alpha=0.15, color=CHART_STYLE['green'])
    ax.plot(x, profits, color=CHART_STYLE['green'], linewidth=2.5, marker='o',
            markersize=6, markerfacecolor=CHART_STYLE['bg'], markeredgecolor=CHART_STYLE['green'], markeredgewidth=2)
    for i, (xi, yi) in enumerate(zip(x, profits)):
        ax.annotate(f'₹{yi:,.0f}', (xi, yi), textcoords='offset points', xytext=(0, 10),
                    ha='center', color=CHART_STYLE['text'], fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(monthly['month_str'].tolist(), rotation=30, ha='right')
    ax.set_ylabel('Profit (₹)', color=CHART_STYLE['muted'], fontsize=10)
    ax.set_title('Monthly Profit Trend', color=CHART_STYLE['text'], fontsize=13, fontweight='bold', pad=15)
    ax.tick_params(colors=CHART_STYLE['muted'], labelsize=9)
    ax.spines[:].set_visible(False)
    ax.yaxis.grid(True, color='#2a2d3a', linewidth=0.5)
    ax.set_axisbelow(True)
    plt.tight_layout()
    return fig_to_b64(fig)

def make_pie_chart(products):
    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor(CHART_STYLE['bg'])
    ax.set_facecolor(CHART_STYLE['bg'])
    labels = [str(p)[:14] for p in products['product'].head(6)]
    sizes = products['revenue'].head(6).values
    palette = ['#6c63ff','#00d4aa','#ff6b6b','#f7b731','#45aaf2','#fd9644'][:len(labels)]
    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, autopct='%1.1f%%',
        colors=palette, startangle=140,
        wedgeprops={'edgecolor': CHART_STYLE['bg'], 'linewidth': 2},
        pctdistance=0.82
    )
    for at in autotexts:
        at.set_color(CHART_STYLE['text'])
        at.set_fontsize(9)
    legend = ax.legend(wedges, labels, loc='lower center', bbox_to_anchor=(0.5, -0.15),
                       ncol=3, fontsize=9, frameon=False, labelcolor=CHART_STYLE['text'])
    ax.set_title('Product Revenue Contribution', color=CHART_STYLE['text'], fontsize=13, fontweight='bold', pad=10)
    plt.tight_layout()
    return fig_to_b64(fig)

# ────────────────────────────────────────────
#  PDF REPORT
# ────────────────────────────────────────────
def generate_pdf(data, username):
    path = os.path.join(REPORTS_FOLDER, f'report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=22, textColor=colors.HexColor('#6c63ff'), spaceAfter=6)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#333'), spaceBefore=16, spaceAfter=6)
    body = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#444'), spaceAfter=4)

    story.append(Paragraph("📊 Business Growth Analyzer", title_style))
    story.append(Paragraph(f"Report generated for <b>{username}</b> — {datetime.now().strftime('%d %B %Y, %H:%M')}", body))
    story.append(Spacer(1, 0.2*inch))

    # Summary table
    s = data.get('summary', {})
    story.append(Paragraph("Financial Summary", h2))
    tdata = [
        ['Metric', 'Value'],
        ['Total Revenue', f"₹{s.get('total_revenue', 0):,.2f}"],
        ['Total Cost', f"₹{s.get('total_cost', 0):,.2f}"],
        ['Net Profit', f"₹{s.get('net_profit', 0):,.2f}"],
        ['Profit Margin', f"{s.get('profit_margin', 0):.2f}%"],
        ['Transactions', str(s.get('total_transactions', 0))],
    ]
    t = Table(tdata, colWidths=[3*inch, 3*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#6c63ff')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f5f5ff'), colors.white]),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#dddddd')),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.2*inch))

    # Prediction
    pred = data.get('prediction', {})
    story.append(Paragraph("Next Month Prediction", h2))
    story.append(Paragraph(f"Predicted profit: <b>₹{pred.get('next_month', 0):,.2f}</b> — Trend: <b>{pred.get('trend', 'N/A').upper()}</b>", body))
    story.append(Spacer(1, 0.1*inch))

    # AI Suggestions
    story.append(Paragraph("AI Business Insights", h2))
    for tip in data.get('suggestions', []):
        clean_tip = tip.replace('<b>', '').replace('</b>', '')
        story.append(Paragraph(f"• {clean_tip}", body))
    story.append(Spacer(1, 0.15*inch))

    # Charts
    story.append(Paragraph("Visual Analytics", h2))
    for chart_key in ['bar', 'line', 'pie']:
        b64 = data.get('charts', {}).get(chart_key)
        if b64:
            img_data = base64.b64decode(b64)
            buf = io.BytesIO(img_data)
            img = RLImage(buf, width=5.5*inch, height=3.1*inch)
            story.append(img)
            story.append(Spacer(1, 0.1*inch))

    doc.build(story)
    return path

if __name__ == '__main__':
    app.run(debug=True, port=5050)
