import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

st.set_page_config(page_title="Pro Football Predictor", layout="wide")

# --- API CONFIG ---
API_KEY = "a963742bcd5642afbe8c842d057f25ad" 

LEAGUES = {'PL':'Premier League','PD':'La Liga', 'BL1':'Bundesliga', 'SA':'Serie A', 'FL1':'Ligue 1'}

@st.cache_data(ttl=300)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except: return {}

# --- ΥΠΟΛΟΓΙΣΜΟΣ ΠΡΑΓΜΑΤΙΚΩΝ ΣΤΑΤΙΣΤΙΚΩΝ ---
def get_team_lambda(matches, team_name):
    goals = []
    for m in matches:
        if m.get('status') == 'FINISHED':
            is_h = m['homeTeam']['name'] == team_name
            g = m['score']['fullTime']['home'] if is_h else m['score']['fullTime']['away']
            if g is not None: goals.append(g)
    return sum(goals) / len(goals) if goals else 1.2

def calc_all(h_l, a_l):
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po15 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(2)])
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])
    return p1, px, p2, pgg, po15, po25

# --- UI ---
st.sidebar.title("📍 Ρυθμίσεις")
sel_league_name = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
top_picks = st.sidebar.toggle("🔥 TOP PICKS")
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# --- ΠΙΝΑΚΑΣ ΒΑΘΜΟΛΟΓΙΑΣ (GOOGLE STYLE) ---
st.sidebar.markdown(f"### 🏆 Πίνακας {sel_league_name}")
st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")

if st_data and 'standings' in st_data:
    raw_table = st_data['standings'][0]['table']
    for t in raw_table:
        # Οριζόντια κουτάκια: Ομάδα(Σήμα+Όνομα) | Θέση | Βαθμοί
        c1, c2, c3 = st.sidebar.columns([5, 2, 2])
        with c1:
            st.markdown(f"<img src='{t['team']['crest']}' width='18'> {t['team']['shortName']}", unsafe_allow_html=True)
        with c2: st.write(f"#{t['position']}")
        with c3: st.write(f"**{t['points']}**")
        st.sidebar.markdown("<hr style='margin:1px 0; opacity:0.1'>", unsafe_allow_html=True)

# --- ΑΓΩΝΕΣ ---
st.title(f"⚽ {sel_league_name} Predictions")
all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_matches = all_data.get('matches', [])
display_matches = [m for m in all_matches if m['status'] in ['SCHEDULED', 'TIMED', 'LIVE']][:15]
if not display_matches: display_matches = [m for m in all_matches if m['status'] == 'FINISHED'][-10:]

for m in display_matches:
    h_t, a_t, h_id, a_id = m['homeTeam']['name'], m['awayTeam']['name'], m['homeTeam']['id'], m['awayTeam']['id']
    
    # 1. Φέρνουμε τα τελευταία 5 ματς για ΠΡΑΓΜΑΤΙΚΑ ΣΤΑΤΙΣΤΙΚΑ
    h_f_data = fetch_data(f"https://api.football-data.org/v4/teams/{h_id}/matches?status=FINISHED&limit=5")
    a_f_data = fetch_data(f"https://api.football-data.org/v4/teams/{a_id}/matches?status=FINISHED&limit=5")
    
    h_lambda = get_team_lambda(h_f_data.get('matches', []), h_t)
    a_lambda = get_team_lambda(a_f_data.get('matches', []), a_t)
    
    # 2. Υπολογισμός πιθανοτήτων βάσει φόρμας
    p1, px, p2, pgg, po15, po25 = calc_all(h_lambda, a_lambda)
    
    if top_picks and not (p1 > 0.7 or p2 > 0.7 or po25 > 0.7): continue

    with st.expander(f"⭐ {m['utcDate'][:10]} | {h_t} vs {a_t}"):
        cols = st.columns(6)
        labels = ["1", "X", "2", "GG", "O1.5", "O2.5"]
        vals = [p1, px, p2, pgg, po15, po25]
        for i in range(6):
            cols[i].metric(labels[i], f"{round(vals[i]*100)}%")

        st.divider()
        
        # 3. ΦΟΡΜΑ (5 ΜΑΤΣ ΔΙΠΛΑ-ΔΙΠΛΑ - ΟΡΙΖΟΝΤΙΑ)
        for label, f_matches, t_name in [("🏠 " + h_t, h_f_data.get('matches', []), h_t), ("🚀 " + a_t, a_f_data.get('matches', []), a_t)]:
            st.write(f"**{label}**")
            f_cols = st.columns(10) # 5 στήλες για τα 5 ματς
            for i, tm in enumerate(f_matches):
                is_h = tm['homeTeam']['name'] == t_name
                opp_logo = tm['awayTeam']['crest'] if is_h else tm['homeTeam']['crest']
                hg, ag = tm['score']['fullTime']['home'], tm['score']['fullTime']['away']
                icon = "🟡" if hg == ag else ("🟢" if (is_h and hg > ag) or (not is_h and ag > hg) else "🔴")
                
                with f_cols[i]:
                    st.markdown(f"{icon}<br><img src='{opp_logo}' width='20'>", unsafe_allow_html=True)
