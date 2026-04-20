import streamlit as st
import simpy
import random
import math
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Queueing Simulation Dashboard",
    page_icon="📊",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.header("⚙️ Simulation Parameters")

LAMBDA      = st.sidebar.slider("Arrival rate λ (customers/min)", 0.1, 3.0, 1.0, 0.1)
MU          = st.sidebar.slider("Service rate μ (customers/min)", 0.1, 3.0, 1.0, 0.1)
NUM_SERVERS = 2
SIM_TIME    = st.sidebar.slider("Simulation time (min)", 30, 300, 120, 10)
SEED        = st.sidebar.number_input("Random seed", value=42, step=1)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Systems:**\n"
    "- **M/D/2** — exponential arrivals, deterministic service, shared queue\n"
    "- **M/M/2** — exponential arrivals & service, shared queue\n"
    "- **Tunisian** — exponential arrivals & service, 2 separate queues (join shortest)"
)
rho = LAMBDA / (NUM_SERVERS * MU)
color = "red" if rho >= 1 else "green"
st.sidebar.markdown(f"**Utilization ρ = {rho:.3f}** — system is {'⚠️ overloaded!' if rho >= 1 else '✅ stable'}")

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
            yield env.timeout(1.0 / mu)   # deterministic
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
        "n_served":   len(wt),
        "avg_wait":   float(np.mean(wt)),
        "max_wait":   float(np.max(wt)),
        "avg_queue":  float(np.mean(qlens)),
        "max_queue":  int(np.max(qlens)),
        "p_idle":     p_idle,
        "p_one":      p_one,
        "p_two":      p_two,
    }


# ─────────────────────────────────────────────────────────────────────────────
# RUN SIMULATIONS (cached on parameter change)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def run_all(lam, mu, sim_time, seed):
    wt1, ql1, ss1             = run_md2(lam, mu, sim_time, seed)
    wt2, ql2, ss2             = run_mm2(lam, mu, sim_time, seed)
    wt3, ql3, ss3, q1l, q2l  = run_tunisian(lam, mu, sim_time, seed)
    return (wt1, ql1, ss1), (wt2, ql2, ss2), (wt3, ql3, ss3, q1l, q2l)


with st.spinner("Running simulations…"):
    (wt1, ql1, ss1), (wt2, ql2, ss2), (wt3, ql3, ss3, q1l, q2l) = run_all(
        LAMBDA, MU, SIM_TIME, int(SEED)
    )

s1 = compute_stats(wt1, ql1, ss1, SIM_TIME)
s2 = compute_stats(wt2, ql2, ss2, SIM_TIME)
s3 = compute_stats(wt3, ql3, ss3, SIM_TIME)

# ─────────────────────────────────────────────────────────────────────────────
# PLOT HELPERS
# ─────────────────────────────────────────────────────────────────────────────
COLORS = {"M/D/2": "#2196F3", "M/M/2": "#FF5722", "Tunisian": "#4CAF50"}

