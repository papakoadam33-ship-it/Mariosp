import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# Ρύθμιση σελίδας
st.set_page_config(page_title="Football Predictor Pro", layout="wide")

# --- CSS ΓΙΑ CLEAN DESIGN & SIDEBAR FIXES ---
st.markdown("""
    <style>
    /* Background με Blur & Σκοτάδι */
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.8)), 
        url("https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=2036&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* Εξαφάνιση του Toolbar πάνω από τον πίνακα (αυτό που κύκλωσες) */
    [data-testid="stElementToolbar"] {
        display: none !important;
    }

    /* Διόρθωση Selectbox */
    div[data-baseweb="select"] > div {
        background-color: white !important;
        color: black !important;
    }
    
    /* Καθαρά Λευκά Γράμματα παντού */
    h1, h2, h3, h4, p, span, label {
        color: white !important;
        text-shadow: none !important;
    }

    /* Στυλ για τα Expanders */
    .streamlit-expanderHeader {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        color: white !important;
    }
    
    /* Metrics Styling */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
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
        return f'<span style="color: #00ff88; font-weight: bold;">{perc}%</span>'
    return f'<span style="color: white;">{perc}%</span>'

# --- SIDEBAR ---
st.sidebar.markdown("# ⚽ Predictor Menu")
sel_league_name = st.sidebar.selectbox("Επιλογή Πρωταθλήματος:", list(LEAGUES.values()))
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

st.sidebar.markdown(f"### 🏆 {sel_league_name} Standings")
st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_dict = {}

if st_data and 'standings' in st_data:
    st_table = st_data['standings'][0]['table']
    for t in st_table:
        standings_dict[t['team']['name']] = {
            'gf': t['goalsFor'] / t['playedGames'] if t['playedGames'] > 0 else 1.2,
            'ga': t['goalsAgainst'] / t['playedGames'] if t['playedGames'] > 0 else 1.2
        }
    df_sidebar = [{"#": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table]
    # Χρήση dataframe με ρυθμίσεις για να μην φαίνεται το toolbar
    st.sidebar.dataframe(pd.DataFrame(df_sidebar), hide_index=True, use_container_width=True)

# --- MAIN ---
st.title(f"⚽ {sel_league_name} Analysis")

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = all_data.get('matches', [])
display_m = [m for m in all_m if m['status'] in ['IN_PLAY', 'PAUSED', 'SCHEDULED', 'TIMED']][:15]

for m in display_m:
    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    status = m['status']
    score = m.get('score', {}).get('fullTime', {})
    cur_h, cur_a = (score.get('home') or 0), (score.get('away') or 0)
    
    h_stats = standings_dict.get(h_t, {'gf': 1.2, 'ga': 1.2})
    a_stats = standings_dict.get(a_t, {'gf': 1.2, 'ga': 1.2})
    h_l, a_l = (h_stats['gf'] + a_stats['ga'])/2, (a_stats['gf'] + h_stats['ga'])/2
    
    # Poisson
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 6)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(6)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po15 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(2)])
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])

    date_str = m['utcDate'][:10]
    time_str = m['utcDate'][11:16]
    
    # Τίτλος Expander
    if status in ['IN_PLAY', 'PAUSED']:
        title = f"🔴 LIVE {cur_h}-{cur_a} | {h_t} vs {a_t}"
    else:
        title = f"🗓️ {date_str} {time_str} | {h_t} vs {a_t}"

    # Επαναφορά του Expander (Click to open)
    with st.expander(title):
        cols = st.columns(6)
        lbls = ["1", "X", "2", "GG", "O1.5", "O2.5"]
        vals = [p1, px, p2, pgg, po15, po25]
        
        for i in range(6):
            with cols[i]:
                st.markdown(f"""<div style="text-align: center;">
                    <div style="color: #aaa; font-size: 14px; margin-bottom: 5px;">{lbls[i]}</div>
                    {get_colored_val(vals[i])}
                </div>""", unsafe_allow_html=True)
