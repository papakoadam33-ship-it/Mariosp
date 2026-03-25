import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
from datetime import datetime

st.set_page_config(page_title="Pro Predictor", layout="wide")

# --- API CONFIG ---
API_KEY = "a963742bcd5642afbe8c842d057f25ad" # <--- ΒΑΛΕ ΤΟ ΚΛΕΙΔΙ ΣΟΥ

LEAGUES = {
    'PL': 'Premier League',
    'PD': 'La Liga',
    'BL1': 'Bundesliga',
    'SA': 'Serie A',
    'FL1': 'Ligue 1',
    'PPL': 'Primeira Liga'
}

@st.cache_data(ttl=600)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except: pass
    return {}

def get_form(team_name, matches):
    if not matches: return "N/A", []
    f, d = [], []
    for m in matches:
        if m.get('status') != 'FINISHED': continue
        is_h = m['homeTeam']['name'] == team_name
        opp = m['awayTeam']['name'] if is_h else m['homeTeam']['name']
        score = m.get('score', {}).get('fullTime', {})
        hg, ag = score.get('home'), score.get('away')
        if hg is None: continue
        if hg == ag: icon, txt = "🟡", f"Ισοπαλία {hg}-{ag} με {opp}"
        elif (is_h and hg > ag) or (not is_h and ag > hg): icon, txt = "🟢", f"Νίκη {hg}-{ag} με {opp}"
        else: icon, txt = "🔴", f"Ήττα {hg}-{ag} με {opp}"
        f.append(icon); d.append(txt)
        if len(f) == 5: break
    return "".join(f), d

def calc_all(h_l, a_l):
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po15 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(2)])
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])
    return p1, px, p2, pgg, po15, po25

# --- UI ---
st.title("⚽ Pro Football Predictor")
sel_league_name = st.sidebar.selectbox("Επίλεξε Πρωτάθλημα:", list(LEAGUES.values()))
top_picks = st.sidebar.toggle("🔥 TOP PICKS (>70%)")
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# Τραβάμε ΜΟΝΟ αγώνες για να είναι γρήγορο
data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = data.get('matches', [])
upcoming = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED', 'LIVE']]

if not upcoming:
    st.info(f"📅 Δεν υπάρχουν live/μελλοντικά ματς στην {sel_league_name}. Εμφάνιση πρόσφατων:")
    upcoming = [m for m in all_m if m['status'] == 'FINISHED'][-8:]
else:
    upcoming = upcoming[:15]

for m in upcoming:
    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    h_id, a_id = m['homeTeam']['id'], m['awayTeam']['id']
    date = m['utcDate'][:10]
    
    p1, px, p2, pgg, po15, po25 = calc_all(1.7, 1.2)
    if top_picks and not (p1 > 0.7 or p2 > 0.7 or po25 > 0.7): continue

    with st.expander(f"⭐ {date} | {h_t} vs {a_t}"):
        cols = st.columns(6)
        cols[0].metric("1", f"{round(p1*100)}%")
        cols[1].metric("X", f"{round(px*100)}%")
        cols[2].metric("2", f"{round(p2*100)}%")
        cols[3].metric("GG", f"{round(pgg*100)}%")
        cols[4].metric("O1.5", f"{round(po15*100)}%")
        cols[5].metric("O2.5", f"{round(po25*100)}%")
        
        st.divider()
        c_h, c_a = st.columns(2)
        # Φέρνουμε φόρμα ΜΟΝΟ αν ανοίξει ο χρήστης το expander
        h_data = fetch_data(f"https://api.football-data.org/v4/teams/{h_id}/matches?status=FINISHED&limit=8")
        a_data = fetch_data(f"https://api.football-data.org/v4/teams/{a_id}/matches?status=FINISHED&limit=8")
        f_h, d_h = get_form(h_t, h_data.get('matches', []))
        f_a, d_a = get_form(a_t, a_data.get('matches', []))
        
        with c_h:
            st.write(f"🏠 **{h_t}**"); st.subheader(f_h)
            for d in d_h: st.caption(d)
        with c_a:
            st.write(f"🚀 **{a_t}**"); st.subheader(f_a)
            for d in d_a: st.caption(d)
