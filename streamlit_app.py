import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# Ρύθμιση σελίδας
st.set_page_config(page_title="Pro Predictor v16.40", layout="wide")

# --- CSS ΓΙΑ ΤΟ ΤΕΛΙΚΟ DESIGN ---
st.markdown("""
    <style>
    /* 1. Φόντο v16.27 */
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), 
        url("https://images.unsplash.com/photo-1504450758481-7338eba7524a?q=80&w=2069&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* 2. Sidebar: Σκούρο Μενού & Πιο Γκρι Πίνακας */
    [data-testid="stSidebar"] {
        background-color: #1e1e1e !important;
    }
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    
    /* Κάνει τον πίνακα στο πλάι πιο γκρι/ημιδιαφανή */
    [data-testid="stTable"] {
        background-color: rgba(50, 50, 50, 0.5) !important;
        border-radius: 10px;
    }
    .stDataFrame {
        background-color: rgba(40, 40, 40, 0.7) !important;
    }

    /* 3. ΕΠΙΒΟΛΗ ΛΕΥΚΩΝ ΓΡΑΜΜΑΤΩΝ ΣΤΗΝ ΑΡΧΙΚΗ */
    /* Στοχεύουμε απευθείας το κείμενο μέσα στα expanders */
    .streamlit-expanderHeader p {
        color: white !important;
        -webkit-text-fill-color: white !important;
        font-weight: 800 !important;
        font-size: 1.15rem !important;
        text-shadow: 1px 1px 3px black !important;
    }

    /* 4. Fix για το άσπρισμα όταν πατάμε τον αγώνα */
    .streamlit-expanderHeader[aria-expanded="true"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
    }

    /* 5. Διαχωριστική Γραμμή Αγωνιστικής */
    .matchday-divider {
        border: 0;
        height: 2px;
        background: linear-gradient(to right, transparent, #00ff88, #ffffff, #00ff88, transparent);
        margin: 35px 0 15px 0;
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
        return f'<span style="color: #00ff88; font-weight: 900; font-size: 22px;">{perc}%</span>'
    return f'<span style="color: white; font-weight: bold; font-size: 18px;">{perc}%</span>'

# --- LIVE ENGINE ---
def calculate_live_probs(h_l, a_l, cur_h, cur_a, status):
    if status in ['SCHEDULED', 'TIMED']:
        p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 7)])
        px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(7)])
        p2 = max(0, 1 - p1 - px)
    else:
        rem_h_l, rem_a_l = h_l * 0.45, a_l * 0.45 # Live adjustment
        p1, px, p2 = 0, 0, 0
        for i in range(6):
            for j in range(6):
                prob = poisson.pmf(i, rem_h_l) * poisson.pmf(j, rem_a_l)
                if cur_h + i > cur_a + j: p1 += prob
                elif cur_h + i == cur_a + j: px += prob
                else: p2 += prob
    return p1, px, p2

# --- SIDEBAR ---
st.sidebar.markdown("### ⚙️ Ρυθμίσεις")
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
    
    # ΕΔΩ ΦΤΙΑΧΝΟΥΜΕ ΤΟΝ ΤΙΤΛΟ ΠΟΥ ΚΥΚΛΩΣΕΣ
    st.sidebar.markdown(f"### 🏆 {sel_league_name} Table")
    df = pd.DataFrame([{"#": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table])
    st.sidebar.dataframe(df, hide_index=True, use_container_width=True)

# --- MAIN ---
st.markdown(f'<h1 style="text-align:center; color:white; text-shadow: 2px 2px 8px black;">⚽ {sel_league_name} Predictor</h1>', unsafe_allow_html=True)

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
display_m = [m for m in all_data.get('matches', []) if m['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY', 'PAUSED']][:20]

matches_per_round = num_teams // 2

for i, m in enumerate(display_m):
    if i > 0 and i % matches_per_round == 0:
        st.markdown('<div class="matchday-divider"></div>', unsafe_allow_html=True)

    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    status = m['status']
    score = m.get('score', {}).get('fullTime', {})
    cur_h, cur_a = (score.get('home') or 0), (score.get('away') or 0)
    
    h_l, a_l = (standings_dict.get(h_t, {'gf':1.2})['gf'] + standings_dict.get(a_t, {'ga':1.2})['ga'])/2, (standings_dict.get(a_t, {'gf':1.2})['gf'] + standings_dict.get(h_t, {'ga':1.2})['ga'])/2
    
    p1, px, p2 = calculate_live_probs(h_l, a_l, cur_h, cur_a, status)
    
    live_info = f"🔴 {cur_h}-{cur_a}" if status in ['IN_PLAY', 'PAUSED'] else f"📅 {m['utcDate'][11:16]}"
    title = f"{live_info} | {h_t} vs {a_t}"
    
    with st.expander(title):
        cols = st.columns(3)
        lbls, vals = ["1", "X", "2"], [p1, px, p2]
        for idx in range(3):
            cols[idx].markdown(f"""
                <div style="text-align:center; background:rgba(0,0,0,0.6); padding:10px; border-radius:10px;">
                    <div style="color:#aaa; font-size:12px;">{lbls[idx]}</div>
                    {get_colored_val(vals[idx])}
                </div>
            """, unsafe_allow_html=True)
