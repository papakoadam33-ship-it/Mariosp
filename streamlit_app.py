import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# Ρύθμιση σελίδας
st.set_page_config(page_title="Pro Predictor v16.37", layout="wide")

# --- CSS UPDATED ---
st.markdown("""
    <style>
    /* 1. Φόντο */
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), 
        url("https://images.unsplash.com/photo-1504450758481-7338eba7524a?q=80&w=2069&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* 2. Sidebar: Ανθρακί Χρώμα */
    [data-testid="stSidebar"] {
        background-color: #2b2b2b !important;
    }
    
    /* Dropdown text fix */
    div[data-baseweb="select"] * {
        color: #000000 !important;
    }

    /* 3. Τίτλος Βαθμολογίας & Γενικό Λευκό */
    .sidebar-white-text {
        color: #ffffff !important;
        font-weight: bold;
        margin-bottom: 10px;
    }
    h1, h2, h3, [data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
    }

    /* 4. Διαχωριστική Γραμμή Αγωνιστικής (Back by demand) */
    .matchday-divider {
        border: 0;
        height: 3px;
        background: linear-gradient(to right, transparent, #00ff88, #ffffff, #00ff88, transparent);
        margin: 40px 0 20px 0;
    }

    /* 5. Πιο Διάφανα Κουτάκια */
    .prediction-box {
        background: rgba(255, 255, 255, 0.08) !important; 
        padding: 12px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(3px);
    }
    
    /* Απόκρυψη Toolbar Πίνακα */
    [data-testid="stElementToolbar"] {
        display: none !important;
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

# --- SIDEBAR ---
st.sidebar.markdown('<p class="sidebar-white-text" style="font-size:25px;">⚙️ Ρυθμίσεις</p>', unsafe_allow_html=True)
league_names = list(LEAGUES.values())
sel_league_name = st.sidebar.selectbox("Επιλέξτε Πρωτάθλημα:", league_names)
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

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
    
    df = pd.DataFrame([{"#": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table])
    st.sidebar.markdown("---")
    st.sidebar.markdown('<p class="sidebar-white-text">📊 Βαθμολογία</p>', unsafe_allow_html=True)
    st.sidebar.dataframe(df, hide_index=True, use_container_width=True)

matches_per_round = num_teams // 2

# --- MAIN ---
st.markdown(f'<h1 style="text-align:center;">⚽ {sel_league_name} Analysis</h1>', unsafe_allow_html=True)

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
display_m = [m for m in all_data.get('matches', []) if m['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY']][:30]

for i, m in enumerate(display_m):
    # Εμφάνιση γραμμής ανά αγωνιστική
    if i > 0 and i % matches_per_round == 0:
        st.markdown('<div class="matchday-divider"></div>', unsafe_allow_html=True)

    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    h_stats = standings_dict.get(h_t, {'gf':1.2, 'ga':1.2})
    a_stats = standings_dict.get(a_t, {'gf':1.2, 'ga':1.2})
    
    h_l, a_l = (h_stats['gf'] + a_stats['ga'])/2, (a_stats['gf'] + h_stats['ga'])/2
    
    p1 = sum([poisson.pmf(k, h_l) * sum([poisson.pmf(j, a_l) for j in range(k)]) for k in range(1, 6)])
    px = sum([poisson.pmf(k, h_l) * poisson.pmf(k, a_l) for k in range(6)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1-poisson.pmf(0, h_l))*(1-poisson.pmf(0, a_l))
    po15 = 1-sum([poisson.pmf(k, h_l+a_l) for k in range(2)])
    po25 = 1-sum([poisson.pmf(k, h_l+a_l) for k in range(3)])

    title = f"📅 {m['utcDate'][:10]} | {m['homeTeam']['shortName']} vs {m['awayTeam']['shortName']}"
    
    with st.expander(title):
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        res_list = [
            ("1", p1), ("X", px), ("2", p2), 
            ("GG", pgg), ("O1.5", po15), ("O2.5", po25)
        ]
        
        for idx, (lbl, val) in enumerate(res_list):
            cols = [c1, c2, c3, c4, c5, c6]
            val_perc = round(val * 100)
            color = "#00ff88" if val_perc > 65 else "#ffffff"
            
            cols[idx].markdown(f"""
                <div class="prediction-box">
                    <small style="color: #bbb;">{lbl}</small><br>
                    <span style="color: {color}; font-size: 18px; font-weight: bold;">{val_perc}%</span>
                </div>
            """, unsafe_allow_html=True)
