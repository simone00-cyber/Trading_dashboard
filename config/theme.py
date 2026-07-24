BG = "#050505"
PANEL = "#0e0e0e"
PANEL_2 = "#151515"
ORANGE = "#ff9f00"
GREEN = "#00d26a"
RED = "#ff3b3b"
TEXT = "#f2f2f2"
MUTED = "#9a9a9a"
GRID = "#2a2a2a"
BLUE = "#4da3ff"
CYAN = "#3ee6e0"
PURPLE = "#b58cff"

CUSTOM_CSS = f"""
<style>
html, body, [class*="css"] {{ font-family: Consolas, "Courier New", monospace; }}
.stApp {{ background: {BG}; color: {TEXT}; }}
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {{ display:none !important; visibility:hidden !important; height:0 !important; }}
.stApp > header {{ display:none !important; }}
.block-container {{ padding-top:.25rem !important; padding-bottom:3rem; max-width:100%; }}
section[data-testid="stSidebar"] {{ background:#080808; border-right:1px solid #272727; }}
section[data-testid="stSidebar"] * {{ color:{TEXT}; }}
h1,h2,h3 {{ color:{ORANGE} !important; letter-spacing:.02em; }}
.top-terminal-bar {{ display:flex; justify-content:space-between; align-items:center; background:{ORANGE}; color:#000; padding:.42rem .70rem; font-weight:900; border-bottom:2px solid #000; margin-bottom:.18rem; }}
.ticker-strip {{ display:flex; gap:1.10rem; flex-wrap:wrap; background:#0a0a0a; border-top:1px solid #292929; border-bottom:1px solid #292929; padding:.42rem .70rem; margin-bottom:.70rem; font-size:.84rem; }}
.terminal-header {{ background:{ORANGE}; color:#000; padding:.55rem .8rem; font-weight:800; font-size:1.05rem; margin-bottom:.7rem; border-radius:2px; }}
.terminal-subheader {{ color:{ORANGE}; border-bottom:1px solid {ORANGE}; padding-bottom:.25rem; margin:.9rem 0 .55rem 0; font-size:.95rem; font-weight:700; }}
.panel {{ border:1px solid #333; background:{PANEL}; padding:.8rem; }}
.report-box {{ border:1px solid #333; border-left:4px solid {ORANGE}; padding:1rem 1.1rem; background:{PANEL}; line-height:1.6; color:{TEXT}; }}
.signal-box {{ border:1px solid #3a3a3a; border-left:5px solid {ORANGE}; padding:.9rem 1rem; background:{PANEL_2}; margin-bottom:.8rem; }}
.small-note {{ color:{MUTED}; font-size:.82rem; }}
.regime-badge {{ padding:.55rem .8rem; font-size:1.35rem; font-weight:900; text-align:center; border:1px solid #444; background:{PANEL}; }}
div[data-testid="stMetric"] {{ background:{PANEL}; border:1px solid #303030; border-radius:2px; padding:.7rem; }}
div[data-testid="stMetricLabel"] {{ color:{MUTED}; }} div[data-testid="stMetricValue"] {{ color:{TEXT}; }}
button[kind="primary"] {{ background:{ORANGE} !important; color:#000 !important; border:1px solid {ORANGE} !important; }}
.stTabs [data-baseweb="tab-list"] {{ gap:2px; background:#080808; }}
.stTabs [data-baseweb="tab"] {{ background:{PANEL}; border:1px solid #292929; color:{TEXT}; border-radius:0; }}
.stTabs [aria-selected="true"] {{ background:{ORANGE} !important; color:#000 !important; }}
div[data-testid="stDataFrame"] {{ border:1px solid #303030; }} hr {{ border-color:#2b2b2b; }} code {{ color:{ORANGE}; }}
</style>
"""
