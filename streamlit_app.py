import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# 1. Βασική Ρύθμιση
st.set_page_config(page_title="Pro Predictor v16.24", layout="wide")

# 2. CSS - Εδώ διορθώνουμε όλα τα οπτικά θέματα
st.markdown("""
    <style>
    /* Φόντο: ΠΡΑΓΜΑΤΙΚΑ άδειο στάδιο τη νύχτα */
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.8)), 
        url("https://images.unsplash.com/photo-1504450758481-7338eba7524a?q=80&w=2069&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* SIDEBAR: Μαύρα γράμματα παντού για να διαβάζονται στο λευκό/γκρι φόντο */
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #000000 !important;
        font-weight: bold !important;
    }
    
    /* Μαύρο κουμπί Sidebar (αυτό που κύκλωσες) */
    [data-testid="stHeader"] button svg, 
    [data-testid="stSidebarCollapsedControl"] svg {
        fill: #000000 !important;
    }

    /* EXPANDERS: Λευκά γράμματα στους τίτλους των ματς */
    .streamlit-expanderHeader p {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
    }
    
    /* Αφαίρεση του Toolbar από τον πίνακα (αυτό που κύκλωσες) */
    [data-testid="stElementToolbar"] {
        display: none !important;
    }

    /* Τίτλος Αρχικής */
    .main-title {
        color: white !important;
        font-size: 2.5rem !important;
        font-weight: 800;
        text-align: center;
        margin-bottom: 20px;
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
        return f'<span style="color: #00ff00; font-weight: bold; font-size: 20px;">{perc}%</span>'
    return f'<span style="color: white; font-size: 18px;">{perc}%</span>'

# --- SIDEBAR ---
st.sidebar.markdown("### ⚙️ Ρυθμίσεις")
sel_league_name = st.sidebar.selectbox("Επιλογή Πρωταθλήματος:", list(LEAGUES.values()))
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# Standings
st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_dict = {}

if st_data and 'standings' in st_data:
    st.sidebar.markdown(f"### 🏆 {sel_league_name}")
    st_table = st_data['standings'][0]['table']
    for t in st_table:
        standings_dict[t['team']['name']] = {
            'gf': t['goalsFor'] / t['playedGames'] if t['playedGames'] > 0 else 1.2,
            'ga': t['goalsAgainst'] / t['playedGames'] if t['playedGames'] > 0 else 1.2
        }
    df_sidebar = [{"#": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table]
    st.sidebar.dataframe(pd.DataFrame(df_sidebar), hide_index=True, use_container_width=True)

# --- MAIN ---
st.markdown(f'<div class="main-title">⚽ {sel_league_name} Analysis</div>', unsafe_allow_html=True)

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = all_data.get('matches', [])
display_m = [m for m in all_m if m['status'] in ['IN_PLAY', 'PAUSED', 'SCHEDULED', 'TIMED']][:15]

for m in display_m:
    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    status = m['status']
    score = m.get('score', {}).get('fullTime', {})
    
    # Διόρθωση TypeError: Διασφαλίζουμε ότι τα σκορ είναι αριθμοί και όχι None
    cur_h = score.get('home') if score.get('home') is not None else 0
    cur_a = score.get('away') if score.get('away') is not None else 0
    
    h_stats = standings_dict.get(h_t, {'gf': 1.2, 'ga': 1.2})
    a_stats = standings_dict.get(a_t, {'gf': 1.2, 'ga': 1.2})
    h_l, a_l = (h_stats['gf'] + a_stats['ga'])/2, (a_stats['gf'] + h_stats['ga'])/2
    
    # Πιθανότητες
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 6)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(6)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po15 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(2)])
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])

    date_str = m['utcDate'][:10]
    time_str = m['utcDate'][11:16]
    
    # Τίτλος - Πάντα λευκός από το CSS
    if status in ['IN_PLAY', 'PAUSED']:
        title = f"🔴 LIVE {cur_h}-{cur_a} | {h_t} vs {a_t}"
    else:
        title = f"🗓️ {date_str} {time_str} | {h_t} vs {a_t}"

    with st.expander(title):
        cols = st.columns(6)
        lbls = ["1", "X", "2", "GG", "O1.5", "O2.5"]
        vals = [p1, px, p2, pgg, po15, po25]
        
        for i in range(6):
            with cols[i]:
                st.markdown(f"""<div style="text-align: center; background: rgba(0,0,0,0.5); padding: 10px; border-radius: 8px;">
                    <div style="color: #aaa; font-size: 12px;">{lbls[i]}</div>
                    {get_colored_val(vals[i])}
                </div>""", unsafe_allow_html=True)

