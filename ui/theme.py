"""Colours, chart layout and CSS shared by every page."""

from __future__ import annotations

import plotly.graph_objects as go

ISSUE_STATUS_COLORS = {
    "Open": "#3B82F6", "Reopened": "#8B5CF6", "In Progress": "#F59E0B", "Blocked": "#EF4444",
    "In Testing": "#06B6D4", "Resolved": "#10B981", "Closed": "#047857",
}
PRIORITY_COLORS = {"Highest": "#B91C1C", "High": "#F97316", "Medium": "#EAB308", "Low": "#3B82F6", "Lowest": "#94A3B8"}
EXECUTION_COLORS = {"Pass": "#16A34A", "Fail": "#DC2626", "Blocked": "#F97316", "In Progress": "#3B82F6", "Not Executed": "#94A3B8"}
ENVIRONMENT_COLORS = {"DEV": "#94A3B8", "SIT": "#60A5FA", "UAT": "#3B82F6", "PREPROD": "#1D4ED8", "PROD": "#DC2626"}
AUTOMATION_COLORS = {"Automated": "#2563EB", "Manual": "#94A3B8", "To Automate": "#F59E0B", "Not Automatable": "#CBD5E1"}
TEAM_COLORS = {"TEAM-A": "#2563EB", "TEAM-B": "#0D9488", "TEAM-C": "#7C3AED", "TEAM-D": "#DB2777", "TEAM-E": "#EA580C"}
TREND_COLORS = {"created": "#2563EB", "resolved": "#10B981"}
RAG_COLORS = {"green": "#16A34A", "amber": "#D97706", "red": "#DC2626"}
RAG_BACKGROUNDS = {"green": "#DCFCE7", "amber": "#FEF3C7", "red": "#FEE2E2"}

FONT = "Inter, Segoe UI, Helvetica, Arial, sans-serif"


def style_figure(fig: go.Figure, height: int = 320, legend: bool | str = True) -> go.Figure:
    """legend: True (top), "bottom" (centred below, for donuts) or False."""
    legend_layout = dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text="")
    if legend == "bottom":
        legend_layout = dict(orientation="h", yanchor="top", y=-0.02, xanchor="center", x=0.5, title_text="")
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=36, t=28, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color="#334155"),
        showlegend=bool(legend),
        legend=legend_layout,
        hoverlabel=dict(font_family=FONT),
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, linecolor="#E2E8F0", title_text="")
    fig.update_yaxes(gridcolor="#EEF2F7", zeroline=False, title_text="")
    return fig


CSS = """
<style>
.block-container {padding-top: 3.2rem; padding-bottom: 2rem; max-width: 1500px;}
h1, h2, h3 {letter-spacing: -0.01em;}
section[data-testid="stSidebar"] {background: #0F172A;}
section[data-testid="stSidebar"] * {color: #E2E8F0;}
section[data-testid="stSidebar"] [data-baseweb="select"] *,
section[data-testid="stSidebar"] [data-baseweb="input"] *,
section[data-testid="stSidebar"] input {color: #0F172A;}
section[data-testid="stSidebar"] [data-baseweb="tag"] {background: #2563EB;}
section[data-testid="stSidebar"] [data-baseweb="tag"] * {color: #FFFFFF;}
section[data-testid="stSidebar"] .stCaption, section[data-testid="stSidebar"] small {color: #94A3B8 !important;}
.brand {font-size: 1.15rem; font-weight: 700; color: #FFFFFF; margin-bottom: 0.1rem;}
.brand-sub {font-size: 0.78rem; color: #94A3B8; margin-bottom: 0.8rem;}

.page-title {font-size: 1.65rem; font-weight: 700; color: #0F172A; margin: 0;}
.page-sub {color: #64748B; font-size: 0.9rem; margin: 0.15rem 0 0.6rem 0;}
.chips {display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 1rem;}
.chip {background: #E8EEFC; color: #1E3A8A; border-radius: 999px; padding: 2px 10px; font-size: 0.76rem;}
.section-title {font-size: 1.02rem; font-weight: 650; color: #0F172A; margin: 1.1rem 0 0.4rem 0;
                border-left: 3px solid #2563EB; padding-left: 8px;}

.kpi-card {background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 12px 14px 10px 16px;
           box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04); min-height: 122px; position: relative; overflow: hidden;
           display: flex; flex-direction: column;}
.kpi-card::before {content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: #CBD5E1;}
.kpi-card.rag-green::before {background: #16A34A;}
.kpi-card.rag-amber::before {background: #D97706;}
.kpi-card.rag-red::before {background: #DC2626;}
.kpi-card.unresolved {background: repeating-linear-gradient(135deg, #FFFFFF, #FFFFFF 10px, #F8FAFC 10px, #F8FAFC 20px);}
.kpi-label {font-size: 0.8rem; color: #475569; font-weight: 600; line-height: 1.2;}
.kpi-value {font-size: 1.7rem; font-weight: 700; color: #0F172A; margin-top: 4px; line-height: 1.15;}
.kpi-value.muted {font-size: 1.05rem; color: #64748B; margin-top: 10px;}
.kpi-foot {display: flex; justify-content: space-between; align-items: center; gap: 6px; margin-top: auto; padding-top: 4px;}
.kpi-sub {font-size: 0.72rem; color: #64748B; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0;}
.badge {font-size: 0.64rem; font-weight: 600; border-radius: 6px; padding: 1px 6px; white-space: nowrap;}
.badge-standard {background: #E2E8F0; color: #334155;}
.badge-provisional {background: #FEF3C7; color: #92400E;}
.badge-proxy {background: #EDE9FE; color: #5B21B6;}
.badge-unresolved {background: #FEE2E2; color: #991B1B;}
</style>
"""
