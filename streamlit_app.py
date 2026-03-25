import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

st.set_page_config(page_title="Pro Predictor & Standings", layout="wide")

# --- API CONFIG ---
API_KEY = "a963742bcd5642afbe8c842d057f25ad" 

LEAGUES = {
    'PL': 'Premier League',
    'PD': 'La Liga',
    'BL1': 'Bundesliga',
    'SA': 'Serie A',
    'FL1': 'Ligue 1'
}

@st.cache_data(ttl=600)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except: return {}

# --- ΣΥΝΑΡΤΗΣΗ ΓΙΑ ΒΑΘΜΟΛΟΓΙΑ ---
def get_standings(league_code):
    url = f"https://api.football-data.org/v4/competitions/{league_code}/standings"
    data = fetch_data(url)
    table = data.get('standings', [{}])[0].get('table', [])
    return table

def get_visual_form(team_name, matches):
    if not matches: return [], []
    form_icons, opponent_logos = [], []
    for m in matches:
        if m.get('status') != 'FINISHED': continue
        is_h = m['homeTeam']['name'] == team_name
        opp_logo = m['awayTeam']['crest'] if is_h else m['homeTeam']['crest']
        score = m.get('score', {}).get('fullTime', {})
        hg, ag = score.get('home'), score.get('away')
        if hg is None: continue
        icon = "🟡" if hg == ag else ("🟢" if (is_h and hg > ag) or (not is_h and ag > hg) else "🔴")
        form_icons.append(icon); opponent_logos.append(opp_logo)
        if len(form_icons) == 5: break
    return form_icons, opponent_logos

def calc_all(h_l, a_l):
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2, pgg = max(0, 1 - p1 - px), (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po15, po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(2)]), 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])
    return p1, px, p2, pgg, po15, po25

# --- UI ---
st.title("⚽ Football Pro: Predictions & Standings")
sel_league_name = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
top_picks = st.sidebar.toggle("🔥 TOP PICKS (>70%)")
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# Χωρίζουμε την οθόνη σε 2 μέρη: Αγώνες και Βαθμολογία
col_left, col_right = st.columns([2, 1])

with col_left:
    st.header("📅 Αγώνες & Προβλέψεις")
    data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
    all_m = data.get('matches', [])
    upcoming = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED', 'LIVE']]
    display_matches = upcoming[:15] if upcoming else [m for m in all_m if m['status'] == 'FINISHED'][-10:]

    for m in display_matches:
        h_t, a_t, h_id, a_id = m['homeTeam']['name'], m['awayTeam']['name'], m['homeTeam']['id'], m['awayTeam']['id']
        p1, px, p2, pgg, po15, po25 = calc_all(1.7, 1.2)
        if top_picks and not (p1 > 0.7 or p2 > 0.7 or po25 > 0.7): continue

        with st.expander(f"⭐ {m['utcDate'][:10]} | {h_t} vs {a_t}"):
            # (Κώδικας metrics & φόρμας όπως πριν...)
            st.write(f"🏠 {h_t} vs 🚀 {a_t}")
            # ... (εδώ μπαίνουν τα metrics και τα logos της φόρμας)

with col_right:
    st.header("🏆 Βαθμολογία")
    standings = get_standings(sel_code)
    for team in standings:
        # Δημιουργούμε μια γραμμή για κάθε ομάδα με σήμα και όνομα
        c1, c2, c3, c4 = st.columns([0.5, 1, 3, 1])
        with c1: st.write(f"**{team['position']}**")
        with c2: st.image(team['team']['crest'], width=25)
        with c3: st.write(team['team']['shortName'])
        with c4: st.write(f"**{team['points']}**")
        st.divider()
