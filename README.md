# 📊 Business ERP Suite & Growth Analyzer

A full-stack, highly optimized web application for business owners to manage operations, track inventory, handle orders, and get **instant sales analytics, chronological profit trends, and AI-powered insights**.

---

## ✨ Key Features

- 🔐 **Secure Multi-Field Registration**:
  - Exact registration order: Email or Phone -> Simulated OTP verification -> Username -> Password -> CAPTCHA.
  - Interactive toast alerts to simulate OTP messaging.
  - Hashed credentials stored in SQLite.
- 👥 **Customer Relationship Management (CRM)**:
  - Add, edit, and delete customer profiles.
  - View individual customer purchase histories, total spent, and timelines.
- 📦 **Product & Inventory Control**:
  - Track stock levels, prices, and unit costs.
  - Group products into custom Categories.
  - **Low Stock Banner Alerts** dynamically trigger when stock falls below user-set thresholds.
- 🛒 **Order Management System**:
  - Place new orders by selecting customers, adding product rows, and calculating totals.
  - Filter orders by status: *Pending*, *Completed*, or *Cancelled*.
  - **Auto-Inventory Sync**: Completing or cancelling orders automatically decrements or restores product stock levels.
- 📊 **Chronological Sales Analytics**:
  - Dynamically switches charts between **Daily**, **Weekly**, **Monthly**, and **Yearly** sales trends.
  - Powered by responsive, client-side **Chart.js** canvases for ultra-fast page load speeds.
- 📄 **On-Demand PDF Reports**:
  - Generates comprehensive PDF reports with embedded data tables and charts using ReportLab.

---

## 🗂️ Project Structure

```
business-analyzer/
├── app.py                  # Flask web server & REST API routes
├── database.py             # SQLite schema, indices, & CRUD database queries
├── test_db.py              # Automated database integration test suite
├── requirements.txt        # Backend dependencies
├── templates/
│   ├── auth.html           # Captcha, OTP, and Login validation layouts
│   └── index.html          # Core ERP Dashboard
├── static/
│   ├── css/style.css       # Premium dark dashboard theme
│   └── js/dashboard.js     # Chart.js graphs, CRUD handlers, and lazy load operations
└── uploads/                # User uploads folder
```

---

## 🚀 Setup & Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/Nandinikanaujiya/business-analyzer.git
cd business-analyzer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python app.py

# 4. Open your browser
# http://localhost:5050
```

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python Flask |
| **Database** | SQLite3 (Persistent relational tables with indices) |
| **Data Ingestion** | Pandas + NumPy |
| **PDF Reporting** | ReportLab + Matplotlib |
| **Frontend** | HTML5 + CSS3 + Vanilla JavaScript |
| **Interactive Charts** | Chart.js (Responsive client-side canvas) |
| **Authentication** | Werkzeug password hashing |

---

## 📄 License

MIT — free to use and modify.
