import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
from datetime import datetime, timedelta

st.set_page_config(page_title="Pro Football Predictor PRO", layout="wide")

# --- ΡΥΘΜΙΣΕΙΣ API ---
API_KEY = "a963742bcd5642afbe8c842d057f25ad" # Βάλε το κλειδί που δουλεύει

LEAGUES = {
    'PL': 'Premier League',
    'PD': 'La Liga',
    'BL1': 'Bundesliga',
    'SA': 'Serie A',
    'FL1': 'Ligue 1',
    'PPL': 'Primeira Liga'
}

def get_form_string(team_name, matches):
    form = []
    details = []
    for m in matches:
        if m['status'] != 'FINISHED': continue
        is_home = m['homeTeam']['name'] == team_name
        opp = m['awayTeam']['name'] if is_home else m['homeTeam']['name']
        res = m['score']['fullTime']
        h_g, a_g = res['home'], res['away']
        
        if h_g is None or a_g is None: continue
        
        # Result logic
        if h_g == a_g: 
            icon, txt = "🟡", f"Ισοπαλία {h_g}-{a_g} με {opp}"
        elif (is_home and h_g > a_g) or (not is_home and a_g > h_g):
            icon, txt = "🟢", f"Νίκη {h_g}-{a_g} με {opp}"
        else:
            icon, txt = "🔴", f"Ήττα {h_g}-{a_g} με {opp}"
        
        form.append(icon)
        details.append(txt)
        if len(form) == 5: break
    return "".join(form), details

@st.cache_data(ttl=600)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    res = requests.get(url, headers=headers)
    return res.json() if res.status_code == 200 else {}

def calc_all(h_l, a_l):
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po15 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(2)])
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])
    return p1, px, p2, pgg, po15, po25

st.title("⚽ Pro Predictor & Form Tracker")

# SIDEBAR
st.sidebar.header("📍 Επιλογές")
sel_league_name = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
top_picks = st.sidebar.toggle("🔥 TOP PICKS (>70%)")

sel_league_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# Κλήση για αγώνες
data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_league_code}/matches?status=SCHEDULED")
matches = data.get('matches', [])

if matches:
    for m in matches[:10]:
        h_team = m['homeTeam']['name']
        a_team = m['awayTeam']['name']
        h_id = m['homeTeam']['id']
        a_id = m['awayTeam']['id']
        
        # Προβλέψεις (Poisson)
        p1, px, p2, pgg, po15, po25 = calc_all(1.7, 1.2)
        
        if top_picks and not (p1 > 0.7 or p2 > 0.7 or po25 > 0.7): continue

        with st.expander(f"⭐ {h_team} vs {a_team}"):
            # Stats Columns
            c1, c2, c3 = st.columns(3)
            c1.metric("1", f"{round(p1*100)}%")
            c2.metric("X", f"{round(px*100)}%")
            c3.metric("2", f"{round(p2*100)}%")
            
            c4, c5, c6 = st.columns(3)
            c4.metric("G/G", f"{round(pgg*100)}%")
            c5.metric("Over 1.5", f"{round(po15*100)}%")
            c6.metric("Over 2.5", f"{round(po25*100)}%")
            
            st.divider()
            
            # Φόρμα Ομάδων (Χρειάζεται έξτρα κλήση - Προσοχή στο όριο!)
            st.subheader("📊 Τελευταία 5 Ματς")
            col_h, col_a = st.columns(2)
            
            # Εδώ τραβάμε τα αποτελέσματα για κάθε ομάδα
            h_data = fetch_data(f"https://api.football-data.org/v4/teams/{h_id}/matches?status=FINISHED&limit=5")
            a_data = fetch_data(f"https://api.football-data.org/v4/teams/{a_id}/matches?status=FINISHED&limit=5")
            
            f_h, d_h = get_form_string(h_team, h_data.get('matches', []))
            f_a, d_a = get_form_string(a_team, a_data.get('matches', []))
            
            with col_h:
                st.write(f"**{h_team}**")
                st.large_caption(f_h)
                for d in d_h: st.write(f"· {d}")
            
            with col_a:
                st.write(f"**{a_team}**")
                st.large_caption(f_a)
                for d in d_a: st.write(f"· {d}")
else:
    st.info("Δεν βρέθηκαν προσεχείς αγώνες. Δοκίμασε άλλο πρωτάθλημα.")
