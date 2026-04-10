import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# Ρύθμιση σελίδας
st.set_page_config(page_title="Pro Predictor v16.38", layout="wide")

# --- CSS ΓΙΑ ΤΟ ΤΕΛΙΚΟ DESIGN (V16.38 FIXES) ---
st.markdown("""
    <style>
    /* 1. Φόντο v16.27 */
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), 
        url("https://images.unsplash.com/photo-1504450758481-7338eba7524a?q=80&w=2069&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* 2. Sidebar: ΣΚΟΥΡΟ ΓΚΡΙ & Διορθωμένος Πίνακας */
    [data-testid="stSidebar"] {
        background-color: #1e1e1e !important;
    }
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    
    /* Πιο γκρι/σκούρος πίνακας για ομαλή μετάβαση */
    [data-testid="stSidebar"] .stDataFrame {
        background-color: #2b2b2b !important;
        border-radius: 10px;
    }
    
    /* 3. ΕΠΙΒΟΛΗ ΛΕΥΚΩΝ ΓΡΑΜΜΑΤΩΝ ΣΤΟΥΣ ΑΓΩΝΕΣ (Force All Layers) */
    div[data-testid="stExpander"] p, 
    div[data-testid="stExpander"] span, 
    div[data-testid="stExpander"] label,
    .streamlit-expanderHeader {
        color: white !important;
        fill: white !important;
        -webkit-text-fill-color: white !important;
    }

    .streamlit-expanderHeader p {
        font-weight: 800 !important;
        font-size: 1.2rem !important;
        text-shadow: 2px 2px 4px #000000 !important;
    }

    /* 4. Διαχωριστική Γραμμή Αγωνιστικής */
    .matchday-divider {
        border: 0;
        height: 3px;
        background: linear-gradient(to right, transparent, #00ff88, #ffffff, #00ff88, transparent);
        margin: 40px 0 20px 0;
    }
    
    /* 5. Dropdown Menu (Το κουτάκι που κύκλωσες) */
    div[data-baseweb="select"] > div {
        background-color: #333333 !important;
        color: white !important;
        border: 1px solid #444 !important;
    }

    /* 6. Hide Toolbars */
    [data-testid="stElementToolbar"] {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

API_KEY = "a963742bcd5642afbe8c842d057f25ad" 
LEAGUES = {
    'PL':'Premier League', 'PD':'La Liga', 'BL1':'Bundesliga', 
    'SA':'Serie A', 'FL1':'Ligue 1', 'CL':'Champions League', 
    'DED':'Eredivisie', 'ELC':'Championship'
}

@st.cache_data(ttl=60)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except: return {}

def get_colored_val(val):
    perc = round(val * 100)
    if perc >= 70:
        return f'<span style="color: #00ff88; font-weight: bold; font-size: 22px;">{perc}%</span>'
    return f'<span style="color: white; font-size: 18px;">{perc}%</span>'

# --- SIDEBAR ---
st.sidebar.markdown("## ⚙️ Ρυθμίσεις")

# Dropdown με τον τίτλο της διοργάνωσης
sel_league_name = st.sidebar.selectbox(
    "Επιλεγμένη Διοργάνωση:", 
    list(LEAGUES.values()),
    key="league_selector"
)
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# Standings Data
st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_dict = {}
num_teams = 20 

if st_data and 'standings' in st_data:
    st_table = st_data['standings'][0]['table']
    num_teams = len(st_table)
    for t in st_table:
        standings_dict[t['team']['name']] = {
            'gf': t['goalsFor']/t['playedGames'] if t['playedGames']>0 else 1.2, 
            'ga': t['goalsAgainst']/t['playedGames'] if t['playedGames']>0 else 1.2
        }
    
    st.sidebar.markdown(f"### 🏆 Βαθμολογία {sel_league_name}")
    df_sidebar = [{"#": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table]
    st.sidebar.dataframe(pd.DataFrame(df_sidebar), hide_index=True, use_container_width=True)

# Υπολογισμός αγώνων ανά αγωνιστική
matches_per_round = num_teams // 2

# --- MAIN ---
st.markdown(f'<h1 style="text-align:center; color:white; text-shadow: 2px 2px 10px #000;">⚽ {sel_league_name} Pro Predictor</h1>', unsafe_allow_html=True)

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
display_m = [m for m in all_data.get('matches', []) if m['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY']][:30]

for i, m in enumerate(display_m):
    # Διαχωριστική γραμμή ανά αγωνιστική
    if i > 0 and i % matches_per_round == 0:
        st.markdown('<div class="matchday-divider"></div>', unsafe_allow_html=True)

    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    h_stats = standings_dict.get(h_t, {'gf':1.2, 'ga':1.2})
    a_stats = standings_dict.get(a_t, {'gf':1.2, 'ga':1.2})
    h_l, a_l = (h_stats['gf'] + a_stats['ga'])/2, (a_stats['gf'] + h_stats['ga'])/2
    
    p1 = sum([poisson.pmf(k, h_l) * sum([poisson.pmf(j, a_l) for j in range(k)]) for k in range(1, 6)])
    px = sum([poisson.pmf(k, h_l) * poisson.pmf(k, a_l) for k in range(6)])
    p2 = max(0, 1 - p1 - px)
    pgg, po15, po25 = (1-poisson.pmf(0, h_l))*(1-poisson.pmf(0, a_l)), 1-sum([poisson.pmf(k, h_l+a_l) for k in range(2)]), 1-sum([poisson.pmf(k, h_l+a_l) for k in range(3)])

    # Τίτλος αγώνα - Επιβολή λευκού χρώματος
    date_label = f"{m['utcDate'][:10]} {m['utcDate'][11:16]}"
    match_title = f"{date_label} | {h_t} vs {a_t}"
    
    with st.expander(match_title):
        cols = st.columns(6)
        lbls, vals = ["1", "X", "2", "GG", "O1.5", "O2.5"], [p1, px, p2, pgg, po15, po25]
        for idx in range(6):
            cols[idx].markdown(f"""
                <div style="text-align:center; background:rgba(255,255,255,0.05); padding:10px; border-radius:10px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="color:#bbb; font-size:12px;">{lbls[idx]}</div>
                    {get_colored_val(vals[idx])}
                </div>
            """, unsafe_allow_html=True)
