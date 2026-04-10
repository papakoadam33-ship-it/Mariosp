import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# 1. Βασική Ρύθμιση
st.set_page_config(page_title="Pro Predictor v16.42", layout="wide")

# 2. CSS - ΕΔΩ ΕΙΝΑΙ ΟΛΗ Η "ΜΑΓΕΙΑ" ΓΙΑ ΤΑ ΧΡΩΜΑΤΑ
st.markdown("""
    <style>
    /* Φόντο Γήπεδο */
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), 
        url("https://images.unsplash.com/photo-1504450758481-7338eba7524a?q=80&w=2069&auto=format&fit=crop");
        background-size: cover;
    }

    /* Sidebar Σκούρο */
    [data-testid="stSidebar"] {
        background-color: #1a1a1a !important;
    }

    /* Ο Πίνακας να γίνει ΓΚΡΙ */
    [data-testid="stDataFrame"] div {
        background-color: #2b2b2b !important;
        color: white !important;
    }

    /* ΕΠΙΒΟΛΗ ΛΕΥΚΩΝ ΓΡΑΜΜΑΤΩΝ ΣΤΟΥΣ ΑΓΩΝΕΣ - ΤΕΡΜΑ ΤΑ ΨΕΜΑΤΑ */
    .streamlit-expanderHeader * {
        color: white !important;
        -webkit-text-fill-color: white !important;
        font-weight: 800 !important;
    }
    
    /* Background του Expanders */
    .streamlit-expanderHeader {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }

    /* Διαχωριστική Γραμμή */
    .matchday-line {
        border-top: 3px solid #00ff88;
        margin: 30px 0px 10px 0px;
        opacity: 0.8;
    }
    </style>
    """, unsafe_allow_html=True)

API_KEY = "a963742bcd5642afbe8c842d057f25ad" 
LEAGUES = {'PL':'Premier League', 'PD':'La Liga', 'BL1':'Bundesliga', 'SA':'Serie A', 'FL1':'Ligue 1', 'DED':'Eredivisie'}

@st.cache_data(ttl=60)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    res = requests.get(url, headers=headers)
    return res.json() if res.status_code == 200 else {}

def get_colored_val(val):
    perc = round(val * 100)
    # ΕΔΩ ΤΟ ΠΡΑΣΙΝΟ ΧΡΩΜΑ
    if perc >= 70:
        return f'<span style="color: #00ff88; font-weight: 900; font-size: 22px;">{perc}%</span>'
    return f'<span style="color: white; font-weight: bold; font-size: 18px;">{perc}%</span>'

# --- SIDEBAR ---
st.sidebar.title("⚽ MENU")
sel_league_name = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# Φόρτωση Βαθμολογίας
st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_dict = {}
num_teams = 20

if st_data and 'standings' in st_data:
    table_data = st_data['standings'][0]['table']
    num_teams = len(table_data)
    for t in table_data:
        standings_dict[t['team']['name']] = {
            'gf': t['goalsFor']/t['playedGames'] if t['playedGames']>0 else 1.2, 
            'ga': t['goalsAgainst']/t['playedGames'] if t['playedGames']>0 else 1.2
        }
    
    # Ο ΤΙΤΛΟΣ ΠΟΥ ΗΘΕΛΕΣ ΣΤΟ SIDEBAR
    st.sidebar.subheader(f"🏆 {sel_league_name} Table")
    df = pd.DataFrame([{"#": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in table_data])
    st.sidebar.table(df) # Χρησιμοποιούμε table για πιο σταθερό γκρι στυλ

# --- ΚΥΡΙΩΣ ΣΕΛΙΔΑ ---
st.markdown(f'<h1 style="text-align:center; color:white;">{sel_league_name}</h1>', unsafe_allow_html=True)

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
matches = [m for m in all_data.get('matches', []) if m['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY', 'PAUSED']][:20]

m_per_round = num_teams // 2

for i, m in enumerate(matches):
    # Γραμμή Αγωνιστικής
    if i > 0 and i % m_per_round == 0:
        st.markdown('<div class="matchday-line"></div><p style="color:#00ff88; text-align:center;">ΕΠΟΜΕΝΗ ΑΓΩΝΙΣΤΙΚΗ</p>', unsafe_allow_html=True)

    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    
    # Poisson
    h_l = (standings_dict.get(h_t, {'gf':1.2})['gf'] + standings_dict.get(a_t, {'ga':1.2})['ga'])/2
    a_l = (standings_dict.get(a_t, {'gf':1.2})['gf'] + standings_dict.get(h_t, {'ga':1.2})['ga'])/2
    
    p1 = sum([poisson.pmf(k, h_l) * sum([poisson.pmf(j, a_l) for j in range(k)]) for k in range(1, 7)])
    px = sum([poisson.pmf(k, h_l) * poisson.pmf(k, a_l) for k in range(7)])
    p2 = max(0, 1 - p1 - px)

    # Τίτλος
    t_str = f"{m['utcDate'][11:16]} | {h_t} vs {a_t}"
    if m['status'] in ['IN_PLAY', 'PAUSED']:
        score = m.get('score', {}).get('fullTime', {})
        t_str = f"🔴 {score.get('home')}-{score.get('away')} | {h_t} vs {a_t}"

    with st.expander(t_str):
        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<div style="text-align:center;">1<br>{get_colored_val(p1)}</div>', unsafe_allow_html=True)
        c2.markdown(f'<div style="text-align:center;">X<br>{get_colored_val(px)}</div>', unsafe_allow_html=True)
        c3.markdown(f'<div style="text-align:center;">2<br>{get_colored_val(p2)}</div>', unsafe_allow_html=True)
