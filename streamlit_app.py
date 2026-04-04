import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

st.set_page_config(page_title="Pro Football Predictor Light", layout="wide")

API_KEY = "a963742bcd5642afbe8c842d057f25ad" 

LEAGUES = {
    'PL':'Premier League',
    'PD':'La Liga',
    'BL1':'Bundesliga',
    'SA':'Serie A',
    'FL1':'Ligue 1',
    'CL':'Champions League',
    'DED':'Eredivisie',
    'ELC':'Championship'
}

@st.cache_data(ttl=600) # Αυξήσαμε το cache για να μην κάνουμε περιττές κλήσεις
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except: return {}

def calc_all(h_l, a_l):
    # Default τιμές αν δεν έχουμε στατιστικά
    h_l, a_l = max(0.5, h_l), max(0.5, a_l)
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po15 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(2)])
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])
    return p1, px, p2, pgg, po15, po25

# --- SIDEBAR ---
st.sidebar.title("📍 Ρυθμίσεις")
sel_league_name = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# --- ΒΑΘΜΟΛΟΓΙΑ (ΔΙΟΡΘΩΜΕΝΗ) ---
st.sidebar.markdown(f"### 🏆 {sel_league_name} Table")
st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_dict = {}

if st_data and 'standings' in st_data:
    # Παίρνουμε το συνολικό πίνακα (index 0)
    st_table = st_data['standings'][0]['table']
    for t in st_table:
        # Αποθηκεύουμε γκολ υπέρ/κατά για τον υπολογισμό Poisson
        standings_dict[t['team']['name']] = {
            'rank': t['position'],
            'gf': t['goalsFor'] / t['playedGames'] if t['playedGames'] > 0 else 1.2,
            'ga': t['goalsAgainst'] / t['playedGames'] if t['playedGames'] > 0 else 1.2
        }
    
    df_data = [{"Pos": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table]
    st.sidebar.table(pd.DataFrame(df_data).set_index('Pos'))

# --- MAIN ---
st.title(f"⚽ Predictions: {sel_league_name}")
all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = all_data.get('matches', [])
display_m = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY', 'PAUSED']][:20]

if not display_m:
    st.info("Δεν υπάρχουν προσεχείς αγώνες.")

for m in display_m:
    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    status = m['status']
    score = m.get('score', {}).get('fullTime', {})
    cur_h = score.get('home') if score.get('home') is not None else 0
    cur_a = score.get('away') if score.get('away') is not None else 0
    
    # Υπολογισμός Poisson βάσει της βαθμολογίας (Μηδέν επιπλέον κλήσεις!)
    h_stats = standings_dict.get(h_t, {'gf': 1.2, 'ga': 1.2, 'rank': 10})
    a_stats = standings_dict.get(a_t, {'gf': 1.2, 'ga': 1.2, 'rank': 10})
    
    # Η ισχύς της επίθεσης επηρεάζεται από την άμυνα του αντιπάλου
    h_l = (h_stats['gf'] + a_stats['ga']) / 2
    a_l = (a_stats['gf'] + h_stats['ga']) / 2
    
    p1, px, p2, pgg, po15, po25 = calc_all(h_l, a_l)

    title = f"📅 {m['utcDate'][:10]} | {h_t} vs {a_t}"
    if status in ['IN_PLAY', 'PAUSED']:
        title = f"🔴 LIVE: {h_t} {cur_h} - {cur_a} {a_t}"

    with st.expander(title):
        cols = st.columns(6)
        lbls = ["1", "X", "2", "GG", "O1.5", "O2.5"]
        vals = [p1, px, p2, pgg, po15, po25]
        
        for i in range(6):
            if i == 4 and (cur_h + cur_a) >= 2: cols[i].write("✅ O1.5")
            elif i == 5 and (cur_h + cur_a) >= 3: cols[i].write("✅ O2.5")
            else: cols[i].metric(lbls[i], f"{round(vals[i]*100)}%")
