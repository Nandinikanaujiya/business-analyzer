# 📊 Business Growth Analyzer

A full-stack web application for small business owners to upload sales data and get **instant profit analysis, growth predictions, and AI-powered business insights**.

---

## ✨ Features

- 📁 **Upload CSV or Excel** sales data
- 💰 **Profit & Loss Analysis** — Revenue, Cost, Net Profit, Margin
- 📈 **Monthly Growth Prediction** — Trend + next month forecast via linear regression
- 🏆 **Best Product Analysis** — Ranked by revenue with share visualization
- 📊 **Charts** — Bar, Line, Pie charts using Matplotlib
- 📄 **PDF Report Download** — Full report with charts via ReportLab
- 🔐 **User Login System** — Register/login with password hashing
- 🕒 **Previous Reports History** — Per-user report log
- 🤖 **AI Insights** — Smart suggestions based on your data

---

## 🗂️ Project Structure

```
business-analyzer/
├── app.py                  # Flask backend + analysis engine
├── requirements.txt
├── templates/
│   ├── auth.html           # Login/Register page
│   └── index.html          # Dashboard
├── static/
│   ├── css/style.css       # Dark dashboard styles
│   └── js/dashboard.js     # Upload, render, download logic
├── uploads/                # Uploaded files (auto-created)
└── reports/                # Generated PDFs (auto-created)
```

---

## 🚀 Setup & Run

```bash
# 1. Clone the repo
git clone https://github.com/Nandini-kanaujiya/business-analyzer.git
cd business-analyzer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python app.py

# 4. Open in browser
# http://localhost:5050
```

---

## 📋 CSV Format

| Date | Product Name | Quantity | Price | Cost |
|------|-------------|----------|-------|------|
| 2024-01-05 | Laptop | 10 | 45000 | 32000 |

Download the **sample CSV** from inside the app (no setup needed).

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python Flask |
| Data Analysis | Pandas + NumPy |
| Charts | Matplotlib |
| PDF Reports | ReportLab |
| Frontend | HTML + CSS + Vanilla JS |
| Auth | Werkzeug password hashing |

---

## 📄 License

MIT — free to use and modify.
