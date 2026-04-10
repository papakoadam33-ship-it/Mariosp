import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# 1. Βασική Ρύθμιση Σελίδας
st.set_page_config(page_title="Pro Predictor v16.44", layout="wide")

# 2. CSS - ΕΔΩ ΓΙΝΟΝΤΑΙ ΟΛΕΣ ΟΙ ΟΠΤΙΚΕΣ ΑΛΛΑΓΕΣ
st.markdown("""
    <style>
    /* Φόντο Γήπεδο (v16.27) */
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), 
        url("https://images.unsplash.com/photo-1504450758481-7338eba7524a?q=80&w=2069&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* === SIDEBAR (ΜΕΝΟΥ) === */
    [data-testid="stSidebar"] {
        background-color: #1a1a1a !important;
    }
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    
    /* ΕΞΑΦΑΝΙΣΗ ΕΡΓΑΛΕΙΟΘΗΚΗΣ ΠΙΝΑΚΑ (Αυτό που κύκλωσες) */
    button[title="View fullscreen"], 
    button[title="Download as CSV"], 
    button[title="Search"], 
    button[title="Type to search"] {
        display: none !important;
    }
    
    /* Smooth Gray Table */
    .stDataFrame, [data-testid="stTable"] {
        background-color: rgba(45, 45, 45, 0.8) !important;
        border-radius: 10px !important;
    }

    /* === ΑΡΧΙΚΗ ΣΕΛΙΔΑ === */
    /* ΕΠΙΒΟΛΗ ΛΕΥΚΩΝ ΓΡΑΜΜΑΤΩΝ ΣΤΟΥΣ ΤΙΤΛΟΥΣ (image_0.png fix) */
    .streamlit-expanderHeader * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important; 
        font-weight: 800 !important;
        font-size: 1.2rem !important;
        text-shadow: 2px 2px 4px #000000 !important;
    }
    
    /* FIX ΓΙΑ ΤΟ ΑΣΠΡΙΣΜΑ ΣΤΟ ΚΛΙΚ (image_1.png fix) */
    /* Κλειδώνουμε το φόντο σε σκούρο, ακόμα και όταν είναι ανοιχτό [aria-expanded="true"] */
    .streamlit-expanderHeader, 
    .streamlit-expanderHeader[aria-expanded="true"], 
    .streamlit-expanderHeader:hover {
        background-color: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
    }

    /* ΝΕΟ ΠΛΑΙΣΙΟ ΠΟΣΟΣΤΩΝ: ΔΙΑΦΑΝΟ/ΛΕΥΚΟ (image_6.png design) */
    .prob-box {
        text-align: center; 
        background-color: rgba(255, 255, 255, 0.15) !important; /* Απαλό διαφανές λευκό */
        padding: 12px; 
        border-radius: 12px; 
        border: 1px solid rgba(255, 255, 255, 0.3); /* Λεπτό λευκό περίγραμμα */
        margin-bottom: 5px;
    }

    /* Διαχωριστική Γραμμή Αγωνιστικής */
    .matchday-divider {
        border: 0;
        height: 2px;
        background: linear-gradient(to right, transparent, #00ff88, #ffffff, #00ff88, transparent);
        margin: 40px 0 20px 0;
    }
    
    /* Hide Default Toolbars */
    [data-testid="stElementToolbar"] {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

API_KEY = "a963742bcd5642afbe8c842d057f25ad" 
LEAGUES = {'PL':'Premier League', 'PD':'La Liga', 'BL1':'Bundesliga', 'SA':'Serie A', 'FL1':'Ligue 1', 'DED':'Eredivisie'}

@st.cache_data(ttl=60)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except: return {}

def get_colored_val(val):
    perc = round(val * 100)
    # Πράσινο στα 70%+
    if perc >= 70:
        return f'<span style="color: #00ff88; font-weight: 900; font-size: 22px; text-shadow: 0px 0px 8px #00ff88;">{perc}%</span>'
    return f'<span style="color: white; font-weight: bold; font-size: 18px;">{perc}%</span>'

# --- SIDEBAR (ΜΕΝΟΥ) ---
st.sidebar.markdown("### ⚙️ Ρυθμίσεις")
sel_league_name = st.sidebar.selectbox("Επιλογή Πρωταθλήματος:", list(LEAGUES.values()))
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_dict = {}
num_teams = 20

if st_data and 'standings' in st_data:
    st_table = st_data['standings'][0]['table']
    num_teams = len(st_table)
    for t in st_table:
        standings_dict[t['team']['name']] = {'gf': t['goalsFor']/t['playedGames'] if t['playedGames']>0 else 1.2, 'ga': t['goalsAgainst']/t['playedGames'] if t['playedGames']>0 else 1.2}
    
    # ΑΦΑΙΡΕΘΗΚΕ Ο ΤΙΤΛΟΣ ΠΟΥ ΖΗΤΗΣΕΣ
    st.sidebar.markdown(f"### 📊 Standings")
    df_sidebar = pd.DataFrame([{"#": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table])
    st.sidebar.dataframe(df_sidebar, hide_index=True, use_container_width=True)

matches_per_round = num_teams // 2

# --- MAIN PAGE ---
st.markdown(f'<h1 style="text-align:center; color:white; text-shadow: 2px 2px 10px black;">⚽ {sel_league_name} Analysis</h1>', unsafe_allow_html=True)

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
display_m = [m for m in all_data.get('matches', []) if m['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY', 'PAUSED']][:20]

for i, m in enumerate(display_m):
    # Διαχωρισμός ανά αγωνιστική
    if i > 0 and i % matches_per_round == 0:
        st.markdown('<div class="matchday-divider"></div>', unsafe_allow_html=True)

    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    status = m['status']
    score = m.get('score', {}).get('fullTime', {})
    cur_h, cur_a = (score.get('home') or 0), (score.get('away') or 0)
    
    # Stats για Poisson
    h_l = (standings_dict.get(h_t, {'gf':1.2})['gf'] + standings_dict.get(a_t, {'ga':1.2})['ga'])/2
    a_l = (standings_dict.get(a_t, {'gf':1.2})['gf'] + standings_dict.get(h_t, {'ga':1.2})['ga'])/2
    
    p1 = sum([poisson.pmf(k, h_l) * sum([poisson.pmf(j, a_l) for j in range(k)]) for k in range(1, 7)])
    px = sum([poisson.pmf(k, h_l) * poisson.pmf(k, a_l) for k in range(7)])
    p2 = max(0, 1 - p1 - px)
    
    live_info = f"🔴 {cur_h}-{cur_a}" if status in ['IN_PLAY', 'PAUSED'] else f"📅 {m['utcDate'][11:16]}"
    title = f"{live_info} | {h_t} vs {a_t}"
    
    # Τα γράμματα εδώ είναι πλέον Force White από το CSS
    with st.expander(title):
        cols = st.columns(3)
        lbls, vals = ["1", "X", "2"], [p1, px, p2]
        for idx in range(3):
            # ΕΦΑΡΜΟΓΗ ΤΟΥprob-box (image_6.png design)
            cols[idx].markdown(f"""
                <div class="prob-box">
                    <div style="color:#eee; font-size:12px; margin-bottom:5px;">{lbls[idx]}</div>
                    {get_colored_val(vals[idx])}
                </div>
            """, unsafe_allow_html=True)
