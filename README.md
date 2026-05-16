# 🏦 Finance Pro | Smart Wealth Management

**Finance Pro** is a premium, personal finance and debt management engine designed for high-precision tracking and automated financial insights. Built with a focus on modern aesthetics and data integrity, it helps users manage liquid assets, credit cards, and complex loan structures with ease.

---

## 👨‍💻 Author
**PRADYUMNA BEHERA (BAPUN)**  
*Lead Developer & Architect*

---

## ✨ Key Features

### 📈 Intelligent Dashboard
- **Real-time KPIs**: Track Liquid Assets, Total Debt (Loans + Cards), and Net Worth at a glance.
- **Automated Summaries**: Background data aggregation for instant dashboard performance.
- **Smart Filters**: High-precision filtering to exclude internal capital movements and "silent" migrations.

### 💸 Loan & EMI Management
- **Automated EMI Engine**: Calculate monthly installments and annual interest rates automatically.
- **Silent Migration**: Seamlessly import existing loans without cluttering your transaction history.
- **Flexible Repayments**: Record regular EMIs, manual adjustments, or full foreclosures.
- **Credit Card Support**: Pay loans directly from liquid accounts or credit card limits.

### 💳 Debt & Ledger
- **Credit Card Tracking**: Monitor outstanding balances and utilization rates.
- **People Ledger**: Keep track of who owes you money and who you owe (Lent/Borrowed).

### 🤖 AI Assistant (Gemini Powered)
- **Token Shield Architecture**: Highly optimized context compression (JSON Summaries) to minimize API token usage.
- **Hybrid Reasoning**: Local SQL logic for simple queries, Gemini 1.5 Flash for complex financial advice.
- **Smart Caching**: Two-key caching system to prevent redundant API calls.

---

## 🛠️ Tech Stack

- **Backend**: Python / Flask
- **Database**: SQLite (WAL Mode for concurrency)
- **Frontend**: HTML5, Vanilla CSS3 (Custom Premium Design), JavaScript (ES6+)
- **Icons**: Phosphor Icons
- **AI**: Google Gemini 1.5 Flash API

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- A Gemini API Key (Optional, for AI Assistant)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/finance-pro.git
cd finance-pro

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (if requirements.txt exists)
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the root directory:
```env
FLASK_APP=app.py
FLASK_ENV=development
GEMINI_API_KEY=your_api_key_here
```

### 4. Running the App
```bash
python app.py
```
Access the app at `http://127.0.0.1:5000`

---

## 🔒 Security & Privacy
- **Local-First**: All financial data stays on your local machine in an encrypted SQLite database.
- **Silent Tags**: Sensitive migration data is tagged as `Silent` to remain hidden from analytics and logs.

---

## 📄 License
This project is for personal use and portfolio demonstration.
