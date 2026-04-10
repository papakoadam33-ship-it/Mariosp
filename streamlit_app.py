import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# Ρύθμιση σελίδας
st.set_page_config(page_title="Pro Predictor v16.37", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), 
        url("https://images.unsplash.com/photo-1504450758481-7338eba7524a?q=80&w=2069&auto=format&fit=crop");
        background-size: cover; background-attachment: fixed;
    }
    [data-testid="stSidebar"] { background-color: #2b2b2b !important; }
    div[data-baseweb="select"] * { color: #000000 !important; }
    .sidebar-white-text { color: #ffffff !important; font-weight: bold; }
    h1, h2, h3, [data-testid="stMarkdownContainer"] p { color: #ffffff !important; }
    
    .matchday-divider {
        border: 0; height: 3px;
        background: linear-gradient(to right, transparent, #00ff88, #ffffff, #00ff88, transparent);
        margin: 40px 0 20px 0;
    }
    
    .prediction-box {
        background: rgba(255, 255, 255, 0.08) !important; 
        padding: 8px 5px; 
        border-radius: 8px; 
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.15); 
        backdrop-filter: blur(3px);
        margin-bottom: 5px;
    }

    [data-testid="stElementToolbar"] { display: none !important; }
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

# --- MAIN ---
st.markdown(f'<h1 style="text-align:center;">⚽ {sel_league_name} Analysis</h1>', unsafe_allow_html=True)

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
matches = all_data.get('matches', [])
display_m = [m for m in matches if m['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY', 'PAUSED']][:30]

for i, m in enumerate(display_m):
    if i > 0 and i % (num_teams // 2) == 0:
        st.markdown('<div class="matchday-divider"></div>', unsafe_allow_html=True)

    status = m['status']
    is_live = status in ['IN_PLAY', 'PAUSED']
    h_score = m['score']['fullTime']['home'] if m['score']['fullTime']['home'] is not None else 0
    a_score = m['score']['fullTime']['away'] if m['score']['fullTime']['away'] is not None else 0
    
    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    h_stats = standings_dict.get(h_t, {'gf':1.2, 'ga':1.2})
    a_stats = standings_dict.get(a_t, {'gf':1.2, 'ga':1.2})
    
    time_factor = 0.5 if is_live else 1.0
    h_l = ((h_stats['gf'] + a_stats['ga'])/2) * time_factor
    a_l = ((a_stats['gf'] + h_stats['ga'])/2) * time_factor
    
    # Poisson Math
    p1 = sum([poisson.pmf(k, h_l) * sum([poisson.pmf(j, a_l) for j in range(k + (h_score - a_score))]) for k in range(0, 6)])
    px = sum([poisson.pmf(k, h_l) * poisson.pmf(k + (h_score - a_score), a_l) for k in range(0, 6)])
    p2 = max(0, 1 - p1 - px)
    
    current_total = h_score + a_score
    po15_val = 1 - sum([poisson.pmf(k, h_l + a_l) for k in range(max(0, 2 - current_total))])
    po25_val = 1 - sum([poisson.pmf(k, h_l + a_l) for k in range(max(0, 3 - current_total))])
    pgg_val = (1-poisson.pmf(0, h_l + (1 if h_score > 0 else 0))) * (1-poisson.pmf(0, a_l + (1 if a_score > 0 else 0)))

    # Έλεγχος αν έχουν ήδη συμβεί (Checkmark Logic)
    is_gg = h_score > 0 and a_score > 0
    is_o15 = current_total > 1
    is_o25 = current_total > 2

    # Τίτλος: Live (emoji + score) ή Προγραμματισμένο (ημερομηνία)
    if is_live:
        title = f"🔴 LIVE {h_score}-{a_score} | {m['homeTeam']['shortName']} vs {m['awayTeam']['shortName']}"
    else:
        title = f"📅 {m['utcDate'][:10]} | {m['homeTeam']['shortName']} vs {m['awayTeam']['shortName']}"
    
    with st.expander(title):
        cols = st.columns(6)
        # Λίστα με (Label, Τιμή, Αν έχει συμβεί ήδη)
        res_list = [
            ("1", p1, False), ("X", px, False), ("2", p2, False), 
            ("GG", pgg_val, is_gg), ("O1.5", po15_val, is_o15), ("O2.5", po25_val, is_o25)
        ]
        
        for idx, (lbl, val, happened) in enumerate(res_list):
            val_perc = min(100, max(0, round(val * 100)))
            display_text = "✅" if happened else f"{val_perc}%"
            color = "#00ff88" if (happened or val_perc > 65) else "#ffffff"
            
            cols[idx].markdown(f"""
                <div class="prediction-box">
                    <small style="color: #bbb; font-size: 12px;">{lbl}</small><br>
                    <span style="color: {color}; font-size: 16px; font-weight: bold;">{display_text}</span>
                </div>
            """, unsafe_allow_html=True)
