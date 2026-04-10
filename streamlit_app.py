import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# Ρύθμιση σελίδας
st.set_page_config(page_title="Pro Football Predictor", layout="wide")

# --- CSS ΓΙΑ ΤΟ ΤΕΛΙΚΟ DESIGN (Restored) ---
st.markdown("""
    <style>
    /* 1. Η Ατμοσφαιρική Φωτογραφία που ήθελες */
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), 
        url("https://images.unsplash.com/photo-1510051646601-988fd274169c?q=80&w=2070&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* 2. Sidebar: Λευκό Φόντο + ΚΑΤΑΜΑΥΡΑ ΓΡΑΜΜΑΤΑ */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
    }
    [data-testid="stSidebar"] * {
        color: #000000 !important;
        font-weight: 800 !important;
    }

    /* 3. Μαύρο Sidebar Toggle (Οι τρεις γραμμές πάνω αριστερά) */
    [data-testid="stHeader"] button svg, 
    [data-testid="stSidebarCollapsedControl"] svg {
        fill: #000000 !important;
    }

    /* 4. ΤΙΤΛΟΙ ΑΓΩΝΩΝ: ΚΑΤΑΛΕΥΚΟΙ (Force CSS) */
    /* Αυτό το κομμάτι στοχεύει απευθείας στο κείμενο του expander */
    .streamlit-expanderHeader div[data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 1.25rem !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,1) !important;
    }

    .streamlit-expanderHeader {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    
    /* 5. Main Title */
    .main-title {
        color: white !important;
        font-size: 2.5rem !important;
        font-weight: 800;
        text-align: center;
        padding: 20px;
    }

    /* 6. Απόκρυψη Toolbar Πίνακα */
    [data-testid="stElementToolbar"] {
        display: none !important;
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

def get_colored_val(val):
    perc = round(val * 100)
    if perc >= 70:
        return f'<span style="color: #00ff88; font-weight: bold; font-size: 22px;">{perc}%</span>'
    return f'<span style="color: white; font-size: 18px;">{perc}%</span>'

# --- SIDEBAR ---
st.sidebar.title("📌 Ρυθμίσεις")
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
    df_sidebar = [{"Pos": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table]
    st.sidebar.dataframe(pd.DataFrame(df_sidebar), hide_index=True, use_container_width=True)

# --- MAIN ---
st.markdown(f'<div class="main-title">⚽ {sel_league_name} Predictor</div>', unsafe_allow_html=True)

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = all_data.get('matches', [])
display_m = [m for m in all_m if m['status'] in ['IN_PLAY', 'PAUSED', 'SCHEDULED', 'TIMED']][:15]

for m in display_m:
    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    status = m['status']
    score = m.get('score', {}).get('fullTime', {})
    cur_h, cur_a = (score.get('home') or 0), (score.get('away') or 0)
    
    h_stats = standings_dict.get(h_t, {'gf': 1.2, 'ga': 1.2})
    a_stats = standings_dict.get(a_t, {'gf': 1.2, 'ga': 1.2})
    h_l, a_l = (h_stats['gf'] + a_stats['ga'])/2, (a_stats['gf'] + h_stats['ga'])/2
    
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

    # Expanders
    with st.expander(title):
        cols = st.columns(6)
        lbls = ["1", "X", "2", "GG", "O1.5", "O2.5"]
        vals = [p1, px, p2, pgg, po15, po25]
        for i in range(6):
            with cols[i]:
                st.markdown(f"""<div style="text-align: center; background: rgba(0,0,0,0.5); padding: 10px; border-radius: 10px;">
                    <div style="color: #bbb; font-size: 14px; margin-bottom: 5px;">{lbls[i]}</div>
                    {get_colored_val(vals[i])}
                </div>""", unsafe_allow_html=True)


