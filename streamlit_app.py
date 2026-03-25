import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
from datetime import datetime, timedelta

st.set_page_config(page_title="Pro Football Predictor PRO", layout="wide")

# --- ΡΥΘΜΙΣΕΙΣ API ---
API_KEY = "ΤΟ_ΚΛΕΙΔΙ_ΣΟΥ_ΕΔΩ" # <--- ΒΑΛΕ ΤΟ ΔΙΚΟ ΣΟΥ ΚΛΕΙΔΙ ΕΔΩ

LEAGUES = {
    'PL': 'Premier League',
    'PD': 'La Liga',
    'BL1': 'Bundesliga',
    'SA': 'Serie A',
    'FL1': 'Ligue 1',
    'PPL': 'Primeira Liga'
}

def get_form_string(team_name, matches_list):
    if not matches_list:
        return "N/A", ["Δεν βρέθηκαν πρόσφατα ματς"]
    form = []
    details = []
    for m in matches_list:
        if m.get('status') != 'FINISHED': continue
        is_home = m['homeTeam']['name'] == team_name
        opp = m['awayTeam']['name'] if is_home else m['homeTeam']['name']
        score = m.get('score', {}).get('fullTime', {})
        h_g, a_g = score.get('home'), score.get('away')
        
        if h_g is None or a_g is None: continue
        
        if h_g == a_g: 
            icon, txt = "🟡", f"Ισοπαλία {h_g}-{a_g} με {opp}"
        elif (is_home and h_g > a_g) or (not is_home and a_g > h_g):
            icon, txt = "🟢", f"Νίκη {h_g}-{a_g} με {opp}"
        else:
            icon, txt = "🔴", f"Ήττα {h_g}-{a_g} με {opp}"
        
        form.append(icon)
        details.append(txt)
        if len(form) == 5: break
    return "".join(form) if form else "N/A", details

@st.cache_data(ttl=600)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json()
    except: pass
    return {}

def calc_all(h_l, a_l):
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po15 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(2)])
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])
    return p1, px, p2, pgg, po15, po25

# --- UI ---
st.title("⚽ Pro Predictor & League Tracker")

st.sidebar.header("📍 Επιλογές")
sel_league_name = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
top_picks = st.sidebar.toggle("🔥 TOP PICKS (>70%)")

sel_league_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# --- SIDEBAR: ΒΑΘΜΟΛΟΓΙΑ ---
st.sidebar.markdown(f"### 🏆 Βαθμολογία {sel_league_name}")
standings_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_league_code}/standings")
if standings_data:
    table = []
    for entry in standings_data.get('standings', [{}])[0].get('table', []):
        table.append({
            "Pos": entry['position'],
            "Team": entry['team']['shortName'],
            "Pts": entry['points']
        })
    st.sidebar.table(pd.DataFrame(table).set_index('Pos'))

# --- ΚΥΡΙΟ ΠΑΝΕΛ: ΑΓΩΝΕΣ ---
today = datetime.utcnow().strftime('%Y-%m-%d')
end_year = "2026-12-31"

url = f"https://api.football-data.org/v4/competitions/{sel_league_code}/matches?dateFrom={today}&dateTo={end_year}"
data = fetch_data(url)
all_matches = data.get('matches', [])
upcoming = [m for m in all_matches if m['status'] == 'SCHEDULED'][:15]

if upcoming:
    for m in upcoming:
        h_team = m['homeTeam']['name']
        a_team = m['awayTeam']['name']
        h_id = m['homeTeam']['id']
        a_id = m['awayTeam']['id']
        match_date = m['utcDate'][:10]
        
        p1, px, p2, pgg, po15, po25 = calc_all(1.7, 1.2)
        
        if top_picks and not (p1 > 0.7 or p2 > 0.7 or po25 > 0.7): continue

        with st.expander(f"📅 {match_date} | {h_team} vs {a_team}"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Άσσος (1)", f"{round(p1*100)}%")
            c2.metric("Ισοπαλία (X)", f"{round(px*100)}%")
            c3.metric("Διπλό (2)", f"{round(p2*100)}%")
            
            c4, c5, c6 = st.columns(3)
            c4.metric("Goal/Goal", f"{round(pgg*100)}%")
            c5.metric("Over 1.5", f"{round(po15*100)}%")
            c6.metric("Over 2.5", f"{round(po25*100)}%")
            
            st.divider()
            st.subheader("📊 Τελευταία 5 Ματς & Αποτελέσματα")
            col_h, col_a = st.columns(2)
            
            h_data = fetch_data(f"https://api.football-data.org/v4/teams/{h_id}/matches?status=FINISHED&limit=10")
            f_h, d_h = get_form_string(h_team, h_data.get('matches', []))
            
            a_data = fetch_data(f"https://api.football-data.org/v4/teams/{a_id}/matches?status=FINISHED&limit=10")
            f_a, d_a = get_form_string(a_team, a_data.get('matches', []))
            
            with col_h:
                st.write(f"🏠 **{h_team}**")
                st.markdown(f"### {f_h}")
                for d in d_h: st.caption(d)
            
            with col_a:
                st.write(f"🚀 **{a_team}**")
                st.markdown(f"### {f_a}")
                for d in d_a: st.caption(d)
else:
    st.info("Δεν βρέθηκαν προγραμματισμένοι αγώνες σύντομα.")
