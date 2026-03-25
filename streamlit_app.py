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

# --- ΑΣΦΑΛΗΣ ΥΠΟΛΟΓΙΣΜΟΣ STATS ---
def get_advanced_stats(matches, team_name, standings):
    if not matches: return 1.2
    total_goals = 0
    strength_points = 0
    ranks = {t['team']['name']: t['position'] for t in standings} if standings else {}
    
    for m in matches:
        is_h = m['homeTeam']['name'] == team_name
        opp_name = m['awayTeam']['name'] if is_h else m['homeTeam']['name']
        score = m.get('score', {}).get('fullTime', {})
        g = score.get('home') if is_h else score.get('away')
        if g is not None: total_goals += g
        
        # Υπολογισμός δύναμης αντιπάλου
        opp_rank = ranks.get(opp_name, 10)
        if (is_h and score.get('home', 0) > score.get('away', 0)) or \
           (not is_h and score.get('away', 0) > score.get('home', 0)):
            strength_points += (21 - opp_rank)

    avg_goals = total_goals / len(matches) if len(matches) > 0 else 1.2
    return max(0.5, avg_goals + (strength_points / 150))

def calc_all(h_l, a_l):
    # Διασφάλιση ότι οι τιμές δεν είναι μηδέν για την Poisson
    h_l, a_l = max(0.1, h_l), max(0.1, a_l)
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])
    return p1, px, p2, pgg, po25

# --- UI SIDEBAR ---
st.sidebar.title("📍 Ρυθμίσεις")
sel_league_name = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
top_picks = st.sidebar.toggle("🔥 TOP PICKS")
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# --- ΠΙΝΑΚΑΣ ΒΑΘΜΟΛΟΓΙΑΣ (GOOGLE STYLE) ---
st.sidebar.markdown(f"### 🏆 {sel_league_name} Table")
st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_list = []
if st_data and 'standings' in st_data:
    standings_list = st_data['standings'][0]['table']
    df_list = [{"#": t['position'], "Ομάδα": t['team']['shortName'], "Β": t['points']} for t in standings_list]
    st.sidebar.table(pd.DataFrame(df_list).set_index('#'))

# --- ΚΥΡΙΟ ΠΑΝΕΛ ---
st.title(f"⚽ Predictions: {sel_league_name}")
all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = all_data.get('matches', [])
display_m = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED', 'LIVE', 'IN_PLAY']][:15]
if not display_m: display_m = [m for m in all_m if m['status'] == 'FINISHED'][-10:]

for m in display_m:
    h_t, a_t, h_id, a_id = m['homeTeam']['name'], m['awayTeam']['name'], m['homeTeam']['id'], m['awayTeam']['id']
    
    h_f_data = fetch_data(f"https://api.football-data.org/v4/teams/{h_id}/matches?status=FINISHED&limit=5")
    a_f_data = fetch_data(f"https://api.football-data.org/v4/teams/{a_id}/matches?status=FINISHED&limit=5")
    
    h_l = get_advanced_stats(h_f_data.get('matches', []), h_t, standings_list)
    a_l = get_advanced_stats(a_f_data.get('matches', []), a_t, standings_list)
    
    p1, px, p2, pgg, po25 = calc_all(h_l, a_l)
    if top_picks and not (p1 > 0.65 or p2 > 0.65 or po25 > 0.65): continue

    with st.expander(f"⭐ {m['utcDate'][:10]} | {h_t} vs {a_t}"):
        cols = st.columns(5)
        for lbl, val in zip(["1", "X", "2", "GG", "O2.5"], [p1, px, p2, pgg, po25]):
            cols[0 if lbl=="1" else 1 if lbl=="X" else 2 if lbl=="2" else 3 if lbl=="GG" else 4].metric(lbl, f"{round(val*100)}%")

        st.divider()
        
        # ΦΟΡΜΑ ΟΡΙΖΟΝΤΙΑ (ICON ΔΙΠΛΑ ΣΤΟ LOGO)
        for label, f_matches, t_name in [("🏠 " + h_t, h_f_data.get('matches', []), h_t), ("🚀 " + a_t, a_f_data.get('matches', []), a_t)]:
            st.write(f"**{label}**")
            f_cols = st.columns(5)
            for i, tm in enumerate(f_matches):
                is_h = tm['homeTeam']['name'] == t_name
                opp_logo = tm['awayTeam']['crest'] if is_h else tm['homeTeam']['crest']
                score = tm.get('score', {}).get('fullTime', {})
                hg, ag = score.get('home'), score.get('away')
                icon = "🟡" if hg == ag else ("🟢" if (is_h and hg > ag) or (not is_h and ag > hg) else "🔴")
                
                with f_cols[i]:
                    # Χρήση HTML για να είναι το Icon ΔΙΠΛΑ στο σήμα οριζόντια
                    st.markdown(f"""
                        <div style="display: flex; align-items: center; background-color: #f0f2f6; padding: 5px; border-radius: 5px; border: 1px solid #ddd;">
                            <span style="font-size: 18px; margin-right: 5px;">{icon}</span>
                            <img src="{opp_logo}" width="22">
                        </div>
                    """, unsafe_allow_html=True)
            st.write("")

