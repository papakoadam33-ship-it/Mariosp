import streamlit as st
import requests
from scipy.stats import poisson

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

st.title("⚽ Pro Football Predictor")
sel_league_name = st.sidebar.selectbox("Επίλεξε Πρωτάθλημα:", list(LEAGUES.values()))
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# Τραβάμε ΜΟΝΟ τους αγώνες - Χωρίς ημερομηνίες για να μη μπερδεύεται
data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = data.get('matches', [])

# Διαχωρισμός: Πρώτα τα μελλοντικά, αν δεν έχει, τότε τα τελειωμένα
upcoming = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED', 'LIVE']]
if not upcoming:
    st.info("Δεν υπάρχουν μελλοντικά ματς. Εμφάνιση τελευταίων αποτελεσμάτων:")
    display_matches = [m for m in all_m if m['status'] == 'FINISHED'][-10:]
else:
    display_matches = upcoming[:15]

for m in display_matches:
    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    date = m['utcDate'][:10]
    
    # Σταθερές τιμές για τις προβλέψεις (αφού το δωρεάν API δεν δίνει goalsScored εύκολα)
    p1, px, p2, pgg, po15, po25 = calc_all(1.6, 1.2)

    with st.expander(f"⭐ {date} | {h_t} vs {a_t}"):
        c = st.columns(6)
        c[0].metric("1", f"{round(p1*100)}%")
        c[1].metric("X", f"{round(px*100)}%")
        c[2].metric("2", f"{round(p2*100)}%")
        c[3].metric("GG", f"{round(pgg*100)}%")
        c[4].metric("O1.5", f"{round(po15*100)}%")
        c[5].metric("O2.5", f"{round(po25*100)}%")
