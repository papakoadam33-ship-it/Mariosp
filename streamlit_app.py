import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# Ρύθμιση σελίδας
st.set_page_config(page_title="Pro Football Predictor", layout="wide")

# --- CSS ΓΙΑ FULL DESIGN & SIDEBAR FIX ---
st.markdown("""
    <style>
    /* Background κεντρικής οθόνης */
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.8)), 
        url("https://images.unsplash.com/photo-1508098682722-e99c43a406b2?ixlib=rb-1.2.1&auto=format&fit=crop&w=1950&q=80");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* Διόρθωση Sidebar (Μενού αριστερά) */
    [data-testid="stSidebar"] {
        background-color: #1a1a1a !important;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* Στυλ για τις κάρτες των αγώνων (Glassmorphism) */
    .match-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 15px;
        color: white;
    }
    
    /* metrics text color */
    [data-testid="stMetricValue"] {
        color: #00ffcc !important;
        font-weight: bold;
    }
    
    h1, h2, h3 {
        color: white !important;
        text-shadow: 2px 2px 4px #000000;
    }
    
    .stExpander {
        border: none !important;
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 15px !important;
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

def calc_all(h_l, a_l, cur_h=0, cur_a=0, is_live=False):
    # Poisson calculation
    h_l, a_l = max(0.5, h_l), max(0.5, a_l)
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po15 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(2)])
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])
    return p1, px, p2, pgg, po15, po25

# --- SIDEBAR (ΠΙΝΑΚΑΣ) ---
st.sidebar.title("📍 Ρυθμίσεις")
sel_league_name = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
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
    # Εμφάνιση πίνακα στο sidebar
    df_sidebar = [{"Pos": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table]
    st.sidebar.table(pd.DataFrame(df_sidebar).set_index('Pos'))

# --- MAIN ---
st.title(f"⚽ {sel_league_name} Pro Analysis")

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = all_data.get('matches', [])
display_m = [m for m in all_m if m['status'] in ['IN_PLAY', 'PAUSED', 'SCHEDULED', 'TIMED']][:20]

for m in display_m:
    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    status = m['status']
    score = m.get('score', {}).get('fullTime', {})
    cur_h = score.get('home') if score.get('home') is not None else 0
    cur_a = score.get('away') if score.get('away') is not None else 0
    total_cur = cur_h + cur_a
    
    # Stats logic
    h_stats = standings_dict.get(h_t, {'gf': 1.2, 'ga': 1.2})
    a_stats = standings_dict.get(a_t, {'gf': 1.2, 'ga': 1.2})
    h_l = (h_stats['gf'] + a_stats['ga']) / 2
    a_l = (a_stats['gf'] + h_stats['ga']) / 2
    
    p1, px, p2, pgg, po15, po25 = calc_all(h_l, a_l)
    
    # Τίτλος με Ημερομηνία
    date_val = m['utcDate'][:10]
    time_val = m['utcDate'][11:16]
    
    if status in ['IN_PLAY', 'PAUSED']:
        title = f"🔴 LIVE {cur_h}-{cur_a} | {h_t} vs {a_t}"
    else:
        title = f"🗓️ {date_val} {time_val} | {h_t} vs {a_t}"

    with st.expander(title):
        cols = st.columns(6)
        lbls = ["1", "X", "2", "GG", "O1.5", "O2.5"]
        vals = [p1, px, p2, pgg, po15, po25]
        
        for i in range(6):
            if i == 4 and total_cur >= 2: cols[i].success("✅ O1.5")
            elif i == 5 and total_cur >= 3: cols[i].success("✅ O2.5")
            else: cols[i].metric(lbls[i], f"{round(vals[i]*100)}%")


