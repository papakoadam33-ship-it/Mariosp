import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# Ρύθμιση σελίδας
st.set_page_config(page_title="Cyber Football Predictor", layout="wide")

# --- CSS ΓΙΑ ΤΟ CYBERPUNK THEME & FIXES ---
st.markdown("""
    <style>
    /* Background κεντρικής οθόνης - Cyberpunk Football Style */
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
        url("https://images.unsplash.com/photo-1551952237-954a0e68786c?q=80&w=2070&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* Διόρθωση Sidebar & Πίνακα */
    [data-testid="stSidebar"] {
        background-color: #0d0d0d !important;
        border-right: 1px solid #333;
    }
    
    /* Διόρθωση Selectbox (Για να φαίνεται το κείμενο) */
    div[data-baseweb="select"] > div {
        background-color: white !important;
        color: black !important;
    }
    div[data-testid="stSelectbox"] label {
        color: white !important;
        font-weight: bold;
    }

    /* Στυλ για τον πίνακα Standings */
    .styled-table {
        background-color: white;
        color: black;
        border-radius: 5px;
    }

    /* Custom Metric Styling */
    .metric-box {
        text-align: center;
        padding: 10px;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .high-prob { color: #00ff88; font-weight: bold; font-size: 1.2em; }
    .normal-prob { color: #ffffff; }
    
    h1, h2, h3 { color: #00f2ff !important; text-shadow: 0 0 10px #00f2ff; }
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

# Συνάρτηση για το χρώμα των ποσοστών
def get_colored_val(val):
    perc = round(val * 100)
    if perc >= 70:
        return f'<span style="color: #00ff88; font-weight: bold; font-size: 20px;">{perc}%</span>'
    return f'<span style="color: white; font-size: 18px;">{perc}%</span>'

# --- SIDEBAR ---
st.sidebar.title("🤖 Predictor Menu")
sel_league_name = st.sidebar.selectbox("Επιλογή Πρωταθλήματος:", list(LEAGUES.values()))
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

st.sidebar.markdown(f"### 🏆 {sel_league_name}")
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
    # Εμφάνιση πίνακα με λευκό στυλ
    st.sidebar.dataframe(pd.DataFrame(df_sidebar), hide_index=True, use_container_width=True)

# --- MAIN ---
st.title(f"⚡ {sel_league_name} Analysis")

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = all_data.get('matches', [])
display_m = [m for m in all_m if m['status'] in ['IN_PLAY', 'PAUSED', 'SCHEDULED', 'TIMED']][:15]

for m in display_m:
    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    status = m['status']
    score = m.get('score', {}).get('fullTime', {})
    cur_h, cur_a = (score.get('home') or 0), (score.get('away') or 0)
    
    # Poisson Logic
    h_stats = standings_dict.get(h_t, {'gf': 1.2, 'ga': 1.2})
    a_stats = standings_dict.get(a_t, {'gf': 1.2, 'ga': 1.2})
    h_l, a_l = (h_stats['gf'] + a_stats['ga'])/2, (a_stats['gf'] + h_stats['ga'])/2
    
    # Προσεγγιστικά ποσοστά (Poisson)
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 6)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(6)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po15 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(2)])
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])

    date_str = m['utcDate'][:10]
    time_str = m['utcDate'][11:16]
    title = f"🗓️ {date_str} {time_str} | {h_t} vs {a_t}"
    if status in ['IN_PLAY', 'PAUSED']:
        title = f"🔴 LIVE {cur_h}-{cur_a} | {h_t} vs {a_t}"

    with st.container():
        st.markdown(f"""<div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 15px; border-left: 5px solid #00f2ff; margin-bottom: 10px;">
            <h4 style="margin:0;">{title}</h4>
        </div>""", unsafe_allow_html=True)
        
        cols = st.columns(6)
        lbls = ["1", "X", "2", "GG", "O1.5", "O2.5"]
        vals = [p1, px, p2, pgg, po15, po25]
        
        for i in range(6):
            with cols[i]:
                st.markdown(f"""<div style="text-align: center; background: rgba(0,0,0,0.3); padding: 5px; border-radius: 8px;">
                    <div style="color: #00f2ff; font-size: 12px;">{lbls[i]}</div>
                    {get_colored_val(vals[i])}
                </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
