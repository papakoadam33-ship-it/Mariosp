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

def get_stats(matches, team_name, standings):
    if not matches: return 1.2
    total_g = 0
    strength = 0
    ranks = {t['team']['name']: t['position'] for t in standings} if standings else {}
    for m in matches:
        is_h = m['homeTeam']['name'] == team_name
        score = m.get('score', {}).get('fullTime', {})
        g = score.get('home') if is_h else score.get('away')
        if g is not None: total_g += g
        opp_rank = ranks.get(m['awayTeam']['name'] if is_h else m['homeTeam']['name'], 10)
        if (is_h and score.get('home', 0) > score.get('away', 0)) or (not is_h and score.get('away', 0) > score.get('home', 0)):
            strength += (21 - opp_rank)
    return max(0.5, (total_g / len(matches)) + (strength / 150))

def calc_all(h_l, a_l):
    h_l, a_l = max(0.1, h_l), max(0.1, a_l)
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2, pgg = max(0, 1-p1-px), (1-poisson.pmf(0, h_l)) * (1-poisson.pmf(0, a_l))
    po25 = 1 - sum([poisson.pmf(i, h_l+a_l) for i in range(3)])
    return p1, px, p2, pgg, po25

# --- SIDEBAR: ΠΙΝΑΚΑΣ ΜΕ ΣΗΜΑΤΑ ---
st.sidebar.title("📍 Ρυθμίσεις")
sel_league = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
top_picks = st.sidebar.toggle("🔥 TOP PICKS")
sel_code = [k for k, v in LEAGUES.items() if v == sel_league][0]

st.sidebar.markdown(f"### 🏆 {sel_league} Table")
st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_list = []

if st_data and 'standings' in st_data:
    standings_list = st_data['standings'][0]['table']
    # Πίνακας με σήμα εκεί που έβαλες τις μπλε βούλες
    for t in standings_list:
        cols = st.sidebar.columns([1, 1.5, 5, 2])
        cols[0].write(f"{t['position']}")
        cols[1].image(t['team']['crest'], width=20)
        cols[2].write(f"{t['team']['shortName']}")
        cols[3].write(f"**{t['points']}**")
    st.sidebar.markdown("---")

# --- ΚΥΡΙΟ ΠΑΝΕΛ ---
st.title(f"⚽ {sel_league} Analysis")
all_m = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches").get('matches', [])
display_m = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED', 'LIVE', 'IN_PLAY']][:15]
if not display_m: display_m = [m for m in all_m if m['status'] == 'FINISHED'][-10:]

for m in display_m:
    h_t, a_t, h_id, a_id = m['homeTeam']['name'], m['awayTeam']['name'], m['homeTeam']['id'], m['awayTeam']['id']
    h_f = fetch_data(f"https://api.football-data.org/v4/teams/{h_id}/matches?status=FINISHED&limit=5")
    a_f = fetch_data(f"https://api.football-data.org/v4/teams/{a_id}/matches?status=FINISHED&limit=5")
    
    p1, px, p2, pgg, po25 = calc_all(get_stats(h_f.get('matches', []), h_t, standings_list), get_stats(a_f.get('matches', []), a_t, standings_list))
    if top_picks and not (p1 > 0.65 or p2 > 0.65 or po25 > 0.65): continue

    with st.expander(f"⭐ {m['utcDate'][:10]} | {h_t} vs {a_t}"):
        c = st.columns(5)
        for i, (l, v) in enumerate(zip(["1", "X", "2", "GG", "O2.5"], [p1, px, p2, pgg, po25])):
            c[i].metric(l, f"{round(v*100)}%")

        st.divider()
        
        # ΟΡΙΖΟΝΤΙΑ ΦΟΡΜΑ (ΟΠΩΣ ΤΑ ΒΕΛΗ ΣΟΥ)
        for label, f_data, name in [("🏠 " + h_t, h_f.get('matches', []), h_t), ("🚀 " + a_t, a_f.get('matches', []), a_t)]:
            st.write(f"**{label}**")
            
            # Δημιουργούμε μια συνεχή οριζόντια γραμμή με HTML
            form_html = '<div style="display: flex; flex-direction: row; gap: 10px; align-items: center; overflow-x: auto;">'
            for tm in f_data:
                is_h = tm['homeTeam']['name'] == name
                opp_logo = tm['awayTeam']['crest'] if is_h else tm['homeTeam']['crest']
                score = tm.get('score', {}).get('fullTime', {})
                hg, ag = score.get('home', 0), score.get('away', 0)
                icon = "🟡" if hg == ag else ("🟢" if (is_h and hg > ag) or (not is_h and ag > hg) else "🔴")
                
                form_html += f'''
                <div style="display: flex; align-items: center; border: 1px solid #ddd; padding: 4px 8px; border-radius: 4px; background: #f9f9f9; min-width: 60px;">
                    <span style="margin-right: 5px;">{icon}</span>
                    <img src="{opp_logo}" width="20">
                    <div style="width: 1px; height: 20px; background: #eee; margin-left: 8px;"></div>
                </div>
                '''
            form_html += '</div>'
            st.markdown(form_html, unsafe_allow_html=True)
            st.write("")
