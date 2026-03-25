import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

st.set_page_config(page_title="Pro Football Predictor", layout="wide")

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
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po15 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(2)])
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])
    return p1, px, p2, pgg, po15, po25

# --- UI SIDEBAR ---
st.sidebar.title("📍 Ρυθμίσεις")
sel_league_name = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
top_picks = st.sidebar.toggle("🔥 TOP PICKS (>70%)")
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# --- SIDEBAR: ΒΑΘΜΟΛΟΓΙΑ (Standings) ---
st.sidebar.markdown(f"### 🏆 Βαθμολογία {sel_league_name}")
st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
if st_data and 'standings' in st_data:
    table = st_data['standings'][0]['table']
    for team in table:
        # Δημιουργούμε μια compact γραμμή για το sidebar
        col1, col2, col3, col4 = st.sidebar.columns([1, 2, 6, 2])
        col1.write(f"**{team['position']}**")
        col2.image(team['team']['crest'], width=20)
        col3.write(team['team']['shortName'])
        col4.write(f"**{team['points']}**")
    st.sidebar.divider()

# --- ΚΥΡΙΟ ΠΑΝΕΛ: ΑΓΩΝΕΣ ---
st.title(f"⚽ {sel_league_name} Predictions")

data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = data.get('matches', [])
upcoming = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED', 'LIVE']]

if not upcoming:
    st.info("📅 Δεν υπάρχουν μελλοντικά ματς. Εμφάνιση πρόσφατων αποτελεσμάτων:")
    display_matches = [m for m in all_m if m['status'] == 'FINISHED'][-10:]
else:
    display_matches = upcoming[:15]

for m in display_matches:
    h_t, a_t, h_id, a_id = m['homeTeam']['name'], m['awayTeam']['name'], m['homeTeam']['id'], m['awayTeam']['id']
    p1, px, p2, pgg, po15, po25 = calc_all(1.7, 1.2)
    if top_picks and not (p1 > 0.7 or p2 > 0.7 or po25 > 0.7): continue

    with st.expander(f"⭐ {m['utcDate'][:10]} | {h_t} vs {a_t}"):
        cols = st.columns(6)
        cols[0].metric("1", f"{round(p1*100)}%")
        cols[1].metric("X", f"{round(px*100)}%")
        cols[2].metric("2", f"{round(p2*100)}%")
        cols[3].metric("GG", f"{round(pgg*100)}%")
        cols[4].metric("O1.5", f"{round(po15*100)}%")
        cols[5].metric("O2.5", f"{round(po25*100)}%")
        
        st.divider()
        c_h, c_a = st.columns(2)
        h_d = fetch_data(f"https://api.football-data.org/v4/teams/{h_id}/matches?status=FINISHED&limit=8")
        a_d = fetch_data(f"https://api.football-data.org/v4/teams/{a_id}/matches?status=FINISHED&limit=8")
        icons_h, logos_h = get_visual_form(h_t, h_d.get('matches', []))
        icons_a, logos_a = get_visual_form(a_t, a_d.get('matches', []))
        
        with c_h:
            st.write(f"🏠 **{h_t}**")
            f_cols = st.columns(5)
            for i in range(len(icons_h)):
                with f_cols[i]:
                    st.write(icons_h[i])
                    st.image(logos_h[i], width=20)
        with c_a:
            st.write(f"🚀 **{a_t}**")
            f_cols_a = st.columns(5)
            for i in range(len(icons_a)):
                with f_cols_a[i]:
                    st.write(icons_a[i])
                    st.image(logos_a[i], width=20)
