# 📊 Queueing Simulation Dashboard

An interactive Streamlit dashboard that runs and compares three discrete-event queueing simulations built with **SimPy**.

## Simulations

| System | Queue type | Service time | Description |
|--------|-----------|--------------|-------------|
| **M/D/2** | Centralized | Deterministic (1/μ) | Exponential arrivals, fixed service duration |
| **M/M/2** | Centralized | Exponential | Classic M/M/c queue |
| **Tunisian** | 2 separate queues | Exponential | Customers join the shortest queue, no switching |

## Features

- 🎛️ **Interactive sidebar** — adjust λ, μ, simulation time and seed live
- 📈 **Per-system dashboards** — queue length over time, busy servers, wait time distribution, server state pie chart
- 📊 **Comparison tab** — head-to-head metric table, overlay histograms, queue evolution, server state stacked bars
- ⚡ **Cached simulations** — re-runs only when parameters change

## Run locally

```bash
git clone https://github.com/<your-username>/queueing-dashboard.git
cd queueing-dashboard
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → select your repo → set **Main file path** to `app.py`
4. Click **Deploy**

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| λ (lambda) | 1.0 | Mean customer arrival rate (customers/min) |
| μ (mu) | 1.0 | Mean service rate (customers/min) |
| Simulation time | 120 min | Total simulation duration |
| Seed | 42 | Random seed for reproducibility |

> **Note:** System is stable when utilization ρ = λ/(2μ) < 1
