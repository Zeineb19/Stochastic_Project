import streamlit as st
import simpy
import random
import math
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
 
st.set_page_config(
    page_title="Queueing Simulation Dashboard",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS — clean blue & white professional theme
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #F0F4F9; }
 
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1A3C6E;
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] .stSlider label,
    [data-testid="stSidebar"] .stNumberInput label {
        color: #BDD5F0 !important;
        font-size: 0.85rem !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #2E5FA3 !important;
    }
 
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 4px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    .stTabs [data-baseweb="tab"] {
        color: #1A3C6E;
        font-weight: 500;
        font-size: 0.9rem;
        border-radius: 8px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1A3C6E !important;
        color: white !important;
    }
 
    /* Metric cards */
    [data-testid="metric-container"] {
        background-color: #FFFFFF;
        border: 1px solid #D6E4F7;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    [data-testid="metric-container"] label {
        color: #5A7FA8 !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #1A3C6E !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }
 
    /* Dataframe */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
 
    /* Section headers */
    h1 { color: #1A3C6E !important; font-weight: 700 !important; }
    h2, h3 { color: #1A3C6E !important; font-weight: 600 !important; }
 
    /* Caption */
    .stCaption { color: #5A7FA8 !important; }
 
    /* Spinner */
    .stSpinner { color: #1A3C6E !important; }
 
    /* Success/error boxes in sidebar */
    .stSuccess { background-color: #E8F5E9 !important; color: #2E7D32 !important; }
    .stError   { background-color: #FFEBEE !important; color: #C62828 !important; }
</style>
""", unsafe_allow_html=True)
 
# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🔷 Queueing Sim")
st.sidebar.markdown("**Simulation Parameters**")
st.sidebar.markdown("---")
 
LAMBDA      = st.sidebar.slider("Arrival rate λ (customers/min)", 0.1, 3.0, 1.0, 0.1)
MU          = st.sidebar.slider("Service rate μ (customers/min)", 0.1, 3.0, 1.0, 0.1)
NUM_SERVERS = 2
SIM_TIME    = st.sidebar.slider("Simulation time (min)", 30, 300, 120, 10)
SEED        = st.sidebar.number_input("Random seed", value=42, step=1)
 
st.sidebar.markdown("---")
 
rho = LAMBDA / (NUM_SERVERS * MU)
if rho >= 1:
    st.sidebar.error(f"⚠️ ρ = {rho:.3f} — Overloaded!")
else:
    st.sidebar.success(f"✅ ρ = {rho:.3f} — Stable")
 
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Systems compared**
 
🔵 **M/D/2**
Shared queue · deterministic service
 
🔴 **M/M/2**
Shared queue · exponential service
 
🟢 **Tunisian**
2 queues · join shortest · no switching
""")
st.sidebar.markdown("---")
st.sidebar.caption("Stochastic Processes Project · 2025")
 
# ─────────────────────────────────────────────────────────────────────────────
# SIMULATION FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def run_md2(lam, mu, sim_time, seed):
    random.seed(seed); np.random.seed(seed)
    waiting_times, queue_len_log, server_state_log = [], [], []
 
    def log(env, servers):
        queue_len_log.append((env.now, len(servers.queue)))
        server_state_log.append((env.now, servers.count))
 
    def customer(env, servers):
        arrival = env.now
        log(env, servers)
        with servers.request() as req:
            yield req
            waiting_times.append(env.now - arrival)
            log(env, servers)
            yield env.timeout(1.0 / mu)
        log(env, servers)
 
    def arrivals(env, servers):
        while True:
            yield env.timeout(-math.log(random.random()) / lam)
            env.process(customer(env, servers))
 
    env = simpy.Environment()
    srv = simpy.Resource(env, capacity=2)
    env.process(arrivals(env, srv))
    env.run(until=sim_time)
    return waiting_times, queue_len_log, server_state_log
 
 
def run_mm2(lam, mu, sim_time, seed):
    random.seed(seed); np.random.seed(seed)
    waiting_times, queue_len_log, server_state_log = [], [], []
 
    def log(env, servers):
        queue_len_log.append((env.now, len(servers.queue)))
        server_state_log.append((env.now, servers.count))
 
    def customer(env, servers):
        arrival = env.now
        log(env, servers)
        with servers.request() as req:
            yield req
            waiting_times.append(env.now - arrival)
            log(env, servers)
            yield env.timeout(-math.log(random.random()) / mu)
        log(env, servers)
 
    def arrivals(env, servers):
        while True:
            yield env.timeout(-math.log(random.random()) / lam)
            env.process(customer(env, servers))
 
    env = simpy.Environment()
    srv = simpy.Resource(env, capacity=2)
    env.process(arrivals(env, srv))
    env.run(until=sim_time)
    return waiting_times, queue_len_log, server_state_log
 
 
def run_tunisian(lam, mu, sim_time, seed):
    random.seed(seed); np.random.seed(seed)
    waiting_times, queue_len_log, server_state_log = [], [], []
    q1_log, q2_log = [], []
 
    def log(env, srv1, srv2):
        q1 = len(srv1.queue) + srv1.count
        q2 = len(srv2.queue) + srv2.count
        queue_len_log.append((env.now, len(srv1.queue) + len(srv2.queue)))
        server_state_log.append((env.now, srv1.count + srv2.count))
        q1_log.append((env.now, q1))
        q2_log.append((env.now, q2))
 
    def customer(env, srv1, srv2):
        arrival = env.now
        log(env, srv1, srv2)
        len1 = len(srv1.queue) + srv1.count
        len2 = len(srv2.queue) + srv2.count
        if len1 < len2:
            chosen = srv1
        elif len2 < len1:
            chosen = srv2
        else:
            chosen = random.choice([srv1, srv2])
        with chosen.request() as req:
            yield req
            waiting_times.append(env.now - arrival)
            log(env, srv1, srv2)
            yield env.timeout(-math.log(random.random()) / mu)
        log(env, srv1, srv2)
 
    def arrivals(env, srv1, srv2):
        while True:
            yield env.timeout(-math.log(random.random()) / lam)
            env.process(customer(env, srv1, srv2))
 
    env = simpy.Environment()
    srv1 = simpy.Resource(env, capacity=1)
    srv2 = simpy.Resource(env, capacity=1)
    env.process(arrivals(env, srv1, srv2))
    env.run(until=sim_time)
    return waiting_times, queue_len_log, server_state_log, q1_log, q2_log
 
 
def time_weighted_proportions(times, states, total_time):
    times = list(times) + [total_time]
    p = {0: 0.0, 1: 0.0, 2: 0.0}
    for i in range(len(states)):
        dt = times[i + 1] - times[i]
        p[states[i]] = p.get(states[i], 0) + dt
    return p[0] / total_time, p[1] / total_time, p[2] / total_time
 
 
def compute_stats(wt, queue_len_log, server_state_log, total_time):
    wt = np.array(wt)
    _, qlens = zip(*queue_len_log)
    times_s, sbusy = zip(*server_state_log)
    p_idle, p_one, p_two = time_weighted_proportions(times_s, sbusy, total_time)
    return {
        "n_served":  len(wt),
        "avg_wait":  float(np.mean(wt)),
        "max_wait":  float(np.max(wt)),
        "avg_queue": float(np.mean(qlens)),
        "max_queue": int(np.max(qlens)),
        "p_idle": p_idle, "p_one": p_one, "p_two": p_two,
    }
 
 
# ─────────────────────────────────────────────────────────────────────────────
# RUN SIMULATIONS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def run_all(lam, mu, sim_time, seed):
    wt1, ql1, ss1            = run_md2(lam, mu, sim_time, seed)
    wt2, ql2, ss2            = run_mm2(lam, mu, sim_time, seed)
    wt3, ql3, ss3, q1l, q2l = run_tunisian(lam, mu, sim_time, seed)
    return (wt1, ql1, ss1), (wt2, ql2, ss2), (wt3, ql3, ss3, q1l, q2l)
 
 
with st.spinner("Running simulations…"):
    (wt1, ql1, ss1), (wt2, ql2, ss2), (wt3, ql3, ss3, q1l, q2l) = run_all(
        LAMBDA, MU, SIM_TIME, int(SEED)
    )
 
s1 = compute_stats(wt1, ql1, ss1, SIM_TIME)
s2 = compute_stats(wt2, ql2, ss2, SIM_TIME)
s3 = compute_stats(wt3, ql3, ss3, SIM_TIME)
 
# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY THEME
# ─────────────────────────────────────────────────────────────────────────────
COLORS   = {"M/D/2": "#1A6EBD", "M/M/2": "#E05A2B", "Tunisian": "#2E9E6B"}
PIE_COLS = ["#BDD5F0", "#5A9FD4", "#1A3C6E"]
 
LAYOUT_BASE = dict(
    paper_bgcolor="white",
    plot_bgcolor="#F7FAFD",
    font=dict(family="Segoe UI, Arial", color="#1A3C6E", size=12),
    margin=dict(t=60, b=30, l=30, r=20),
)
 
 
def system_dashboard(name, wt, ql, ss, color):
    wt = np.array(wt)
    tq, qlens = zip(*ql)
    ts, sbusy = zip(*ss)
    avg_w = np.mean(wt)
    avg_q = np.mean(qlens)
    p_idle, p_one, p_two = time_weighted_proportions(ts, sbusy, SIM_TIME)
 
    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=(
            "Queue length over time", "Busy servers over time", "Server state (time-weighted)",
            "Waiting time per customer", "Waiting time distribution", ""
        ),
        specs=[[{"colspan": 2}, None, {}], [{}, {}, {"type": "domain"}]],
    )
 
    fig.add_trace(go.Scatter(x=list(tq), y=list(qlens), mode="lines",
                             line=dict(color=color, width=1.5, shape="hv"),
                             name="Queue length"), row=1, col=1)
    fig.add_hline(y=avg_q, line_dash="dash", line_color="#E05A2B", line_width=1.2,
                  annotation_text=f"avg = {avg_q:.2f}", annotation_font_color="#E05A2B",
                  row=1, col=1)
 
    fig.add_trace(go.Scatter(x=list(ts), y=list(sbusy), mode="lines",
                             line=dict(color="#5A4FCF", width=1.2, shape="hv"),
                             name="Busy servers"), row=1, col=3)
 
    fig.add_trace(go.Scatter(y=wt, mode="lines",
                             line=dict(color="#2E9E8A", width=0.9),
                             name="Wait time"), row=2, col=1)
    fig.add_hline(y=avg_w, line_dash="dash", line_color="#E05A2B", line_width=1.2,
                  annotation_text=f"avg = {avg_w:.3f}", annotation_font_color="#E05A2B",
                  row=2, col=1)
 
    fig.add_trace(go.Histogram(x=wt, nbinsx=25, name="Distribution",
                               marker_color=color, opacity=0.75,
                               marker_line=dict(color="white", width=0.5)),
                  row=2, col=2)
    fig.add_vline(x=avg_w, line_dash="dash", line_color="#E05A2B",
                  line_width=1.2, row=2, col=2)
 
    fig.add_trace(go.Pie(
        labels=["Both idle", "One busy", "Both busy"],
        values=[p_idle, p_one, p_two],
        marker_colors=PIE_COLS,
        textinfo="label+percent",
        hole=0.38,
        textfont=dict(size=11),
    ), row=2, col=3)
 
    fig.update_layout(
        **LAYOUT_BASE,
        height=580,
        showlegend=False,
        title_text=f"<b>{name}</b>",
        title_font=dict(size=15, color="#1A3C6E"),
    )
    for r, c, yt, xt in [
        (1, 1, "Customers waiting", "Time (min)"),
        (1, 3, "Servers busy",      "Time (min)"),
        (2, 1, "Wait (min)",        "Customer #"),
        (2, 2, "Frequency",         "Wait (min)"),
    ]:
        fig.update_yaxes(title_text=yt, title_font=dict(size=11), row=r, col=c,
                         gridcolor="#E8EFF7", linecolor="#D6E4F7")
        fig.update_xaxes(title_text=xt, title_font=dict(size=11), row=r, col=c,
                         gridcolor="#E8EFF7", linecolor="#D6E4F7")
    return fig
 
 
def comparison_charts(s1, s2, s3, wt1, wt2, wt3, ql1, ql2, ql3):
    names  = ["M/D/2", "M/M/2", "Tunisian"]
    colors = [COLORS[n] for n in names]
 
    metrics = {
        "Avg wait (min)": [s1["avg_wait"],  s2["avg_wait"],  s3["avg_wait"]],
        "Max wait (min)": [s1["max_wait"],  s2["max_wait"],  s3["max_wait"]],
        "Avg queue len":  [s1["avg_queue"], s2["avg_queue"], s3["avg_queue"]],
        "Max queue len":  [s1["max_queue"], s2["max_queue"], s3["max_queue"]],
    }
 
    fig_bar = make_subplots(rows=2, cols=2, subplot_titles=list(metrics.keys()),
                            horizontal_spacing=0.12, vertical_spacing=0.18)
    for (r, c), (_, vals) in zip([(1,1),(1,2),(2,1),(2,2)], metrics.items()):
        fig_bar.add_trace(
            go.Bar(x=names, y=vals, marker_color=colors,
                   marker_line=dict(color="white", width=1), showlegend=False),
            row=r, col=c
        )
    fig_bar.update_layout(**LAYOUT_BASE, height=480,
                          title_text="<b>Comparative Metrics</b>",
                          title_font=dict(size=15, color="#1A3C6E"))
    fig_bar.update_xaxes(gridcolor="#E8EFF7", linecolor="#D6E4F7")
    fig_bar.update_yaxes(gridcolor="#E8EFF7", linecolor="#D6E4F7")
 
    fig_hist = go.Figure()
    for name, wt, col in zip(names, [wt1, wt2, wt3], colors):
        fig_hist.add_trace(go.Histogram(
            x=np.array(wt), nbinsx=30, name=name,
            marker_color=col, opacity=0.6,
            marker_line=dict(color="white", width=0.4),
        ))
    fig_hist.update_layout(
        **LAYOUT_BASE,
        barmode="overlay",
        title_text="<b>Waiting Time Distributions — Overlay</b>",
        title_font=dict(size=15, color="#1A3C6E"),
        xaxis_title="Wait (min)", yaxis_title="Frequency",
        height=360,
        legend=dict(orientation="h", y=1.1, font=dict(size=12)),
        xaxis=dict(gridcolor="#E8EFF7"), yaxis=dict(gridcolor="#E8EFF7"),
    )
 
    fig_q = go.Figure()
    for name, ql, col in zip(names, [ql1, ql2, ql3], colors):
        tq, qlens = zip(*ql)
        fig_q.add_trace(go.Scatter(
            x=list(tq), y=list(qlens), mode="lines", name=name,
            line=dict(color=col, width=1.4, shape="hv"), opacity=0.85,
        ))
    fig_q.update_layout(
        **LAYOUT_BASE,
        title_text="<b>Queue Length Over Time — All Systems</b>",
        title_font=dict(size=15, color="#1A3C6E"),
        xaxis_title="Time (min)", yaxis_title="Queue length",
        height=320,
        legend=dict(orientation="h", y=1.1, font=dict(size=12)),
        xaxis=dict(gridcolor="#E8EFF7"), yaxis=dict(gridcolor="#E8EFF7"),
    )
 
    fig_states = go.Figure(data=[
        go.Bar(name="Both idle", x=names, y=[s1["p_idle"], s2["p_idle"], s3["p_idle"]],
               marker_color=PIE_COLS[0]),
        go.Bar(name="One busy",  x=names, y=[s1["p_one"],  s2["p_one"],  s3["p_one"]],
               marker_color=PIE_COLS[1]),
        go.Bar(name="Both busy", x=names, y=[s1["p_two"],  s2["p_two"],  s3["p_two"]],
               marker_color=PIE_COLS[2]),
    ])
    fig_states.update_layout(
        **LAYOUT_BASE,
        barmode="stack",
        title_text="<b>Server State Distribution (time-weighted)</b>",
        title_font=dict(size=15, color="#1A3C6E"),
        yaxis_title="Fraction of time", yaxis_tickformat=".0%",
        height=320,
        legend=dict(orientation="h", y=1.1, font=dict(size=12)),
        xaxis=dict(gridcolor="#E8EFF7"), yaxis=dict(gridcolor="#E8EFF7"),
    )
    return fig_bar, fig_hist, fig_q, fig_states
 
 
# ─────────────────────────────────────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='background: linear-gradient(90deg, #1A3C6E 0%, #2563A8 100%);
            padding: 1.4rem 2rem; border-radius: 12px; margin-bottom: 1.5rem;'>
    <h1 style='color: white; margin: 0; font-size: 1.7rem;'>
        🔷 Queueing Simulation Dashboard
    </h1>
    <p style='color: #BDD5F0; margin: 0.3rem 0 0; font-size: 0.9rem;'>
        Discrete-event simulation · M/D/2 · M/M/2 · Tunisian System
    </p>
</div>
""", unsafe_allow_html=True)
 
st.caption(f"λ = {LAMBDA} | μ = {MU} | servers = 2 | T = {SIM_TIME} min | seed = {int(SEED)}")
 
# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🔵  M/D/2", "🔴  M/M/2", "🟢  Tunisian", "📊  Comparison"
])
 
 
def metric_row(stats):
    cols = st.columns(6)
    cols[0].metric("👥 Served",        stats["n_served"])
    cols[1].metric("⏱ Avg wait",       f"{stats['avg_wait']:.3f} min")
    cols[2].metric("🔺 Max wait",       f"{stats['max_wait']:.3f} min")
    cols[3].metric("📋 Avg queue",      f"{stats['avg_queue']:.3f}")
    cols[4].metric("📋 Max queue",      stats["max_queue"])
    cols[5].metric("⚙️ Utilization ρ",  f"{LAMBDA/(NUM_SERVERS*MU):.3f}")
 
 
with tab1:
    st.markdown("### M/D/2 — Centralized queue · Deterministic service")
    metric_row(s1)
    st.plotly_chart(system_dashboard(
        "M/D/2 — Centralized Queue, Deterministic Service",
        wt1, ql1, ss1, COLORS["M/D/2"]), use_container_width=True)
 
with tab2:
    st.markdown("### M/M/2 — Centralized queue · Exponential service")
    metric_row(s2)
    st.plotly_chart(system_dashboard(
        "M/M/2 — Centralized Queue, Exponential Service",
        wt2, ql2, ss2, COLORS["M/M/2"]), use_container_width=True)
 
with tab3:
    st.markdown("### Tunisian — Two separate queues · Join shortest · No switching")
    metric_row(s3)
    st.plotly_chart(system_dashboard(
        "Tunisian System — Two Separate Queues, Join Shortest",
        wt3, ql3, ss3, COLORS["Tunisian"]), use_container_width=True)
 
with tab4:
    st.markdown("### Head-to-head comparison")
 
    df = pd.DataFrame({
        "System":           ["M/D/2", "M/M/2", "Tunisian"],
        "Customers served": [s1["n_served"],  s2["n_served"],  s3["n_served"]],
        "Avg wait (min)":   [round(s1["avg_wait"],  4), round(s2["avg_wait"],  4), round(s3["avg_wait"],  4)],
        "Max wait (min)":   [round(s1["max_wait"],  4), round(s2["max_wait"],  4), round(s3["max_wait"],  4)],
        "Avg queue len":    [round(s1["avg_queue"], 4), round(s2["avg_queue"], 4), round(s3["avg_queue"], 4)],
        "Max queue len":    [s1["max_queue"],  s2["max_queue"],  s3["max_queue"]],
        "Both idle %":      [f"{100*s1['p_idle']:.1f}%", f"{100*s2['p_idle']:.1f}%", f"{100*s3['p_idle']:.1f}%"],
        "One busy %":       [f"{100*s1['p_one']:.1f}%",  f"{100*s2['p_one']:.1f}%",  f"{100*s3['p_one']:.1f}%"],
        "Both busy %":      [f"{100*s1['p_two']:.1f}%",  f"{100*s2['p_two']:.1f}%",  f"{100*s3['p_two']:.1f}%"],
    })
    st.dataframe(df.set_index("System"), use_container_width=True)
    st.markdown("---")
 
    fig_bar, fig_hist, fig_q, fig_states = comparison_charts(
        s1, s2, s3, wt1, wt2, wt3, ql1, ql2, ql3
    )
    st.plotly_chart(fig_bar,    use_container_width=True)
    st.plotly_chart(fig_hist,   use_container_width=True)
    st.plotly_chart(fig_q,      use_container_width=True)
    st.plotly_chart(fig_states, use_container_width=True)
 
