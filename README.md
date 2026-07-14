# 🛡️ MuleGuard – Real-Time Transaction Graph Analysis for UPI Mule Account Identification

> **A Cybersecurity & FinTech Analytics Prototype for Detecting Potential UPI Mule Accounts using Graph-Based Transaction Analysis and Heuristic Risk Scoring.**

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red)
![NetworkX](https://img.shields.io/badge/NetworkX-Graph%20Analytics-green)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Processing-blue)
![Status](https://img.shields.io/badge/Status-Completed-success)

---

# 📖 Overview

MuleGuard is a Python-based cybersecurity and financial analytics prototype developed to identify potentially suspicious **UPI mule accounts** through **graph-based transaction analysis**. Instead of analysing transactions individually, the system models the complete transaction ecosystem as a **directed graph**, enabling investigators to uncover hidden relationships, suspicious money flow patterns, and interconnected fraudulent accounts.

The application combines **graph analytics, heuristic risk scoring, interactive dashboards, and automated report generation** to assist in identifying mule account behaviour within digital payment ecosystems.

This project was developed as part of a **Cybersecurity Internship** and is intended solely for **educational, research, and demonstration purposes**.

---

# 🎯 Problem Statement

With the rapid adoption of UPI-based digital payments, financial fraud involving mule accounts has increased significantly. Fraudsters often route stolen funds through multiple intermediary accounts to disguise the origin of transactions.

Traditional fraud detection systems mainly inspect transactions individually and often fail to identify hidden relationships among accounts.

MuleGuard addresses this challenge by converting transaction datasets into a graph structure and analysing account connectivity, transaction behaviour, and network characteristics to detect potentially suspicious accounts.

---

# 🎯 Objectives

- Parse transaction datasets
- Build a directed transaction graph
- Analyse account relationships
- Calculate heuristic-based risk scores
- Detect suspicious mule accounts
- Visualise transaction networks
- Generate investigation-ready PDF reports
- Provide an interactive analytical dashboard

---

# ✨ Features

- 📂 CSV Transaction Parsing
- 🌐 Directed Graph Construction using NetworkX
- 📊 Interactive Dashboard (Streamlit)
- ⚠️ Heuristic-Based Risk Scoring
- 🔍 Suspicious Mule Account Detection
- 📈 Graph Analytics & Network Visualization
- 📄 Automated PDF Report Generation
- 📋 Transaction Summary & Statistics
- 📝 Logging & Monitoring
- 🏗️ Modular Project Architecture

---

# 🛠 Technology Stack

## Programming Language

- Python 3.x

## Frontend

- Streamlit

## Backend

- Python

## Libraries

- Pandas
- NetworkX
- Plotly
- Matplotlib
- NumPy
- FPDF

## Development Tools

- Visual Studio Code
- Git
- GitHub

---

# 📂 Project Structure

```
MuleGuard/
│
├── app/
│   ├── dashboard/
│   ├── graph/
│   ├── parser/
│   ├── report_generator/
│   ├── risk_engine/
│   └── utils/
│
├── data/
│   ├── input/
│   └── output/
│
├── docs/
├── logs/
├── screenshots/
├── tests/
│
├── main.py
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

---

# 🏗️ System Architecture

```
CSV Transaction Dataset
          │
          ▼
Transaction Parser
          │
          ▼
Data Preprocessing
          │
          ▼
Graph Builder (NetworkX)
          │
          ▼
Risk Scoring Engine
          │
          ▼
Mule Account Detection
          │
     ┌────┴────┐
     ▼         ▼
Dashboard   PDF Report
```

---

# ⚙️ System Workflow

1. Upload transaction dataset.
2. Parse transaction records.
3. Validate and preprocess data.
4. Build a directed transaction graph.
5. Analyse account relationships.
6. Compute heuristic risk scores.
7. Identify suspicious mule accounts.
8. Visualise transaction networks.
9. Generate downloadable investigation reports.

---

# 🔬 Risk Analysis Methodology

The system follows a **heuristic-based fraud detection approach** where multiple behavioural indicators contribute to an overall risk score.

### Indicators Used

- High transaction frequency
- Large cumulative transaction amounts
- Multiple incoming transactions
- Multiple outgoing transactions
- Fan-In / Fan-Out behaviour
- Highly connected graph nodes
- Rapid fund movement
- Suspicious transaction chains
- Degree Centrality
- Betweenness Centrality

Each account is assigned a cumulative risk score that helps investigators prioritise suspicious accounts for further analysis.

---

# 🌐 Graph Analytics

The application models financial transactions as a **directed graph**.

- **Nodes:** UPI Accounts
- **Edges:** Transactions

Graph analytics performed include:

- Degree Analysis
- Degree Centrality
- Betweenness Centrality
- Connected Components
- Network Connectivity
- Transaction Relationship Mapping

These metrics help identify accounts acting as hubs, intermediaries, or potential mule accounts.

---

# 📊 Dashboard

The Streamlit dashboard provides:

- Dataset Upload
- Transaction Summary
- Suspicious Account Detection
- Risk Score Analysis
- Interactive Charts
- Network Graph Visualization
- Investigation Report Generation

---

# 📥 Input

The application accepts transaction datasets in CSV format.

Example fields include:

- Transaction ID
- Sender Account
- Receiver Account
- Transaction Amount
- Timestamp

---

# 📤 Output

The system generates:

- Transaction Network Graph
- Suspicious Account List
- Risk Score Summary
- Dashboard Analytics
- Investigation PDF Report

---

# 🚀 Installation

## Clone Repository

```bash
git clone https://github.com/cheriesharma122/MuleGuard-Real-Time-Transaction-Graph-Analysis-for-UPI-Mule-Account-Identification.git
```

## Navigate to Project

```bash
cd MuleGuard-Real-Time-Transaction-Graph-Analysis-for-UPI-Mule-Account-Identification
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Run Application

If your entry point is:

```bash
streamlit run main.py
```

or

```bash
streamlit run app/dashboard/dashboard.py
```

*(Use the one that matches your project structure.)*

---

# 💼 Applications

- Banking Fraud Investigation
- UPI Fraud Detection
- Financial Crime Investigation
- Cybercrime Analysis
- Anti-Money Laundering (AML)
- Banking Risk Assessment
- Digital Payment Monitoring
- Cybersecurity Demonstrations
- Academic Research

---

# 🔐 Security Considerations

- Uses sample transaction datasets only
- No real banking credentials are stored
- No customer-sensitive information is collected
- Runs locally without external API dependency
- Designed solely for educational and internship purposes

---

# ⚠️ Limitations

- Prototype implementation
- Offline transaction datasets
- Rule-based heuristic analysis
- No live UPI integration
- No machine learning model
- Intended for demonstration purposes

---

# 🚀 Future Enhancements

Future versions of MuleGuard can include:

- Machine Learning-based Fraud Detection
- Graph Neural Networks (GNN)
- Community Detection Algorithms
- Neo4j Graph Database Integration
- REST API Support
- Real-Time Transaction Streaming
- Cloud Deployment
- User Authentication & Role-Based Access
- Email & SMS Alert System
- Investigator Case Management Portal

---

# 📦 Repository Modules

| Module | Description |
|---------|-------------|
| Parser | Reads and validates transaction datasets |
| Graph Builder | Builds the transaction graph using NetworkX |
| Risk Engine | Calculates heuristic-based risk scores |
| Mule Detector | Detects suspicious accounts |
| Dashboard | Displays analytics and visualisations |
| Report Generator | Generates PDF investigation reports |
| Utilities | Helper functions and project constants |

---

# 🧪 Testing

The application has been manually tested using multiple sample transaction datasets.

Testing includes:

- CSV Upload
- Graph Construction
- Dashboard Rendering
- Risk Score Calculation
- PDF Report Generation
- Suspicious Account Identification

---

# 📸 Screenshots

Add screenshots inside the `screenshots/` folder.

Recommended images:

- Home Dashboard
- Dataset Upload
- Network Graph
- Risk Analysis
- Suspicious Accounts
- PDF Report

---

# 📚 References

- Reserve Bank of India (RBI)
- National Payments Corporation of India (NPCI)
- NetworkX Documentation
- Streamlit Documentation
- Plotly Documentation
- Pandas Documentation
- Research Papers on Graph-Based Fraud Detection

---

# 👩‍💻 Author

**Cherie Sharma**

Cybersecurity Internship Project

**MuleGuard – Real-Time Transaction Graph Analysis for UPI Mule Account Identification**

2026

---

# 📄 License

This project is intended solely for educational, research, and internship evaluation purposes.

**Copyright © 2026 Cherie Sharma. All Rights Reserved.**

---

# 🙏 Acknowledgements

Special thanks to:

- Open Source Community
- Python Software Foundation
- Streamlit
- NetworkX
- Pandas
- Plotly
- Matplotlib
- FPDF

for providing the tools and libraries that made this project possible.