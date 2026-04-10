import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# Ρύθμιση σελίδας
st.set_page_config(page_title="Pro Predictor v16.39 LIVE", layout="wide")

# --- CSS ΓΙΑ ΤΟ DESIGN ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), 
        url("https://images.unsplash.com/photo-1504450758481-7338eba7524a?q=80&w=2069&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    [data-testid="stSidebar"] { background-color: #1e1e1e !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .streamlit-expanderHeader {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
    }
    .streamlit-expanderHeader p {
        color: #ffffff !important;
        font-weight: 800 !important;
        text-shadow: 2px 2px 4px #000000 !important;
    }
    .matchday-divider {
        border: 0; height: 3px;
        background: linear-gradient(to right, transparent, #00ff88, #ffffff, #00ff88, transparent);
        margin: 40px 0 20px 0;
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
    if perc >= 70:
        return f'<span style="color: #00ff88; font-weight: 900; font-size: 24px; text-shadow: 0px 0px 10px #00ff88;">{perc}%</span>'
    return f'<span style="color: white; font-weight: bold; font-size: 20px;">{perc}%</span>'

# --- LIVE POISSON ENGINE ---
def calculate_live_probs(h_l, a_l, cur_h, cur_a, status):
    # Αν το ματς δεν έχει αρχίσει, δουλεύει κανονικά
    if status in ['SCHEDULED', 'TIMED']:
        p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 7)])
        px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(7)])
        p2 = max(0, 1 - p1 - px)
    else:
        # LIVE LOGIC: Υπολογίζουμε πιθανότητες για τα ΕΠΙΠΛΕΟΝ γκολ (χοντρικά για το υπόλοιπο του ματς)
        # Θεωρούμε ότι απομένει το 50% του χρόνου κατά μέσο όρο αν είναι Live
        rem_h_l, rem_a_l = h_l * 0.5, a_l * 0.5
        
        p1, px, p2 = 0, 0, 0
        for i in range(6): # Επιπλέον γκολ γηπεδούχου
            for j in range(6): # Επιπλέον γκολ φιλοξενούμενου
                prob = poisson.pmf(i, rem_h_l) * poisson.pmf(j, rem_a_l)
                final_h = cur_h + i
                final_a = cur_a + j
                if final_h > final_a: p1 += prob
                elif final_h == final_a: px += prob
                else: p2 += prob
                
    # Υπολογισμός Over/GG (απλοποιημένο για live)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po25 = 1 - sum([poisson.pmf(k, h_l + a_l) for k in range(3)])
    return p1, px, p2, pgg, po25

# --- SIDEBAR ---
sel_league_name = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]
st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_dict = {}
num_teams = 20

if st_data and 'standings' in st_data:
    st_table = st_data['standings'][0]['table']
    num_teams = len(st_table)
    for t in st_table:
        standings_dict[t['team']['name']] = {'gf': t['goalsFor']/t['playedGames'] if t['playedGames']>0 else 1.2, 'ga': t['goalsAgainst']/t['playedGames'] if t['playedGames']>0 else 1.2}
    st.sidebar.dataframe(pd.DataFrame([{"#": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table]), hide_index=True)

# --- MAIN ---
st.markdown(f'<h1 style="text-align:center; color:white;">⚽ {sel_league_name} Live Predictor</h1>', unsafe_allow_html=True)

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
display_m = [m for m in all_data.get('matches', []) if m['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY', 'PAUSED']][:20]

for i, m in enumerate(display_m):
    if i > 0 and i % (num_teams // 2) == 0:
        st.markdown('<div class="matchday-divider"></div>', unsafe_allow_html=True)

    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    status = m['status']
    score = m.get('score', {}).get('fullTime', {})
    cur_h, cur_a = (score.get('home') or 0), (score.get('away') or 0)
    
    h_stats = standings_dict.get(h_t, {'gf':1.2, 'ga':1.2})
    a_stats = standings_dict.get(a_t, {'gf':1.2, 'ga':1.2})
    h_l, a_l = (h_stats['gf'] + a_stats['ga'])/2, (a_stats['gf'] + h_stats['ga'])/2
    
    # Κλήση της Live Μηχανής
    p1, px, p2, pgg, po25 = calculate_live_probs(h_l, a_l, cur_h, cur_a, status)

    live_label = f"🔴 LIVE {cur_h}-{cur_a}" if status in ['IN_PLAY', 'PAUSED'] else f"📅 {m['utcDate'][11:16]}"
    title = f"{live_label} | {h_t} vs {a_t}"
    
    with st.expander(title):
        cols = st.columns(5)
        lbls, vals = ["1", "X", "2", "GG", "O2.5"], [p1, px, p2, pgg, po25]
        for idx in range(5):
            cols[idx].markdown(f"""
                <div style="text-align:center; background:rgba(0,0,0,0.6); padding:12px; border-radius:12px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="color:#aaa; font-size:13px; margin-bottom:5px;">{lbls[idx]}</div>
                    {get_colored_val(vals[idx])}
                </div>
            """, unsafe_allow_html=True)

