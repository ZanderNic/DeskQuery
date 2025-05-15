
<h1 align="center">Deskquery</h1>

<h4 align="center"><i>Your smart assistant for desk booking analytics.</i></h4>

<p align="center">
  <img src="https://img.shields.io/badge/Easy%20Booking%20Analytics-%F0%9F%92%BC-green" alt="Easy Booking Analytics" />
  <img src="https://img.shields.io/badge/In%20Simple%20Natural%20Language-%F0%9F%94%A5-orange" alt="Natural Language" />
  <img src="https://img.shields.io/badge/No%20Coding%20Required-%F0%9F%94%A1-yellow" alt="No Coding Required" />
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-blue" alt="MIT License" />
  </a>
</p>

---

`deskquery` is an AI-powered chatbot and data analysis tool that helps companies understand and optimize their desk utilization. It combines a conversational interface (via LLMs) with a robust backend of analytic functions for workplace intelligence.

---

## 🌐 Live WebApp

A Flask-based frontend allows users to ask questions like:

* *"How many desks were unused last week?"*
* *"Simulate the effect of closing Room 3."*
* *"Estimate how many tables we need for 90% utilization."*

---

## What It Does

* Interprets natural language queries via a large language model (LLM)
* Maps them to predefined analytic functions
* Executes Python functions to return insights about desk usage
* Includes simulations, forecasts, anomaly detection, and interactive plotting

---

## 🚀 Quickstart

```bash
# Install dependencies
pip install -r requirements.txt

# Install the package 
pip install .

# Start the Flask web app
python3 src/deskquery/webapp/app.py
```

---

## 📃 Core Features

* ✅ LLM-based query interpretation (Gemini, GPT, etc.)
* ✅ Modular analytics functions (forecasting, clustering, policy simulation)
* ✅ Interactive visualizations (Matplotlib / Plotly)
* ✅ Structured JSON response pipeline
* ✅ Flask-based web frontend with chat interface

---

## 🔧 How It Works

1. **User asks a question**
2. **LLM receives a prompt** including function summaries and example queries
3. **LLM replies with JSON:** selects a function + fills in parameters
4. **Backend executes the selected function**, or asks the user for missing info
5. **Frontend displays the result** (text, plot, or warning)

---

## 💡 Why?

* Empower managers to ask *"what if"* questions
* Close the loop between workplace data and strategic decisions

---

## 📄 License

MIT