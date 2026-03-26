import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

st.set_page_config(page_title="Pro Football Predictor", layout="wide")

API_KEY = "a963742bcd5642afbe8c842d057f25ad" 
LEAGUES = {'PL':'Premier League','PD':'La Liga', 'BL1':'Bundesliga', 'SA':'Serie A', 'FL1':'Ligue 1'}

@st.cache_data(ttl=300)
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
    for m in matches:
        is_h = m['homeTeam']['name'] == team_name
        score = m.get('score', {}).get('fullTime', {})
        g = score.get('home') if is_h else score.get('away')
        if g is not None: total_goals += g
    avg_goals = total_goals / len(matches) if len(matches) > 0 else 1.2
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
parlay_btn = st.sidebar.button("🎯 Δημιουργία Δελτίου (Top Picks)")
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_list = st_data.get('standings', [{}])[0].get('table', []) if st_data else []

if standings_list:
    st.sidebar.markdown(f"### 🏆 {sel_league_name} Table")
    df_data = [{"Pos": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in standings_list]
    st.sidebar.table(pd.DataFrame(df_data).set_index('Pos'))

# --- MAIN ---
st.title(f"⚽ Predictions: {sel_league_name}")

all_m = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches").get('matches', [])
display_m = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED', 'LIVE', 'IN_PLAY']][:15]

top_parlay_list = []

for m in display_m:
    h_t, a_t, h_id, a_id = m['homeTeam']['name'], m['awayTeam']['name'], m['homeTeam']['id'], m['awayTeam']['id']
    h_f = fetch_data(f"https://api.football-data.org/v4/teams/{h_id}/matches?status=FINISHED&limit=5")
    a_f = fetch_data(f"https://api.football-data.org/v4/teams/{a_id}/matches?status=FINISHED&limit=5")
    
    p1, px, p2, pgg, po15, po25 = calc_all(get_advanced_stats(h_f.get('matches', []), h_t, standings_list), get_advanced_stats(a_f.get('matches', []), a_t, standings_list))
    
    # Προσθήκη στα Top Picks αν η πιθανότητα είναι > 70%
    if p1 > 0.70: top_parlay_list.append({"match": f"{h_t} - {a_t}", "tip": "1", "prob": p1})
    elif p2 > 0.70: top_parlay_list.append({"match": f"{h_t} - {a_t}", "tip": "2", "prob": p2})
    elif po15 > 0.80: top_parlay_list.append({"match": f"{h_t} - {a_t}", "tip": "Over 1.5", "prob": po15})

    # (Εδώ μπαίνει ο κώδικας του Expander που είχαμε στον v16.7 για να βλέπεις τα ματς ένα-ένα)
    with st.expander(f"⭐ {h_t} vs {a_t}"):
        cols = st.columns(6)
        lbls, vals = ["1", "X", "2", "GG", "O1.5", "O2.5"], [p1, px, p2, pgg, po15, po25]
        for i in range(6): cols[i].metric(lbls[i], f"{round(vals[i]*100)}%")

# --- PARLAY SECTION ---
if parlay_btn and top_parlay_list:
    st.success("### 🎯 Το Δελτίο της Ημέρας")
    total_odds = 1.0
    for pick in top_parlay_list:
        est_odd = round(1 / pick['prob'], 2) # Υπολογισμός απόδοσης βάσει πιθανότητας
        total_odds *= est_odd
        st.write(f"✅ **{pick['match']}** -> Σημείο: `{pick['tip']}` (Απόδοση: {est_odd})")
    st.info(f"🔥 **Συνολική Απόδοση: {round(total_odds, 2)}**")
