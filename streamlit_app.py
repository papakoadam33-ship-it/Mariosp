import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

st.set_page_config(page_title="Pro Football Predictor LIVE", layout="wide")

API_KEY = "a963742bcd5642afbe8c842d057f25ad" 

LEAGUES = {'PL':'Premier League','PD':'La Liga','BL1':'Bundesliga','SA':'Serie A','FL1':'Ligue 1','CL':'Champions League','DED':'Eredivisie','ELC':'Championship'}

@st.cache_data(ttl=60)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except: return {}

def get_advanced_stats(matches, team_name, standings):
    if not matches: return 1.2
    total_goals = 0
    ranks = {t['team']['name']: t['position'] for t in standings} if standings else {}
    current_rank = ranks.get(team_name, 10)
    quality_bonus = (21 - current_rank) / 20 
    valid_matches = 0
    for m in matches:
        score = m.get('score', {}).get('fullTime', {})
        # Διόρθωση για None τιμές
        gh = score.get('home') if score.get('home') is not None else 0
        ga = score.get('away') if score.get('away') is not None else 0
        is_h = m['homeTeam']['name'] == team_name
        total_goals += gh if is_h else ga
        valid_matches += 1
    avg_goals = total_goals / valid_matches if valid_matches > 0 else 1.2
    return max(0.5, (avg_goals * 0.6) + (quality_bonus * 0.4)) 

def calc_all(h_l, a_l):
    h_l, a_l = max(0.1, h_l), max(0.1, a_l)
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

st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_list = st_data.get('standings', [{}])[0].get('table', []) if st_data else []

# --- MAIN ---
st.title(f"⚽ Analysis: {sel_league_name}")
all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = all_data.get('matches', [])
# Δείχνουμε Live και τα επόμενα 15 ματς
display_m = [m for m in all_m if m['status'] in ['IN_PLAY', 'PAUSED', 'SCHEDULED', 'TIMED']][:20]

for m in display_m:
    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    status = m['status']
    score = m.get('score', {}).get('fullTime', {})
    
    # ΠΡΟΣΤΑΣΙΑ ΑΠΟ ΤΟ ERROR ΤΗΣ ΕΙΚΟΝΑΣ:
    cur_h = score.get('home') if score.get('home') is not None else 0
    cur_a = score.get('away') if score.get('away') is not None else 0
    total_cur = cur_h + cur_a
    
    if status in ['IN_PLAY', 'PAUSED']:
        title = f"🔴 LIVE: {h_t} {cur_h} - {cur_a} {a_t}"
    else:
        title = f"📅 {m['utcDate'][:10]} | {h_t} vs {a_t}"

    # Fetch Form Data
    h_f = fetch_data(f"https://api.football-data.org/v4/teams/{m['homeTeam']['id']}/matches?status=FINISHED&limit=5&competitions={sel_code}")
    a_f = fetch_data(f"https://api.football-data.org/v4/teams/{m['awayTeam']['id']}/matches?status=FINISHED&limit=5&competitions={sel_code}")
    
    h_l = get_advanced_stats(h_f.get('matches', []), h_t, standings_list)
    a_l = get_advanced_stats(a_f.get('matches', []), a_t, standings_list)
    
    p1, px, p2, pgg, po15, po25 = calc_all(h_l, a_l)

    with st.expander(title):
        cols = st.columns(6)
        lbls = ["1", "X", "2", "GG", "O1.5", "O2.5"]
        
        # ΛΟΓΙΚΗ ΕΜΦΑΝΙΣΗΣ/ΑΠΟΚΡΥΨΗΣ
        # Αν το ματς είναι LIVE, δείχνουμε μόνο όσα δεν έχουν κριθεί
        res_vals = [p1, px, p2, pgg, po15, po25]
        
        for i in range(6):
            if i == 4 and total_cur >= 2: # Over 1.5 check
                cols[i].write("✅ O1.5")
            elif i == 5 and total_cur >= 3: # Over 2.5 check
                cols[i].write("✅ O2.5")
            else:
                cols[i].metric(lbls[i], f"{round(res_vals[i]*100)}%")
        
        st.divider()
        # Φόρμα (Τελευταία 5)
        for label, f_matches, t_name in [("🏠 " + h_t, h_f.get('matches', []), h_t), ("🚀 " + a_t, a_f.get('matches', []), a_t)]:
            st.write(f"**{label}**")
            if not f_matches: st.caption("No recent data")
            else:
                f_cols = st.columns(5)
                for i, tm in enumerate(f_matches[:5]):
                    is_h = tm['homeTeam']['name'] == t_name
                    hg, ag = tm['score']['fullTime']['home'], tm['score']['fullTime']['away']
                    icon = "🟡" if hg == ag else ("🟢" if (is_h and hg > ag) or (not is_h and ag > hg) else "🔴")
                    with f_cols[i]: st.markdown(f'<img src="{tm["awayTeam"]["crest"] if is_h else tm["homeTeam"]["crest"]}" width="20"> {icon}', unsafe_allow_html=True)
