import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# 1. Ρύθμιση σελίδας
st.set_page_config(page_title="Pro Predictor v16.43", layout="wide")

# 2. CSS - ΕΔΩ ΔΙΟΡΘΩΝΟΥΜΕ ΤΟΝ ΠΙΝΑΚΑ ΚΑΙ ΤΟ SIDEBAR
st.markdown("""
    <style>
    /* Φόντο v16.27 */
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), 
        url("https://images.unsplash.com/photo-1504450758481-7338eba7524a?q=80&w=2069&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* Sidebar: ΣΚΟΥΡΟ ΓΚΡΙ */
    [data-testid="stSidebar"] {
        background-color: #1a1a1a !important;
    }
    
    /* ΟΜΑΛΟΣ ΣΚΟΥΡΟΣ ΠΙΝΑΚΑΣ (Sidebar) */
    [data-testid="stDataFrame"] {
        background-color: #262626 !important;
        border-radius: 10px;
        padding: 5px;
    }

    /* Διαχωριστική Γραμμή Αγωνιστικής */
    .matchday-divider {
        border: 0;
        height: 2px;
        background: linear-gradient(to right, transparent, #00ff88, #ffffff, #00ff88, transparent);
        margin: 30px 0 10px 0;
    }
    .matchday-label {
        color: #00ff88;
        text-align: center;
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 20px;
    }

    /* ΕΠΙΒΟΛΗ ΓΙΑ ΛΕΥΚΑ ΓΡΑΜΜΑΤΑ ΣΤΟΥΣ EXPANDERS */
    .streamlit-expanderHeader {
        background-color: rgba(255, 255, 255, 0.05) !important;
    }
    .streamlit-expanderHeader p {
        color: white !important;
        font-weight: 800 !important;
    }
    </style>
    """, unsafe_allow_html=True)

API_KEY = "a963742bcd5642afbe8c842d057f25ad" 
LEAGUES = {'PL':'Premier League', 'PD':'La Liga', 'BL1':'Bundesliga', 'SA':'Serie A', 'FL1':'Ligue 1', 'CL':'Champions League', 'DED':'Eredivisie', 'ELC':'Championship'}

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
    color = "#00ff88" if perc >= 70 else "white"
    size = "22px" if perc >= 70 else "18px"
    return f'<span style="color: {color}; font-weight: bold; font-size: {size};">{perc}%</span>'

# --- SIDEBAR ---
st.sidebar.title("⚽ Predictor Menu")
sel_league_name = st.sidebar.selectbox("Επιλογή Πρωταθλήματος:", list(LEAGUES.values()))
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# ΤΙΤΛΟΣ ΠΟΥ ΦΑΙΝΕΤΑΙ ΠΟΙΟ ΠΡΩΤΑΘΛΗΜΑ ΕΧΕΙΣ ΕΠΙΛΕΞΕΙ
st.sidebar.markdown(f"## 🏆 {sel_league_name}")

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
    
    st.sidebar.markdown("### Standings")
    df_standings = pd.DataFrame([{"#": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table])
    st.sidebar.dataframe(df_standings, hide_index=True, use_container_width=True)

matches_per_round = num_teams // 2

# --- MAIN PAGE ---
st.markdown(f'<h1 style="text-align:center; color:white;">⚽ {sel_league_name} Analysis</h1>', unsafe_allow_html=True)

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
display_m = [m for m in all_data.get('matches', []) if m['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY']][:30]

for i, m in enumerate(display_m):
    if i > 0 and i % matches_per_round == 0:
        st.markdown('<div class="matchday-divider"></div><div class="matchday-label">ΕΠΟΜΕΝΗ ΑΓΩΝΙΣΤΙΚΗ</div>', unsafe_allow_html=True)

    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    h_stats = standings_dict.get(h_t, {'gf':1.2, 'ga':1.2})
    a_stats = standings_dict.get(a_t, {'gf':1.2, 'ga':1.2})
    h_l, a_l = (h_stats['gf'] + a_stats['ga'])/2, (a_stats['gf'] + h_stats['ga'])/2
    
    p1 = sum([poisson.pmf(k, h_l) * sum([poisson.pmf(j, a_l) for j in range(k)]) for k in range(1, 6)])
    px = sum([poisson.pmf(k, h_l) * poisson.pmf(k, a_l) for k in range(6)])
    p2 = max(0, 1 - p1 - px)
    pgg, po15, po25 = (1-poisson.pmf(0, h_l))*(1-poisson.pmf(0, a_l)), 1-sum([poisson.pmf(k, h_l+a_l) for k in range(2)]), 1-sum([poisson.pmf(k, h_l+a_l) for k in range(3)])

    # ΛΥΣΗ ΓΙΑ ΛΕΥΚΑ ΓΡΑΜΜΑΤΑ: HTML ΜΕΣΑ ΣΤΟ TITLE
    title_html = f"{m['utcDate'][11:16]} | {h_t} vs {a_t}"
    
    with st.expander(title_html):
        cols = st.columns(6)
        lbls, vals = ["1", "X", "2", "GG", "O1.5", "O2.5"], [p1, px, p2, pgg, po15, po25]
        for idx in range(6):
            cols[idx].markdown(f"""
                <div style="text-align:center; background:rgba(0,0,0,0.6); padding:10px; border-radius:10px;">
                    <div style="color:#aaa; font-size:12px; margin-bottom:5px;">{lbls[idx]}</div>
                    {get_colored_val(vals[idx])}
                </div>
            """, unsafe_allow_html=True)