def system_dashboard(name, wt, ql, ss, color):
    wt   = np.array(wt)
    tq, qlens = zip(*ql)
    ts, sbusy  = zip(*ss)
    avg_w = np.mean(wt)
    avg_q = np.mean(qlens)
    p_idle, p_one, p_two = time_weighted_proportions(ts, sbusy, SIM_TIME)

    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=(
            "Queue length over time", "Busy servers over time", "Server state (time-weighted)",
            "Waiting time per customer", "Waiting time distribution", ""
        ),
        specs=[
            [{"colspan": 2}, None, {}],
            [{},             {},   {"type": "domain"}],
        ],
    )

    # Queue length
    fig.add_trace(go.Scatter(x=list(tq), y=list(qlens), mode="lines", name="Queue length",
                             line=dict(color=color, width=1.2, shape="hv")), row=1, col=1)
    fig.add_hline(y=avg_q, line_dash="dash", line_color="crimson",
                  annotation_text=f"avg={avg_q:.2f}", row=1, col=1)

    # Busy servers
    fig.add_trace(go.Scatter(x=list(ts), y=list(sbusy), mode="lines", name="Busy servers",
                             line=dict(color="mediumpurple", width=1, shape="hv")), row=1, col=3)

    # Waiting time per customer
    fig.add_trace(go.Scatter(y=wt, mode="lines", name="Wait time",
                             line=dict(color="teal", width=0.9)), row=2, col=1)
    fig.add_hline(y=avg_w, line_dash="dash", line_color="crimson",
                  annotation_text=f"avg={avg_w:.3f}", row=2, col=1)

    # Histogram
    fig.add_trace(go.Histogram(x=wt, nbinsx=25, name="Distribution",
                               marker_color="coral", opacity=0.85), row=2, col=2)
    fig.add_vline(x=avg_w, line_dash="dash", line_color="darkred", row=2, col=2)

    # Pie
    fig.add_trace(go.Pie(
        labels=["Both idle", "One busy", "Both busy"],
        values=[p_idle, p_one, p_two],
        marker_colors=["#a8d8ea", "#7eb8c9", "#3a7ca5"],
        textinfo="label+percent",
        hole=0.3,
    ), row=2, col=3)

    fig.update_layout(
        height=600,
        showlegend=False,
        title_text=f"<b>{name}</b>",
        title_font_size=16,
        margin=dict(t=80, b=20, l=20, r=20),
    )
    fig.update_yaxes(title_text="Waiting customers", row=1, col=1)
    fig.update_yaxes(title_text="Servers busy",      row=1, col=3)
    fig.update_yaxes(title_text="Wait (min)",         row=2, col=1)
    fig.update_yaxes(title_text="Frequency",          row=2, col=2)
    fig.update_xaxes(title_text="Time (min)", row=1, col=1)
    fig.update_xaxes(title_text="Time (min)", row=1, col=3)
    fig.update_xaxes(title_text="Customer #", row=2, col=1)
    fig.update_xaxes(title_text="Wait (min)", row=2, col=2)
    return fig


def comparison_charts(s1, s2, s3, wt1, wt2, wt3, ql1, ql2, ql3, ts1, ts2, ts3):
    names  = ["M/D/2", "M/M/2", "Tunisian"]
    colors = [COLORS[n] for n in names]

    # Bar metrics
    metrics = {
        "Avg wait (min)":  [s1["avg_wait"],  s2["avg_wait"],  s3["avg_wait"]],
        "Max wait (min)":  [s1["max_wait"],  s2["max_wait"],  s3["max_wait"]],
        "Avg queue len":   [s1["avg_queue"], s2["avg_queue"], s3["avg_queue"]],
        "Max queue len":   [s1["max_queue"], s2["max_queue"], s3["max_queue"]],
    }

    fig_bar = make_subplots(rows=2, cols=2,
                            subplot_titles=list(metrics.keys()))
    positions = [(1,1),(1,2),(2,1),(2,2)]
    for (r, c), (title, vals) in zip(positions, metrics.items()):
        fig_bar.add_trace(
            go.Bar(x=names, y=vals, marker_color=colors, showlegend=False),
            row=r, col=c
        )
    fig_bar.update_layout(height=500, title_text="<b>Comparative Metrics</b>",
                          title_font_size=16, margin=dict(t=80, b=20))

    # Overlapping wait-time histograms
    fig_hist = go.Figure()
    for name, wt, col in zip(names, [wt1, wt2, wt3], colors):
        fig_hist.add_trace(go.Histogram(
            x=np.array(wt), nbinsx=30, name=name,
            marker_color=col, opacity=0.55,
        ))
    fig_hist.update_layout(
        barmode="overlay",
        title_text="<b>Waiting Time Distributions (overlay)</b>",
        xaxis_title="Wait (min)",
        yaxis_title="Frequency",
        height=380,
        legend=dict(orientation="h", y=1.08),
        margin=dict(t=60, b=40),
    )

    # Queue length over time overlay
    fig_q = go.Figure()
    for name, ql, col in zip(names, [ql1, ql2, ql3], colors):
        tq, qlens = zip(*ql)
        fig_q.add_trace(go.Scatter(
            x=list(tq), y=list(qlens), mode="lines",
            name=name, line=dict(color=col, width=1.2, shape="hv"),
            opacity=0.8,
        ))
    fig_q.update_layout(
        title_text="<b>Queue Length Over Time (all systems)</b>",
        xaxis_title="Time (min)", yaxis_title="Queue length",
        height=340,
        legend=dict(orientation="h", y=1.08),
        margin=dict(t=60, b=40),
    )

    # Server state stacked bar
    fig_states = go.Figure(data=[
        go.Bar(name="Both idle",  x=names, y=[s1["p_idle"], s2["p_idle"], s3["p_idle"]],
               marker_color="#a8d8ea"),
        go.Bar(name="One busy",   x=names, y=[s1["p_one"],  s2["p_one"],  s3["p_one"]],
               marker_color="#7eb8c9"),
        go.Bar(name="Both busy",  x=names, y=[s1["p_two"],  s2["p_two"],  s3["p_two"]],
               marker_color="#3a7ca5"),
    ])
    fig_states.update_layout(
        barmode="stack",
        title_text="<b>Server State Distribution (time-weighted)</b>",
        yaxis_title="Fraction of time",
        yaxis_tickformat=".0%",
        height=340,
        legend=dict(orientation="h", y=1.08),
        margin=dict(t=60, b=40),
    )

    return fig_bar, fig_hist, fig_q, fig_states


