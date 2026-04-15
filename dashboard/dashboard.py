# dashboard.py — Monitor de Microsegmentacion SDN
# Autor: Hector Munoz Rubio
# TFG — Microsegmentacion de red en entornos SDN

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import time
import json
import requests
import warnings
from grafico import build_topology_figure

# Ignorar TODOS los molestos avisos de deprecación (Streamlit y Plotly)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*keyword arguments.*deprecated.*")
warnings.filterwarnings("ignore", message=".*use_container_width.*")

# ---------------------------------------------------------------------------
#  CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SDN Microsegmentación — Dashboard",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
#  PALETA DE COLORES & TOKENS DE DISEÑO
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#0a0e17",
    "surface": "#111827",
    "surface2": "#1a2235",
    "border": "#1e293b",
    "text": "#e2e8f0",
    "text_muted": "#94a3b8",
    "accent": "#6366f1",  # indigo-500
    "accent_glow": "rgba(99,102,241,0.25)",
    "allowed": "#22c55e",  # green-500
    "blocked": "#ef4444",  # red-500
    "cyan": "#06b6d4",
    "amber": "#f59e0b",
    "purple": "#a855f7",
    "rose": "#f43f5e",
}

# Plotly layout reutilizable
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=COLORS["text"], size=13),
    margin=dict(l=24, r=24, t=48, b=24),
    legend=dict(
        bgcolor="rgba(17,24,39,0.85)",
        bordercolor=COLORS["border"],
        borderwidth=1,
        font=dict(size=12, color=COLORS["text"]),
    ),
)

_AXIS_DEFAULTS = dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"])

