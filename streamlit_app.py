import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# Ρύθμιση σελίδας
st.set_page_config(page_title="Pro Predictor v16.37", layout="wide")

# --- CSS ΓΙΑ ΤΟ ΤΕΛΙΚΟ DESIGN ---
st.markdown("""
    <style>
    /* Φόντο */
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), 
        url("https://images.unsplash.com/photo-1504450758481-7338eba7524a?q=80&w=2069&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* Sidebar: Σκούρο Slate */
    [data-testid="stSidebar"] {
        background-color: #121212 !important;
    }
    
    /* Επιβολή Λευκού Χρώματος σε όλα τα κείμενα */
    h1, h2, h3, p, span, div, label {
        color: #ffffff !important;
    }

    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border-radius: 5px;
    }

    /* Matchday Divider */
    .matchday-divider {
        border: 0;
        height: 2px;
        background: linear-gradient(to right, transparent, #00ff88, transparent);
        margin: 30px 0;
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

# --- SIDEBAR & LOGIC ---
st.sidebar.markdown("### ⚙️ Ρυθμίσεις")

# Διόρθωση: Χρήση session_state για να φαίνεται η επιλογή
if 'league_idx' not in st.session_state:
    st.session_state.league_idx = 0

league_names = list(LEAGUES.values())
sel_league_name = st.sidebar.selectbox(
    "Επιλέξτε Πρωτάθλημα:", 
    league_names, 
    index=st.session_state.league_idx
)

# Ενημέρωση του index
st.session_state.league_idx = league_names.index(sel_league_name)
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
    
    # Πιο σκούρος πίνακας (Dataframe)
    df = pd.DataFrame([{"#": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table])
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Βαθμολογία")
    st.sidebar.dataframe(df.style.set_properties(**{
        'background-color': '#1e1e1e',
        'color': 'white',
        'border-color': '#333333'
    }), hide_index=True, use_container_width=True)

matches_per_round = num_teams // 2

# --- MAIN SCREEN ---
st.markdown(f'<h1 style="text-align:center;">⚽ {sel_league_name} Analysis</h1>', unsafe_allow_html=True)

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
display_m = [m for m in all_data.get('matches', []) if m['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY']][:30]

if not display_m:
    st.info("Δεν βρέθηκαν προγραμματισμένοι αγώνες.")

for i, m in enumerate(display_m):
    if i > 0 and i % matches_per_round == 0:
        st.markdown('<div class="matchday-divider"></div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#00ff88; font-weight:bold;">ΕΠΟΜΕΝΗ ΑΓΩΝΙΣΤΙΚΗ</p>', unsafe_allow_html=True)

    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    h_stats = standings_dict.get(h_t, {'gf':1.2, 'ga':1.2})
    a_stats = standings_dict.get(a_t, {'gf':1.2, 'ga':1.2})
    
    # Poisson Math
    h_l, a_l = (h_stats['gf'] + a_stats['ga'])/2, (a_stats['gf'] + h_stats['ga'])/2
    p1 = sum([poisson.pmf(k, h_l) * sum([poisson.pmf(j, a_l) for j in range(k)]) for k in range(1, 6)])
    px = sum([poisson.pmf(k, h_l) * poisson.pmf(k, a_l) for k in range(6)])
    p2 = max(0, 1 - p1 - px)
    
    pgg = (1-poisson.pmf(0, h_l))*(1-poisson.pmf(0, a_l))
    po25 = 1-sum([poisson.pmf(k, h_l+a_l) for k in range(3)])

    title = f"📅 {m['utcDate'][:10]} | {m['homeTeam']['shortName']} vs {m['awayTeam']['shortName']}"
    
    with st.expander(title):
        col1, col2, col3, col4, col5 = st.columns(5)
        stats = {
            "1": f"{round(p1*100)}%",
            "X": f"{round(px*100)}%",
            "2": f"{round(p2*100)}%",
            "GG": f"{round(pgg*100)}%",
            "O2.5": f"{round(po25*100)}%"
        }
        
        for idx, (lbl, val) in enumerate(stats.items()):
            cols = [col1, col2, col3, col4, col5]
            color = "#00ff88" if int(val[:-1]) > 65 else "#ffffff"
            cols[idx].markdown(f"""
                <div style="background: rgba(0,0,0,0.4); padding:10px; border-radius:10px; text-align:center; border: 1px solid #333;">
                    <small style="color: #aaa;">{lbl}</small><br>
                    <span style="color: {color}; font-size: 20px; font-weight: bold;">{val}</span>
                </div>
            """, unsafe_allow_html=True)
  
        
        
