import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

st.set_page_config(page_title="Pro Football Predictor", layout="wide")

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
    
    valid_matches = 0
    for m in matches:
        score = m.get('score', {}).get('fullTime', {})
        if score.get('home') is not None:
            is_h = m['homeTeam']['name'] == team_name
            g = score.get('home') if is_h else score.get('away')
            total_goals += g
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
parlay_mode = st.sidebar.toggle("🎯 Εμφάνιση Δελτίου Top Picks")
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

st.sidebar.markdown(f"### 🏆 {sel_league_name} Table")
st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_list = []
if st_data and 'standings' in st_data:
    st_table = st_data['standings'][0]['table']
    standings_list = st_table
    df_data = [{"Pos": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table]
    st.sidebar.table(pd.DataFrame(df_data).set_index('Pos'))

# --- MAIN ---
st.title(f"⚽ Predictions: {sel_league_name}")
all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = all_data.get('matches', [])
display_m = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED', 'LIVE', 'IN_PLAY']][:15]

top_picks = []

if not display_m:
    st.warning("Δεν βρέθηκαν προσεχείς αγώνες.")
else:
    for m in display_m:
        h_t, a_t, h_id, a_id = m['homeTeam']['name'], m['awayTeam']['name'], m['homeTeam']['id'], m['awayTeam']['id']
        date_str = m['utcDate'][:10]
        
        # ΔΙΟΡΘΩΣΗ: Προσθήκη ανταγωνισμού στο URL για να φέρνει τα σωστά ματς της ομάδας
        h_f_data = fetch_data(f"https://api.football-data.org/v4/teams/{h_id}/matches?status=FINISHED&limit=10&competitions={sel_code}")
        a_f_data = fetch_data(f"https://api.football-data.org/v4/teams/{a_id}/matches?status=FINISHED&limit=10&competitions={sel_code}")
        
        h_f_matches = h_f_data.get('matches', [])[:5]
        a_f_matches = a_f_data.get('matches', [])[:5]
        
        p1, px, p2, pgg, po15, po25 = calc_all(
            get_advanced_stats(h_f_matches, h_t, standings_list), 
            get_advanced_stats(a_f_matches, a_t, standings_list)
        )

        if p1 > 0.70: top_picks.append({"m": f"{h_t} - {a_t}", "t": "1", "p": p1})
        elif p2 > 0.70: top_picks.append({"m": f"{h_t} - {a_t}", "t": "2", "p": p2})
        elif po15 > 0.85: top_picks.append({"m": f"{h_t} - {a_t}", "t": "Over 1.5", "p": po15})

        with st.expander(f"📅 {date_str} | {h_t} vs {a_t}"):
            cols = st.columns(6)
            lbls, vals = ["1", "X", "2", "GG", "O1.5", "O2.5"], [p1, px, p2, pgg, po15, po25]
            for i in range(6): cols[i].metric(lbls[i], f"{round(vals[i]*100)}%")
            
            st.divider()
            for label, f_matches, t_name in [("🏠 " + h_t, h_f_matches, h_t), ("🚀 " + a_t, a_f_matches, a_t)]:
                st.write(f"**{label}**")
                if not f_matches:
                    st.caption("Δεν βρέθηκαν πρόσφατα ματς.")
                else:
                    f_cols = st.columns(5)
                    for i, tm in enumerate(f_matches):
                        is_h = tm['homeTeam']['name'] == t_name
                        opp_logo = tm['awayTeam']['crest'] if is_h else tm['homeTeam']['crest']
                        score = tm.get('score', {}).get('fullTime', {})
                        hg, ag = score.get('home', 0), score.get('away', 0)
                        icon = "🟡" if hg == ag else ("🟢" if (is_h and hg > ag) or (not is_h and ag > hg) else "🔴")
                        with f_cols[i]:
                            st.markdown(f'<div style="display: flex; align-items: center; gap: 5px;"><span>{icon}</span><img src="{opp_logo}" width="20"></div>', unsafe_allow_html=True)

if parlay_mode and top_picks:
    st.sidebar.success("### 🎯 Το Δελτίο σου")
    total_odds = 1.0
    for pick in top_picks:
        odd = round(1/pick['p'], 2)
        total_odds *= odd
        st.sidebar.write(f"🔹 {pick['m']}: **{pick['t']}** ({odd})")
    st.sidebar.info(f"🔥 Συνολική Απόδοση: **{round(total_odds, 2)}**")
