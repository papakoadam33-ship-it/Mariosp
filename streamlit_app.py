import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
from datetime import datetime, timedelta

st.set_page_config(page_title="Pro Football Predictor", layout="wide")

# --- ΡΥΘΜΙΣΕΙΣ API ---
API_KEY = "a963742bcd5642afbe8c842d057f25ad"

LEAGUES = {
    'PL': 'Premier League',
    'PD': 'La Liga',
    'BL1': 'Bundesliga',
    'SA': 'Serie A',
    'FL1': 'Ligue 1'
}

# Αφαιρούμε το cache προσωρινά για να βλέπουμε ζωντανά τα λάθη
def fetch_live_data(league_code):
    headers = {'X-Auth-Token': API_KEY}
    # Το πιο απλό URL που υπάρχει
    url = f"https://api.football-data.org/v4/competitions/{league_code}/matches?status=SCHEDULED"
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json().get('matches', [])
        else:
            st.error(f"Σφάλμα από το API: {res.status_code}. Μήνυμα: {res.text}")
            return []
    except Exception as e:
        st.error(f"Σφάλμα σύνδεσης: {e}")
        return []

def calc_probs(h_l, a_l):
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])
    return p1, px, p2, pgg, po25

st.title("⚽ Pro Football Predictor")

sel_league_name = st.sidebar.selectbox("Επίλεξε Πρωτάθλημα:", list(LEAGUES.values()))
sel_league_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

matches = fetch_live_data(sel_league_code)

if matches:
    for m in matches[:15]: # Δείξε τα πρώτα 15 ματς
        home = m['homeTeam']['name']
        away = m['awayTeam']['name']
        date_str = m['utcDate']
        
        # Υπολογισμοί
        p1, px, p2, pgg, po25 = calc_probs(1.7, 1.2)
        
        with st.expander(f"{home} vs {away}"):
            st.write(f"Ημερομηνία: {date_str}")
            c1, c2, c3 = st.columns(3)
            c1.metric("1", f"{round(p1*100)}%")
            c2.metric("X", f"{round(px*100)}%")
            c3.metric("2", f"{round(p2*100)}%")
else:
    st.info("Δεν βρέθηκαν αγώνες. Αν βλέπεις σφάλμα 429, περίμενε 1 λεπτό.")
