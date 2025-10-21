

🏢 MCA Insights Engine – Company Data Management System**

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.29.0-red.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.1.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

An intelligent, AI-powered platform for tracking and analyzing Ministry of Corporate Affairs (MCA) company data.

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Architecture](#architecture) • [API](#api-documentation) • [Contributing](#contributing)

</div>

---

## Table of Contents

* Overview
* Key Features
* Technology Stack
* Architecture
* Installation
* Configuration
* Usage Guide
* Project Structure
* API Documentation
* Dashboard Screenshots
* Performance
* Testing
* Deployment
* Roadmap
* Contributing
* License
* Acknowledgments

---

## Overview

The MCA Insights Engine is a comprehensive Python-based system designed to:

* Consolidate and normalize MCA company data from data.gov.in
* Detect daily company-level changes with field-level accuracy
* Track over one million companies across India in real-time
* Analyze data trends using AI-driven natural language queries
* Visualize results with interactive dashboards

### Problem Statement

The Ministry of Corporate Affairs publishes company master data as frequently updated CSV files. Manually tracking changes in this massive dataset is inefficient. This project solves that by providing:

* Automated change tracking with daily snapshots
* AI-powered insights via a conversational interface
* Complete change history with old and new values
* Real-time, interactive data visualizations

---

## Key Features

### Data Management

* Automated daily snapshots of the entire dataset (over one million records)
* Change detection for new, modified, and deleted companies
* Field-level tracking of changes with before-and-after values
* Dual storage: CSV files and MySQL database

### AI-Powered Intelligence

* Smart chatbot powered by Google Gemini for natural language queries
* Context awareness for time-based queries such as “today” or “this week”
* Intent detection to route user requests to the correct data handler
* Conversational flow with follow-up questions and contextual memory

### Analytics and Visualization

* Interactive dashboard built with Streamlit
* Real-time company statistics, trends, and status breakdown
* Change timeline visualization for daily monitoring
* Drill-down analytics by company, type, or date

### Performance

* Hybrid in-memory search for instant query responses
* Asynchronous data processing for scalability
* Optimized batch database operations
* Automated daily jobs for scheduled updates

---

## Technology Stack

### Core Components

* **Python 3.9+** – Core programming language
* **Streamlit** – Dashboard and frontend interface
* **MySQL** – Structured data storage and retrieval
* **LangChain** – AI orchestration and natural language processing
* **Google Gemini API** – AI-powered conversational intelligence

---

Would you like me to continue rewriting the next sections (Architecture, Installation, etc.) in the same clean style?