# ---------------------------------------------------------------------------
#  CSS GLOBAL — dark theme, tipografía Inter, glassmorphism
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Reset general ───────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"],
.main, .block-container, [data-testid="stHeader"],
section[data-testid="stSidebar"] {
    background-color: %(bg)s !important;
    color: %(text)s !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stHeader"] { background: transparent !important; }

/* ── Tabs ─────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: %(surface)s;
    border-radius: 12px;
    padding: 4px;
    border: 1px solid %(border)s;
}
.stTabs [data-baseweb="tab"] {
    color: %(text_muted)s !important;
    font-weight: 500;
    font-size: 14px;
    padding: 10px 24px;
    border-radius: 8px;
    transition: all .2s ease;
}
.stTabs [aria-selected="true"] {
    background: %(accent)s !important;
    color: #fff !important;
    font-weight: 600;
    box-shadow: 0 0 20px %(accent_glow)s;
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"] { display: none; }

/* ── Métricas glassmorphism ──────────────────────────────────────── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(17,24,39,.8), rgba(26,34,53,.6));
    backdrop-filter: blur(12px);
    border: 1px solid %(border)s;
    border-radius: 14px;
    padding: 20px 24px;
    transition: transform .15s ease, box-shadow .15s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,0,0,.35);
}
[data-testid="stMetricLabel"] {
    color: %(text_muted)s !important;
    font-weight: 500;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: .6px;
}
[data-testid="stMetricValue"] {
    color: %(text)s !important;
    font-weight: 700;
    font-size: 28px !important;
}

/* ── Dataframes ──────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid %(border)s;
    border-radius: 12px;
    overflow: hidden;
}

/* ── Expanders ───────────────────────────────────────────────────── */
details {
    background: %(surface)s !important;
    border: 1px solid %(border)s !important;
    border-radius: 12px !important;
}
details summary {
    color: %(text)s !important;
    font-weight: 600;
}

/* ── Botones de descarga ─────────────────────────────────────────── */
.stDownloadButton > button {
    background: transparent !important;
    color: %(accent)s !important;
    border: 1px solid %(border)s !important;
    border-radius: 10px;
    font-weight: 600;
    transition: all .2s ease;
}
.stDownloadButton > button:hover {
    background: %(accent)s !important;
    color: #fff !important;
    border-color: %(accent)s !important;
}

/* ── Multiselect ─────────────────────────────────────────────────── */
[data-baseweb="select"] {
    background: %(surface)s !important;
    border-color: %(border)s !important;
    border-radius: 10px;
}

/* ── Dividers ────────────────────────────────────────────────────── */
hr { border-color: %(border)s !important; opacity: .4; }

/* ── Titles / subtitles ──────────────────────────────────────────── */
h1, h2, h3, h4 { color: %(text)s !important; letter-spacing: -.02em; }
.section-title {
    font-size: 15px;
    font-weight: 600;
    color: %(text_muted)s;
    text-transform: uppercase;
    letter-spacing: .8px;
    margin-bottom: 16px;
}

/* ── Captions ────────────────────────────────────────────────────── */
.stCaption, [data-testid="stCaptionContainer"] {
    color: %(text_muted)s !important;
}
</style>
""" % COLORS,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
#  HEADER
# ---------------------------------------------------------------------------
st.markdown(
    """
<div style="display:flex; align-items:center; gap:14px; margin-bottom:8px;">
<div style="width:42px; height:42px; background:%(accent)s; border-radius:10px;
            display:flex; align-items:center; justify-content:center;
            box-shadow:0 0 24px %(accent_glow)s;">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
</div>
<div>
    <span style="font-size:24px; font-weight:700; color:%(text)s;
                letter-spacing:-.03em;">
    Monitor de Microsegmentacion SDN
    </span><br/>
    <span style="font-size:13px; color:%(text_muted)s; font-weight:400;">
    Firewall &middot; Politicas &middot; Topologia VXLAN Multi-Sitio
    </span>
</div>
</div>
""" % COLORS,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
#  RUTAS
# ---------------------------------------------------------------------------
db_path = "data/log_firewall.db"
config_path = "config_politicas.json"


# ---------------------------------------------------------------------------
#  FUNCIONES DE CARGA
# ---------------------------------------------------------------------------
def load_config():
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error cargando config: {e}")
        return None


def load_logs():
    if not os.path.exists(db_path):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM logs ORDER BY id ASC", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error al leer la base de datos: {e}")
        return pd.DataFrame()


config = load_config()

# ═══════════════════════════════════════════════════════════════════════════
#  TABS
# ═══════════════════════════════════════════════════════════════════════════
tab_politicas, tab_logs, tab_topologia, tab_tools = st.tabs(
    [
        "Politicas de Seguridad",
        "Monitor de Trafico",
        "Topologia de Red",
        "Herramientas",
    ]
)

# ═══════════════════════════════════════════════════════════════════════════
#  TAB 1 — POLÍTICAS
# ═══════════════════════════════════════════════════════════════════════════
with tab_politicas:
    if config:
        st.markdown(
            '<p class="section-title">Configuracion activa</p>',
            unsafe_allow_html=True,
        )

        col_groups, col_policies = st.columns(2, gap="large")

        # ── Grupos & Hosts ──────────────────────────────────────────────
        with col_groups:
            st.markdown("#### Grupos y Hosts")
            groups_data = []
            for ip, group in config["host_groups"].items():
                mac = config["host_macs"].get(ip, "N/A")
                groups_data.append({"IP": ip, "Grupo": group, "MAC": mac})
            df_groups = pd.DataFrame(groups_data)

            group_colors = {
                "VENTAS": COLORS["cyan"],
                "IT": COLORS["amber"],
                "WEB_SERVER": COLORS["purple"],
                "DB_SERVER": "#8b5cf6",
                "ATTACKER": COLORS["rose"],
                "HONEYPOT": "#fb7185",
                "IDS": "#38bdf8",
            }

            def color_group(val):
                c = group_colors.get(val, COLORS["text_muted"])
                return (
                    f"background-color:{c}; color:#fff; font-weight:600;"
                    f"border-radius:6px; padding:2px 8px;"
                )

            st.dataframe(
                df_groups.style.map(color_group, subset=["Grupo"]),
                use_container_width=True,
                hide_index=True,
            )

        # ── Políticas Permitidas ────────────────────────────────────────
        with col_policies:
            st.markdown("#### Politicas Permitidas")
            policies_data = []
            for pol in config["allowed_policies"]:
                policies_data.append(
                    {
                        "Origen": pol[0],
                        "Destino": pol[1],
                        "Flujo": f"{pol[0]}  →  {pol[1]}",
                    }
                )
            st.dataframe(
                pd.DataFrame(policies_data),
                use_container_width=True,
                hide_index=True,
            )

            # KPIs compactos
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Reglas", len(config["allowed_policies"]))
            kpi2.metric("Hosts", len(config["host_macs"]))
            kpi3.metric("Switches", len(config["routing_table"]))

        st.divider()

        # ── Matriz de Políticas ─────────────────────────────────────────
        st.markdown("#### Matriz de Politicas")
        st.caption("Comunicacion permitida entre segmentos de red")

        all_groups = sorted(set(config["host_groups"].values()))
        policy_set = set(tuple(p) for p in config["allowed_policies"])

        matrix_data = []
        for src in all_groups:
            row = {}
            for dst in all_groups:
                row[dst] = 1 if (src, dst) in policy_set else 0
            matrix_data.append(row)
        df_matrix = pd.DataFrame(matrix_data, index=all_groups, columns=all_groups)

        fig_matrix = go.Figure(
            data=go.Heatmap(
                z=df_matrix.values,
                x=all_groups,
                y=all_groups,
                colorscale=[
                    [0, "rgba(239,68,68,0.25)"],
                    [1, "rgba(34,197,94,0.35)"],
                ],
                showscale=False,
                hovertemplate="Origen: %{y}<br>Destino: %{x}<br>%{z}<extra></extra>",
            )
        )
        # Annotations
        for i, src in enumerate(all_groups):
            for j, dst in enumerate(all_groups):
                val = df_matrix.iloc[i, j]
                fig_matrix.add_annotation(
                    x=dst,
                    y=src,
                    text="Permitido" if val == 1 else "Bloqueado",
                    showarrow=False,
                    font=dict(
                        size=11,
                        color=COLORS["allowed"] if val else COLORS["blocked"],
                        family="Inter",
                    ),
                )
        fig_matrix.update_layout(
            **PLOTLY_LAYOUT,
            height=460,
            xaxis=dict(
                title="Grupo Destino",
                side="top",
                gridcolor=COLORS["border"],
                tickfont=dict(size=12, color=COLORS["text"]),
                title_font=dict(size=13, color=COLORS["text_muted"]),
            ),
            yaxis=dict(
                title="Grupo Origen",
                autorange="reversed",
                gridcolor=COLORS["border"],
                tickfont=dict(size=12, color=COLORS["text"]),
                title_font=dict(size=13, color=COLORS["text_muted"]),
            ),
        )
        st.plotly_chart(
            fig_matrix, use_container_width=True, config={"displayModeBar": False}
        )

        st.divider()

        # ── Tabla de Enrutamiento ───────────────────────────────────────
        st.markdown("#### Tabla de Enrutamiento por Switch")

        port_map = {
            "1": {1: "S2 (Usuarios)", 2: "S3 (Data Center)", 3: "S4 (Seguridad)"},
            "2": {1: "S1 (Core)"},
            "3": {1: "S1 (Core)"},
            "4": {1: "S1 (Core)"},
            "5": {1: "S6 (DC-B)", 2: "S7 (Usuarios B)", 3: "S8 (DMZ-B)"},
            "6": {1: "S5 (Core)"},
            "7": {1: "S5 (Core)"},
            "8": {1: "S5 (Core)"},
        }

        for sw_id, routes in config["routing_table"].items():
            with st.expander(f"Switch S{sw_id}"):
                routes_data = []
                for network, port in routes.items():
                    destino = port_map.get(str(sw_id), {}).get(port, f"Puerto {port}")
                    routes_data.append(
                        {
                            "Red Destino": network,
                            "Puerto Salida": port,
                            "Siguiente Salto": f"Puerto {port}  →  {destino}",
                        }
                    )
                st.dataframe(
                    pd.DataFrame(routes_data),
                    use_container_width=True,
                    hide_index=True,
                )
    else:
        st.error("No se pudo cargar la configuracion")

# ═══════════════════════════════════════════════════════════════════════════
#  TAB 2 — MONITOR DE TRÁFICO (fragmento auto-refrescado)
# ═══════════════════════════════════════════════════════════════════════════
with tab_logs:

    @st.fragment(run_every=5)
    def live_traffic_monitor():
        df = load_logs()
        if df.empty:
            st.info(
                "Esperando eventos — realiza un ping en Mininet para generar trafico."
            )
            return

        st.markdown(
            '<p class="section-title">Trafico en tiempo real</p>',
            unsafe_allow_html=True,
        )
        st.caption(f"Ultima actualizacion: {time.strftime('%H:%M:%S')}")

        # ── KPIs ────────────────────────────────────────────────────────
        total = len(df)
        blocked = len(df[df["action"] == "BLOQUEADO"])
        allowed = len(df[df["action"] == "PERMITIDO"])
        block_rate = (blocked / total) * 100 if total > 0 else 0

        c1, c2, c3, c4 = st.columns(4, gap="medium")
        c1.metric("Total Eventos", f"{total:,}")
        c2.metric("Bloqueados", f"{blocked:,}")
        c3.metric("Permitidos", f"{allowed:,}")
        c4.metric("Tasa de Bloqueo", f"{block_rate:.1f}%")

        st.divider()

        # ── Evolución temporal + Distribución ───────────────────────────
        col_time, col_pie = st.columns([2, 1], gap="large")

        with col_time:
            st.markdown("#### Evolucion Temporal")
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df_time = (
                df.groupby([pd.Grouper(key="timestamp", freq="10s"), "action"])
                .size()
                .reset_index(name="count")
            )
            fig_time = px.area(
                df_time,
                x="timestamp",
                y="count",
                color="action",
                color_discrete_map={
                    "BLOQUEADO": COLORS["blocked"],
                    "PERMITIDO": COLORS["allowed"],
                },
                labels={"timestamp": "Tiempo", "count": "Eventos", "action": "Accion"},
            )
            fig_time.update_traces(line=dict(width=2), fillcolor=None)
            fig_time.update_layout(**PLOTLY_LAYOUT, height=360, showlegend=True)
            st.plotly_chart(
                fig_time, use_container_width=True, config={"displayModeBar": False}
            )

        with col_pie:
            st.markdown("#### Distribucion")
            fig_pie = go.Figure(
                data=[
                    go.Pie(
                        labels=["BLOQUEADO", "PERMITIDO"],
                        values=[blocked, allowed],
                        marker=dict(
                            colors=[COLORS["blocked"], COLORS["allowed"]],
                            line=dict(color=COLORS["bg"], width=3),
                        ),
                        hole=0.55,
                        textinfo="percent+label",
                        textfont=dict(size=12, family="Inter", color=COLORS["text"]),
                    )
                ]
            )
            fig_pie.update_layout(**PLOTLY_LAYOUT, height=360, showlegend=False)
            st.plotly_chart(
                fig_pie, use_container_width=True, config={"displayModeBar": False}
            )

        # ── Heatmap de tráfico entre segmentos ──────────────────────────
        st.markdown("#### Trafico entre Segmentos")
        matrix = df.pivot_table(
            index="src_group",
            columns="dst_group",
            values="id",
            aggfunc="count",
            fill_value=0,
        )
        fig_heat = go.Figure(
            data=go.Heatmap(
                z=matrix.values,
                x=matrix.columns.tolist(),
                y=matrix.index.tolist(),
                colorscale=[
                    [0.0, "rgba(99,102,241,0.05)"],
                    [0.5, "rgba(99,102,241,0.35)"],
                    [1.0, COLORS["accent"]],
                ],
                showscale=True,
                colorbar=dict(
                    tickfont=dict(color=COLORS["text_muted"]),
                    title=dict(text="Eventos", font=dict(color=COLORS["text_muted"])),
                ),
                hovertemplate="Origen: %{y}<br>Destino: %{x}<br>Eventos: %{z}<extra></extra>",
                texttemplate="%{z}",
                textfont=dict(color=COLORS["text"], size=12),
            )
        )
        fig_heat.update_layout(
            **PLOTLY_LAYOUT,
            height=420,
            xaxis=dict(
                title="Grupo Destino",
                side="top",
                gridcolor=COLORS["border"],
                tickfont=dict(size=12, color=COLORS["text"]),
            ),
            yaxis=dict(
                title="Grupo Origen",
                autorange="reversed",
                gridcolor=COLORS["border"],
                tickfont=dict(size=12, color=COLORS["text"]),
            ),
        )
        st.plotly_chart(
            fig_heat, use_container_width=True, config={"displayModeBar": False}
        )

        # ── Top IPs bloqueadas ──────────────────────────────────────────
        df_blocked = df[df["action"] == "BLOQUEADO"]
        if not df_blocked.empty:
            st.markdown("#### Top IPs Bloqueadas")
            top_src = df_blocked["src_ip"].value_counts().head(10)
            fig_bar = go.Figure(
                data=[
                    go.Bar(
                        y=top_src.index,
                        x=top_src.values,
                        orientation="h",
                        marker=dict(
                            color=COLORS["blocked"],
                            line=dict(width=0),
                            cornerradius=4,
                        ),
                        hovertemplate="IP: %{y}<br>Bloqueos: %{x}<extra></extra>",
                    )
                ]
            )
            fig_bar.update_layout(
                **PLOTLY_LAYOUT,
                height=max(240, len(top_src) * 36 + 80),
                xaxis=dict(title="Bloqueos", gridcolor=COLORS["border"]),
                yaxis=dict(autorange="reversed", gridcolor=COLORS["border"]),
            )
            st.plotly_chart(
                fig_bar, use_container_width=True, config={"displayModeBar": False}
            )

        # ── Historial detallado ─────────────────────────────────────────
        st.markdown("#### Historial Detallado")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_action = st.multiselect(
                "Filtrar por accion",
                df["action"].unique(),
                default=list(df["action"].unique()),
                key="frag_filter_action",
            )
        with col_f2:
            filter_group = st.multiselect(
                "Filtrar por grupo origen",
                df["src_group"].unique(),
                default=list(df["src_group"].unique()),
                key="frag_filter_group",
            )

        df_filtered = df[
            (df["action"].isin(filter_action)) & (df["src_group"].isin(filter_group))
        ]

        def highlight_action(val):
            c = COLORS["blocked"] if val == "BLOQUEADO" else COLORS["allowed"]
            return f"color:{c}; font-weight:700;"

        st.dataframe(
            df_filtered.style.map(highlight_action, subset=["action"]),
            use_container_width=True,
        )

        st.divider()

        # ── Descargas ───────────────────────────────────────────────────
        dl1, dl2 = st.columns(2)
        with dl1:
            csv_full = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Descargar CSV completo",
                csv_full,
                "logs_firewall.csv",
                "text/csv",
                key="dl_csv_full",
            )
        with dl2:
            resumen = (
                df.groupby(["src_group", "dst_group", "action"])
                .size()
                .reset_index(name="count")
            )
            csv_resumen = resumen.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Descargar Resumen",
                csv_resumen,
                "resumen_politicas.csv",
                "text/csv",
                key="dl_csv_resumen",
            )

    live_traffic_monitor()

# ═══════════════════════════════════════════════════════════════════════════
#  TAB 3 — TOPOLOGÍA
# ═══════════════════════════════════════════════════════════════════════════
with tab_topologia:
    st.markdown(
        '<p class="section-title">Arquitectura de red SDN</p>',
        unsafe_allow_html=True,
    )
    st.caption("Topologia multi-sitio con microsegmentacion y VXLAN")

    if config:
        fig_topo = build_topology_figure(config)
    else:
        fig_topo = build_topology_figure()

    # Adapt topology chart to dark theme
    fig_topo.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=COLORS["surface"],
        font=dict(family="Inter, sans-serif", color=COLORS["text"]),
    )
    st.plotly_chart(
        fig_topo,
        use_container_width=True,
        config={
            "displayModeBar": False,
            "responsive": True,
        },
    )

# ═══════════════════════════════════════════════════════════════════════════
#  TAB 4 — HERRAMIENTAS (ping remoto)
# ═══════════════════════════════════════════════════════════════════════════
MININET_API = "http://mininet:5000"

# Mapa de hosts (estático, coincide con servidor_api.py y config_politicas.json)
HOST_LIST = [
    ("hv1", "10.0.1.1", "VENTAS"),
    ("hv2", "10.0.1.2", "VENTAS"),
    ("hv3", "10.0.1.3", "VENTAS"),
    ("hv4", "10.0.1.4", "VENTAS"),
    ("hit1", "10.0.2.1", "IT"),
    ("hit2", "10.0.2.2", "IT"),
    ("hit3", "10.0.2.3", "IT"),
    ("hit4", "10.0.2.4", "IT"),
    ("srv_web", "10.0.10.80", "WEB_SERVER"),
    ("srv_db", "10.0.10.33", "DB_SERVER"),
    ("backup", "10.0.10.50", "DB_SERVER"),
    ("attacker", "10.0.66.66", "ATTACKER"),
    ("honeypot", "10.0.66.77", "HONEYPOT"),
    ("honeypot2", "10.0.66.78", "HONEYPOT"),
    ("ids", "10.0.66.90", "IDS"),
]

with tab_tools:
    st.markdown(
        '<p class="section-title">Ping entre hosts</p>',
        unsafe_allow_html=True,
    )
    st.caption("Ejecuta pings entre hosts de Mininet directamente desde el dashboard")

    # ── Selectores ──────────────────────────────────────────────────────
    host_options = [f"{name}  ({ip})  [{group}]" for name, ip, group in HOST_LIST]

    with st.form("ping_form"):
        col_src, col_dst, col_count = st.columns([2, 2, 1], gap="large")

        with col_src:
            src_idx = st.selectbox(
                "Host Origen",
                range(len(host_options)),
                format_func=lambda i: host_options[i],
                index=0,
                key="ping_src",
            )
        with col_dst:
            dst_idx = st.selectbox(
                "Host Destino",
                range(len(host_options)),
                format_func=lambda i: host_options[i],
                index=9,  # srv_db por defecto
                key="ping_dst",
            )
        with col_count:
            ping_count = st.number_input(
                "Paquetes", min_value=1, max_value=20, value=4, key="ping_count"
            )

        run_ping = st.form_submit_button(
            "Ejecutar Ping", type="primary", use_container_width=True
        )

    if run_ping:
        src_name = HOST_LIST[src_idx][0]
        dst_name = HOST_LIST[dst_idx][0]
        src_ip = HOST_LIST[src_idx][1]
        dst_ip = HOST_LIST[dst_idx][1]

        if src_name == dst_name:
            st.warning("Origen y destino son el mismo host.")
        else:
            with st.spinner(
                f"Ejecutando ping: {src_name} ({src_ip})  ->  {dst_name} ({dst_ip}) ..."
            ):
                try:
                    resp = requests.post(
                        f"{MININET_API}/ping",
                        json={"src": src_name, "dst": dst_name, "count": ping_count},
                        timeout=30,
                    )
                    result = resp.json()

                    if result.get("ok"):
                        success = result.get("success", False)

                        # Header con resultado
                        if success:
                            st.markdown(
                                f'<div style="background:rgba(34,197,94,0.12); border:1px solid {COLORS["allowed"]};'
                                f' border-radius:12px; padding:16px 20px; margin:12px 0;">'
                                f'<span style="font-size:15px; font-weight:700; color:{COLORS["allowed"]};">'
                                f"Conectividad OK</span><br/>"
                                f'<span style="color:{COLORS["text_muted"]}; font-size:13px;">'
                                f'{result["src"]} ({result["src_ip"]})  ->  '
                                f'{result["dst"]} ({result["dst_ip"]})  ·  '
                                f'{result["count"]} paquetes</span></div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f'<div style="background:rgba(239,68,68,0.12); border:1px solid {COLORS["blocked"]};'
                                f' border-radius:12px; padding:16px 20px; margin:12px 0;">'
                                f'<span style="font-size:15px; font-weight:700; color:{COLORS["blocked"]};">'
                                f"Sin conectividad</span><br/>"
                                f'<span style="color:{COLORS["text_muted"]}; font-size:13px;">'
                                f'{result["src"]} ({result["src_ip"]})  ->  '
                                f'{result["dst"]} ({result["dst_ip"]})  ·  '
                                f'{result["count"]} paquetes</span></div>',
                                unsafe_allow_html=True,
                            )

                        # Output del ping
                        st.code(result.get("output", ""), language="text")
                    else:
                        st.error(
                            f"Error: {result.get('error', 'Respuesta inesperada')}"
                        )

                except requests.ConnectionError:
                    st.error(
                        "No se pudo conectar con la API de Mininet. "
                        "Asegurate de que estructura.py esta en ejecucion."
                    )
                except Exception as e:
                    st.error(f"Error inesperado: {e}")

    # ── Test de Microsegmentación ──────────────────────────────────────
    st.divider()
    st.markdown(
        '<p class="section-title">Test de Microsegmentacion</p>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Ejecuta la bateria completa de pruebas sobre todas las politicas de seguridad"
    )

    run_tests_btn = st.button(
        "Ejecutar Test Completo", type="primary", use_container_width=True
    )

    if run_tests_btn:
        with st.spinner(
            "Ejecutando bateria de pruebas — esto puede tardar unos minutos..."
        ):
            try:
                resp = requests.post(f"{MININET_API}/run_tests", timeout=600)
                st.session_state["test_result"] = resp.json()
            except requests.ConnectionError:
                st.session_state["test_result"] = {
                    "ok": False,
                    "error": "No se pudo conectar con la API de Mininet. "
                    "Asegurate de que estructura.py esta en ejecucion.",
                }
            except Exception as e:
                st.session_state["test_result"] = {"ok": False, "error": str(e)}

    # Mostrar resultados guardados
    if "test_result" in st.session_state:
        result = st.session_state["test_result"]

        if result.get("ok"):
            total = result.get("total", 0)
            passed = result.get("passed", 0)
            failed = total - passed
            pct = (passed / total * 100) if total > 0 else 0

            # KPIs del test
            k1, k2, k3, k4 = st.columns(4, gap="medium")
            k1.metric("Total Tests", total)
            k2.metric("Superados", passed)
            k3.metric("Fallidos", failed)
            k4.metric("Tasa de Exito", f"{pct:.0f}%")

            # Banner de resultado
            if failed == 0:
                st.markdown(
                    f'<div style="background:rgba(34,197,94,0.12); border:1px solid {COLORS["allowed"]};'
                    f' border-radius:12px; padding:16px 20px; margin:12px 0;">'
                    f'<span style="font-size:15px; font-weight:700; color:{COLORS["allowed"]};">'
                    f"Todas las pruebas superadas</span></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="background:rgba(239,68,68,0.12); border:1px solid {COLORS["blocked"]};'
                    f' border-radius:12px; padding:16px 20px; margin:12px 0;">'
                    f'<span style="font-size:15px; font-weight:700; color:{COLORS["blocked"]};">'
                    f"{failed} pruebas fallidas</span></div>",
                    unsafe_allow_html=True,
                )

            # Output completo
            st.code(result.get("output", ""), language="text")
        else:
            st.error(f"Error: {result.get('error', 'Respuesta inesperada')}")

# ═══════════════════════════════════════════════════════════════════════════
#  FOOTER GLOBAL
# ═══════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div style="text-align:center; padding:32px 0 12px; color:#475569; font-size:12px;">'
    "Desarrollado por Hector Munoz Rubio &middot; TFG &middot; Microsegmentacion de red en entornos SDN"
    "</div>",
    unsafe_allow_html=True,
)
