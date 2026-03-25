import streamlit as st
import requests
from scipy.stats import poisson

st.set_page_config(page_title="Pro Football Predictor", layout="wide")

# --- API CONFIG ---
API_KEY = "a963742bcd5642afbe8c842d057f25ad" 

LEAGUES = {'PL':'Premier League','PD':'La Liga','BL1':'Bundesliga','SA':'Serie A', 'FL1':'Ligue 1'}

@st.cache_data(ttl=600)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except: return {}

def calc_all(h_l, a_l):
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
top_picks = st.sidebar.toggle("🔥 TOP PICKS")
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# --- SIDEBAR: ΟΡΙΖΟΝΤΙΑ ΒΑΘΜΟΛΟΓΙΑ (ΠΙΝΑΚΑΣ) ---
st.sidebar.markdown(f"### 🏆 {sel_league_name}")

# Επικεφαλίδες Πίνακα
h1, h2, h3 = st.sidebar.columns([5, 2, 2])
h1.caption("ΟΜΑΔΑ")
h2.caption("ΘΕΣΗ")
h3.caption("ΒΑΘ")
st.sidebar.markdown("---")

st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
if st_data and 'standings' in st_data:
    for team in st_data['standings'][0]['table']:
        # Όλα σε μία γραμμή (Οριζόντια)
        c_name, c_pos, c_pts = st.sidebar.columns([5, 2, 2])
        
        # Κουτί 1: Σήμα + Όνομα
        with c_name:
            st.markdown(f"<img src='{team['team']['crest']}' width='18'> **{team['team']['shortName']}**", unsafe_allow_html=True)
        
        # Κουτί 2: Θέση (με γραμμή αριστερά)
        c_pos.write(f"| #{team['position']}")
        
        # Κουτί 3: Βαθμοί (με γραμμή αριστερά)
        c_pts.write(f"| **{team['points']}**")
        
        st.sidebar.markdown("<hr style='margin:2px 0; opacity:0.2'>", unsafe_allow_html=True)

# --- ΚΥΡΙΟ ΠΑΝΕΛ ---
st.title(f"⚽ {sel_league_name} Predictions")

data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = data.get('matches', [])
upcoming = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED', 'LIVE']]
display_matches = upcoming[:15] if upcoming else [m for m in all_m if m['status'] == 'FINISHED'][-10:]

for m in display_matches:
    h_t, a_t, h_id, a_id = m['homeTeam']['name'], m['awayTeam']['name'], m['homeTeam']['id'], m['awayTeam']['id']
    p1, px, p2, pgg, po15, po25 = calc_all(1.7, 1.2)
    if top_picks and not (p1 > 0.7 or p2 > 0.7 or po25 > 0.7): continue

    with st.expander(f"⭐ {m['utcDate'][:10]} | {h_t} vs {a_t}"):
        m_cols = st.columns(6)
        m_labels = ["1", "X", "2", "G/G", "O1.5", "O2.5"]
        m_vals = [p1, px, p2, pgg, po15, po25]
        for i in range(6):
            m_cols[i].metric(m_labels[i], f"{round(m_vals[i]*100)}%")

        st.divider()
        
        # ΦΟΡΜΑ ΟΡΙΖΟΝΤΙΑ (5 ΣΕ ΜΙΑ ΣΕΙΡΑ)
        for title, team_id, team_name in [("🏠 " + h_t, h_id, h_t), ("🚀 " + a_t, a_id, a_t)]:
            st.write(f"**{title}**")
            t_matches = fetch_data(f"https://api.football-data.org/v4/teams/{team_id}/matches?status=FINISHED&limit=5")
            
            # Φτιάχνουμε 5 κουτάκια οριζόντια
            f_cols = st.columns(5)
            idx = 0
            for tm in t_matches.get('matches', []):
                is_h = tm['homeTeam']['name'] == team_name
                opp_logo = tm['awayTeam']['crest'] if is_h else tm['homeTeam']['crest']
                score = tm.get('score', {}).get('fullTime', {})
                hg, ag = score.get('home'), score.get('away')
                icon = "🟡" if hg == ag else ("🟢" if (is_h and hg > ag) or (not is_h and ag > hg) else "🔴")
                
                with f_cols[idx]:
                    st.markdown(f"{icon}<br><img src='{opp_logo}' width='20'>", unsafe_allow_html=True)
                idx += 1
            st.write("")
