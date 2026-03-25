import streamlit as st
import requests
from scipy.stats import poisson

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

def get_advanced_stats(matches, team_name, standings):
    if not matches: return 1.2
    total_g, strength = 0, 0
    ranks = {t['team']['name']: t['position'] for t in standings} if standings else {}
    for m in matches:
        is_h = m['homeTeam']['name'] == team_name
        score = m.get('score', {}).get('fullTime', {})
        g = score.get('home') if is_h else score.get('away')
        if g is not None: total_g += g
        opp_name = m['awayTeam']['name'] if is_h else m['homeTeam']['name']
        opp_rank = ranks.get(opp_name, 10)
        if (is_h and score.get('home', 0) > score.get('away', 0)) or (not is_h and score.get('away', 0) > score.get('home', 0)):
            strength += (21 - opp_rank)
    avg = total_g / len(matches) if len(matches) > 0 else 1.2
    return max(0.5, avg + (strength / 150))

def calc_all(h_l, a_l):
    h_l, a_l = max(0.1, h_l), max(0.1, a_l)
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2, pgg = max(0, 1-p1-px), (1-poisson.pmf(0, h_l)) * (1-poisson.pmf(0, a_l))
    po15 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(2)])
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])
    return p1, px, p2, pgg, po15, po25

# --- SIDEBAR: ΠΙΝΑΚΑΣ ΜΕ ΚΟΥΤΑΚΙΑ (HTML TABLE) ---
st.sidebar.title("📍 Ρυθμίσεις")
sel_league = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
top_picks = st.sidebar.toggle("🔥 TOP PICKS (>70%)")
sel_code = [k for k, v in LEAGUES.items() if v == sel_league][0]

st.sidebar.markdown(f"### 🏆 {sel_league} Table")
st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_list = []

if st_data and 'standings' in st_data:
    standings_list = st_data['standings'][0]['table']
    # Δημιουργία Πίνακα με HTML για να έχει γραμμές και κουτάκια
    table_html = """
    <table style="width:100%; border-collapse: collapse; font-size: 14px;">
        <tr style="background-color: #f0f2f6; border-bottom: 2px solid #ddd;">
            <th style="padding: 5px; text-align: left;">#</th>
            <th style="padding: 5px; text-align: left;">S</th>
            <th style="padding: 5px; text-align: left;">Ομάδα</th>
            <th style="padding: 5px; text-align: right;">B</th>
        </tr>
    """
    for t in standings_list:
        table_html += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 5px;">{t['position']}</td>
            <td style="padding: 5px;"><img src="{t['team']['crest']}" width="18"></td>
            <td style="padding: 5px;">{t['team']['shortName']}</td>
            <td style="padding: 5px; text-align: right;"><b>{t['points']}</b></td>
        </tr>
        """
    table_html += "</table>"
    st.sidebar.markdown(table_html, unsafe_allow_html=True)

# --- ΚΥΡΙΟ ΠΑΝΕΛ ---
st.title(f"⚽ Predictions: {sel_league}")
all_m = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches").get('matches', [])
display_m = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED', 'LIVE', 'IN_PLAY']][:15]
if not display_m: display_m = [m for m in all_m if m['status'] == 'FINISHED'][-10:]

for m in display_m:
    h_t, a_t, h_id, a_id = m['homeTeam']['name'], m['awayTeam']['name'], m['homeTeam']['id'], m['awayTeam']['id']
    h_f = fetch_data(f"https://api.football-data.org/v4/teams/{h_id}/matches?status=FINISHED&limit=5")
    a_f = fetch_data(f"https://api.football-data.org/v4/teams/{a_id}/matches?status=FINISHED&limit=5")
    
    p1, px, p2, pgg, po15, po25 = calc_all(get_advanced_stats(h_f.get('matches', []), h_t, standings_list), get_advanced_stats(a_f.get('matches', []), a_t, standings_list))
    
    if top_picks and not (p1 > 0.7 or p2 > 0.7 or po25 > 0.7 or po15 > 0.85): continue

    with st.expander(f"⭐ {m['utcDate'][:10]} | {h_t} vs {a_t}"):
        cols = st.columns(6)
        labels = ["1", "X", "2", "GG", "O1.5", "O2.5"]
        vals = [p1, px, p2, pgg, po15, po25]
        for i in range(6):
            cols[i].metric(labels[i], f"{round(vals[i]*100)}%")

        st.divider()
        
        # ΦΟΡΜΑ ΟΡΙΖΟΝΤΙΑ (ICON ΔΙΠΛΑ ΣΤΟ ΣΗΜΑ - ΟΠΩΣ ΤΑ ΒΕΛΗ)
        for label, f_matches, t_name in [("🏠 " + h_t, h_f.get('matches', []), h_t), ("🚀 " + a_t, a_f.get('matches', []), a_t)]:
            st.write(f"**{label}**")
            f_cols = st.columns(5)
            for i, tm in enumerate(f_matches):
                is_h = tm['homeTeam']['name'] == t_name
                opp_logo = tm['awayTeam']['crest'] if is_h else tm['homeTeam']['crest']
                score = tm.get('score', {}).get('fullTime', {})
                hg, ag = score.get('home', 0), score.get('away', 0)
                icon = "🟡" if hg == ag else ("🟢" if (is_h and hg > ag) or (not is_h and ag > hg) else "🔴")
                with f_cols[i]:
                    st.markdown(f"""
                        <div style="display: flex; align-items: center; gap: 6px; border-left: 3px solid #ddd; padding-left: 5px;">
                            <span style="font-size: 16px;">{icon}</span>
                            <img src="{opp_logo}" width="20">
                        </div>
                    """, unsafe_allow_html=True)