# ─────────────────────────────────────────────────────────────────────────────
# PAGE LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
st.title("📊 Queueing Simulation Dashboard")
st.caption(f"λ={LAMBDA}, μ={MU}, servers=2, T={SIM_TIME} min, seed={int(SEED)}")

tab1, tab2, tab3, tab4 = st.tabs(["M/D/2", "M/M/2", "Tunisian", "📊 Comparison"])

def metric_row(stats):
    cols = st.columns(6)
    cols[0].metric("Customers served",  stats["n_served"])
    cols[1].metric("Avg wait (min)",    f"{stats['avg_wait']:.3f}")
    cols[2].metric("Max wait (min)",    f"{stats['max_wait']:.3f}")
    cols[3].metric("Avg queue length",  f"{stats['avg_queue']:.3f}")
    cols[4].metric("Max queue length",  stats["max_queue"])
    cols[5].metric("Utilization ρ",     f"{LAMBDA/(NUM_SERVERS*MU):.3f}")

with tab1:
    metric_row(s1)
    st.plotly_chart(system_dashboard("M/D/2 — Centralized queue, deterministic service",
                                     wt1, ql1, ss1, COLORS["M/D/2"]),
                    use_container_width=True)

with tab2:
    metric_row(s2)
    st.plotly_chart(system_dashboard("M/M/2 — Centralized queue, exponential service",
                                     wt2, ql2, ss2, COLORS["M/M/2"]),
                    use_container_width=True)

with tab3:
    metric_row(s3)
    st.plotly_chart(system_dashboard("Tunisian — Two separate queues (join shortest)",
                                     wt3, ql3, ss3, COLORS["Tunisian"]),
                    use_container_width=True)

with tab4:
    st.subheader("Head-to-head comparison")

    # Summary table
    import pandas as pd
    df = pd.DataFrame({
        "System":           ["M/D/2", "M/M/2", "Tunisian"],
        "Customers served": [s1["n_served"],  s2["n_served"],  s3["n_served"]],
        "Avg wait (min)":   [round(s1["avg_wait"],4),  round(s2["avg_wait"],4),  round(s3["avg_wait"],4)],
        "Max wait (min)":   [round(s1["max_wait"],4),  round(s2["max_wait"],4),  round(s3["max_wait"],4)],
        "Avg queue len":    [round(s1["avg_queue"],4), round(s2["avg_queue"],4), round(s3["avg_queue"],4)],
        "Max queue len":    [s1["max_queue"],  s2["max_queue"],  s3["max_queue"]],
        "Both idle %":      [f"{100*s1['p_idle']:.1f}%", f"{100*s2['p_idle']:.1f}%", f"{100*s3['p_idle']:.1f}%"],
        "One busy %":       [f"{100*s1['p_one']:.1f}%",  f"{100*s2['p_one']:.1f}%",  f"{100*s3['p_one']:.1f}%"],
        "Both busy %":      [f"{100*s1['p_two']:.1f}%",  f"{100*s2['p_two']:.1f}%",  f"{100*s3['p_two']:.1f}%"],
    })
    st.dataframe(df.set_index("System"), use_container_width=True)

    fig_bar, fig_hist, fig_q, fig_states = comparison_charts(
        s1, s2, s3, wt1, wt2, wt3, ql1, ql2, ql3, ss1, ss2, ss3
    )
    st.plotly_chart(fig_bar,    use_container_width=True)
    st.plotly_chart(fig_hist,   use_container_width=True)
    st.plotly_chart(fig_q,      use_container_width=True)
    st.plotly_chart(fig_states, use_container_width=True)
