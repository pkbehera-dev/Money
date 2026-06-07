# 💰 Finance Pro — Personal Finance Tracker [ARCHIVED]

> [!WARNING]
> **ARCHIVE NOTICE:** This project is no longer actively maintained or updated. It is preserved here as a historical archive. Anyone is welcome to clone, fork, study, and contribute to this repository freely under the terms of the MIT License.
>
> For the new, optimized, compiled, and lightning-fast desktop experience without AI latency, check out our new **Go + Wails + SQLite** version.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-WAL_Mode-003B57?style=for-the-badge&logo=sqlite)](https://sqlite.org)
[![AI](https://img.shields.io/badge/AI-Gemini_+_Ollama-FF6F00?style=for-the-badge&logo=google-gemini)](https://deepmind.google/technologies/gemini/)

---

## 📜 LICENSE

This project is open-source and licensed under the standard **MIT License**. You are free to copy, modify, and distribute this software for personal and commercial projects, provided attribution is maintained. See the [LICENSE](file:///d:/PYTHON/Money/LICENSE) file for the full text.

---

## 📖 What Is This?

Finance Pro is a **full-featured personal finance app** that runs locally on your computer.
It is local-first, subscription-free, and has no ads. Your data is stored locally, but if you choose to use the advanced Gemini AI assistant, it will use cloud-based Gemini APIs to process financial questions.


It helps you:
- **Track your income and expenses** across multiple bank accounts
- **Manage credit cards** and see how much you owe
- **Set savings goals** and watch your progress
- **Create monthly budgets** and get alerts when you overspend
- **Track loans and debts** — who you owe, who owes you
- **Get AI-powered advice** about your finances (using Gemini or local Ollama)
- **View reports and charts** to understand where your money goes
- **Manage subscriptions** so you never forget a recurring payment

---

## ✨ Key Features

### 🏦 Multi-Account Support
Manage multiple bank accounts and credit cards in one place. Every transaction is linked to a specific account or card, so your balances are always accurate.

### 💳 Credit Card Tracking
Track credit card spending, payments, and available limits. Bill payments automatically deduct from your bank account and reduce your card balance.

### 📊 Dashboard & Reports
A beautiful dark-mode dashboard shows your total balance, monthly spending, income trends, and financial health score — all at a glance. Detailed reports break down spending by category and time period.

### 🎯 Savings Goals
Set goals like "New Laptop" or "Emergency Fund" with a target amount and date. The app tracks your progress and tells you if you're on track.

### 💵 Budget Management
Create monthly budgets for categories like Food, Transport, or Entertainment. Get automatic alerts at 50%, 70%, 90%, and 100% of your budget.

### 🤝 Interpersonal Ledger (Debts & Loans)
Track who you borrowed money from and who you lent money to. Record partial payments and see settlement progress in real time.

### 🤖 AI Financial Assistant
Ask questions about your finances in plain language:
- *"Can I afford a new phone?"*
- *"How much did I spend on food this month?"*
- *"What is my total debt?"*

The AI uses **Gemini** (Google's AI) for complex advice and **Ollama** (local AI) for quick data lookups — saving you API costs.

### 🔔 Smart Notifications
Background workers check your finances every 15 minutes and alert you about:
- Budget overruns
- Upcoming subscription renewals
- Goal milestones
- Unusual spending patterns

### 🗑️ Trash & Recovery
Accidentally deleted something? Everything goes to the trash first. You can restore it anytime before permanently deleting.

### 💾 Backup & Restore
Create safe backups of your entire database with one click. Restore from any previous backup if something goes wrong. Uses SQLite's native backup API for safety.

### 📱 Asset Tracking
Track your physical assets (phone, laptop, bike, etc.) along with purchase date and current value.

### 🔍 Universal Search
Search across transactions, accounts, and more — all from one search bar.

---

## 🏗️ How It's Built

```
Money/
├── app.py                  ← Main server file (starts everything)
├── database/
│   ├── connection.py       ← Database connection (SQLite with WAL mode)
│   └── schema.sql          ← All database tables
├── models/                 ← Data models (Account, Transaction, etc.)
├── routes/                 ← URL handlers (what happens when you click things)
│   ├── dashboard_routes.py
│   ├── transaction_routes.py
│   ├── ai_routes.py
│   ├── goal_routes.py
│   ├── settings_routes.py
│   └── ... (17 route files)
├── services/               ← Business logic (calculations, AI, analytics)
│   ├── ai_service.py       ← AI query routing (Gemini + Ollama)
│   ├── analytics_service.py
│   ├── budget_service.py
│   ├── transaction_service.py
│   └── ... (26 service files)
├── ui/
│   ├── static/
│   │   ├── css/            ← Stylesheets (dark theme, glassmorphism)
│   │   └── js/             ← Client-side JavaScript
│   └── templates/          ← HTML pages (16 pages)
│       ├── base.html       ← Main layout (sidebar, notifications)
│       ├── dashboard.html
│       ├── transactions.html
│       └── ...
├── utils/                  ← Helper functions
├── requirements.txt        ← Python packages needed
├── run.bat                 ← Quick start script for Windows
└── .env                    ← Your secret keys (not shared)
```

---

## 🚀 How to Set Up

### Step 1 — Install Python
Make sure you have **Python 3.10 or newer** installed.
Download it from [python.org](https://www.python.org/downloads/) if you don't have it.

### Step 2 — Download This Project
```bash
git clone https://github.com/pkbehera-dev/Money.git
cd Money
```

### Step 3 — Create a Virtual Environment
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

### Step 4 — Install Required Packages
```bash
pip install -r requirements.txt
```

### Step 5 — Set Up Your Environment File
Create a `.env` file in the project folder:
```env
FLASK_APP=app.py
FLASK_ENV=development
GEMINI_API_KEY=your_gemini_api_key_here
```
> **Don't have a Gemini API key?** That's fine! The app will fall back to Ollama (local AI) or work without AI features.

### Step 6 — Run the App
```bash
python app.py
```
Or on Windows, just double-click **`run.bat`**.

Open your browser and go to: **http://127.0.0.1:5000**

## 🔒 Privacy & Security

| Feature | Detail |
|---|---|
| **Where is my data?** | Stored locally in `finance.db` on your computer. |
| **Does it need internet?** | Yes, if using the Gemini AI feature. It runs offline if using local Ollama or with AI disabled. |
| **Is my data shared?** | When you ask questions using Gemini, compressed transactional context summaries are sent to Google Gemini APIs. No direct personal identity details are sent. If using local Ollama, queries remain 100% local. |
| **Can others see my data?** | Not unless they access your computer or intercept Gemini API calls. |

---


## 🛠️ Tech Stack

| Technology | Why It's Used |
|---|---|
| **Python 3.10+** | Main programming language — reliable and easy to work with |
| **Flask** | Lightweight web framework — perfect for a personal app |
| **SQLite (WAL mode)** | Fast, file-based database — no server needed |
| **Vanilla HTML/CSS/JS** | No heavy frameworks — keeps things fast and simple |
| **Google Gemini AI** | Smart financial advice using Google's AI |
| **Ollama** | Local AI model — works without internet, saves API costs |
| **Mermaid** | Diagrams in documentation |

---

## 📜 Full Copyright Notice

```
MIT License

Copyright © 2024-2026 Pradyumna Behera (Bapun)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<p align="center">
  <b>Made with ❤️ by Pradyumna Behera (Bapun)</b><br>
  <i>Licensed under the MIT License. Feel free to contribute!</i>
</p>
