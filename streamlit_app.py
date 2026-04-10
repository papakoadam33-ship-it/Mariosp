import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

st.set_page_config(page_title="Pro Football Predictor PRO", layout="wide")

# --- CUSTOM CSS ΓΙΑ BACKGROUND & STYLE ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), 
        url("https://images.unsplash.com/photo-1508098682722-e99c43a406b2?ixlib=rb-1.2.1&auto=format&fit=crop&w=1950&q=80");
        background-size: cover;
        background-attachment: fixed;
    }
    .stMetric {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 10px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .streamlit-expanderHeader {
        background-color: rgba(0, 0, 0, 0.5) !important;
        color: white !important;
        border-radius: 10px;
    }
    h1, h2, h3, p {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

API_KEY = "a963742bcd5642afbe8c842d057f25ad" 

LEAGUES = {'PL':'Premier League','PD':'La Liga','BL1':'Bundesliga','SA':'Serie A','FL1':'Ligue 1','CL':'Champions League','DED':'Eredivisie','ELC':'Championship'}

@st.cache_data(ttl=600)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except: return {}

def calc_all(h_l, a_l, cur_h=0, cur_a=0, is_live=False):
    # Αν είναι live, ο χρόνος που απομένει μειώνει το αναμενόμενο Poisson
    # Επειδή το δωρεάν API δεν δίνει λεπτό, υποθέτουμε ότι στο Live έχει περάσει ο μισός χρόνος (0.5)
    time_factor = 0.5 if is_live else 1.0
    h_l_rem = h_l * time_factor
    a_l_rem = a_l * time_factor

    # Πιθανότητες για τα γκολ που απομένουν
    p1_rem = sum([poisson.pmf(i, h_l_rem) * sum([poisson.pmf(j, a_l_rem) for j in range(i)]) for i in range(1, 10)])
    px_rem = sum([poisson.pmf(i, h_l_rem) * poisson.pmf(i, a_l_rem) for i in range(10)])
    p2_rem = max(0, 1 - p1_rem - px_rem)

    # Προσαρμογή 1Χ2 βάσει τρέχοντος σκορ
    if is_live:
        if cur_h > cur_a: p1, px, p2 = 0.8, 0.15, 0.05
        elif cur_a > cur_h: p1, px, p2 = 0.05, 0.15, 0.8
        else: p1, px, p2 = 0.2, 0.6, 0.2
    else:
        p1, px, p2 = p1_rem, px_rem, p2_rem

    pgg = (1 - poisson.pmf(0, h_l_rem + cur_h)) * (1 - poisson.pmf(0, a_l_rem + cur_a))
    po15 = 1 - sum([poisson.pmf(i, h_l_rem + a_l_rem + cur_h + cur_a) for i in range(2)])
    po25 = 1 - sum([poisson.pmf(i, h_l_rem + a_l_rem + cur_h + cur_a) for i in range(3)])
    
    return p1, px, p2, pgg, po15, po25

# --- SIDEBAR ---
st.sidebar.title("📍 Control Panel")
sel_league_name = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_dict = {}
if st_data and 'standings' in st_data:
    st_table = st_data['standings'][0]['table']
    for t in st_table:
        standings_dict[t['team']['name']] = {
            'gf': t['goalsFor'] / t['playedGames'] if t['playedGames'] > 0 else 1.2,
            'ga': t['goalsAgainst'] / t['playedGames'] if t['playedGames'] > 0 else 1.2
        }
    df_data = [{"Pos": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table]
    st.sidebar.table(pd.DataFrame(df_data).set_index('Pos'))

# --- MAIN ---
st.title(f"🏆 {sel_league_name} Insights")
all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = all_data.get('matches', [])
display_m = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY', 'PAUSED']][:20]

for m in display_m:
    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    status = m['status']
    is_live = status in ['IN_PLAY', 'PAUSED']
    score = m.get('score', {}).get('fullTime', {})
    cur_h, cur_a = (score.get('home') or 0), (score.get('away') or 0)
    
    h_stats = standings_dict.get(h_t, {'gf': 1.2, 'ga': 1.2})
    a_stats = standings_dict.get(a_t, {'gf': 1.2, 'ga': 1.2})
    h_l, a_l = (h_stats['gf'] + a_stats['ga'])/2, (a_stats['gf'] + h_stats['ga'])/2
    
    # Κλήση της νέας Live Poisson συνάρτησης
    p1, px, p2, pgg, po15, po25 = calc_all(h_l, a_l, cur_h, cur_a, is_live)

    title = f"📅 {m['utcDate'][:10]} | {h_t} vs {a_t}"
    if is_live: title = f"🔴 LIVE {cur_h} - {cur_a} | {h_t} vs {a_t}"

    with st.expander(title):
        cols = st.columns(6)
        lbls = ["1", "X", "2", "GG", "O1.5", "O2.5"]
        vals = [p1, px, p2, pgg, po15, po25]
        for i in range(6):
            if i == 4 and (cur_h + cur_a) >= 2: cols[i].markdown("### ✅ O1.5")
            elif i == 5 and (cur_h + cur_a) >= 3: cols[i].markdown("### ✅ O2.5")
            else: cols[i].metric(lbls[i], f"{round(vals[i]*100)}%")
