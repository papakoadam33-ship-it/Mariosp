import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
from datetime import datetime, timedelta

st.set_page_config(page_title="Pro Football Predictor", layout="wide")

# --- ΡΥΘΜΙΣΕΙΣ API ---
# Βεβαιώσου ότι το κλειδί σου είναι σωστό (ala4edf072dc4b2c8153fced44c88de9)
API_KEY = "ala4edf072dc4b2c8153fced44c88de9" 

# Τα πρωταθλήματα που υποστηρίζει το δωρεάν πακέτο
LEAGUES = {
    'PL': 'Premier League',
    'PD': 'La Liga',
    'SA': 'Serie A',
    'BL1': 'Bundesliga',
    'FL1': 'Ligue 1',
    'PPL': 'Primeira Liga'
}

@st.cache_data(ttl=600)
def fetch_live_data(league_code):
    headers = {'X-Auth-Token': API_KEY}
    url = f"https://api.football-data.org/v4/competitions/{league_code}/matches"
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            matches = []
            for m in data.get('matches', []):
                matches.append({
                    'date': m['utcDate'],
                    'league': LEAGUES[league_code],
                    'home': m['homeTeam']['name'],
                    'away': m['awayTeam']['name']
                })
            return pd.DataFrame(matches)
        elif res.status_code == 429:
            st.error("⚠️ Το API σε μπλόκαρε προσωρινά. Περίμενε 1 λεπτό χωρίς refresh.")
            return pd.DataFrame()
        else:
            st.error(f"Σφάλμα API: {res.status_code}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Κάτι πήγε στραβά: {e}")
        return pd.DataFrame()

def calc_probs(h_l, a_l):
    # Poisson Distribution για προβλέψεις
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    return p1, px, p2, pgg

# --- ΚΥΡΙΟ APP ---
st.title("⚽ Pro Football Predictor")

# SIDEBAR ΦΙΛΤΡΑ
st.sidebar.header("📍 Ρυθμίσεις")
sel_league_name = st.sidebar.selectbox("Επίλεξε Πρωτάθλημα:", list(LEAGUES.values()))
top_picks = st.sidebar.toggle("🔥 Δείξε μόνο TOP PICKS (>70%)")

# Εύρεση του κωδικού από το όνομα
sel_league_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# Φόρτωση δεδομένων
df = fetch_live_data(sel_league_code)

if not df.empty:
    # Διόρθωση ημερομηνίας
    df['date_dt'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    now = datetime.utcnow()
    
    # Φιλτράρισμα: Μόνο μελλοντικοί αγώνες (επόμενες 3 μέρες)
    future_df = df[(df['date_dt'] > now) & (df['date_dt'] < now + timedelta(days=3))].sort_values('date_dt')
    
    if future_df.empty:
        st.info(f"Δεν υπάρχουν προσεχείς αγώνες για το πρωτάθλημα: {sel_league_name}")
    else:
        for _, row in future_df.iterrows():
            # Default Poisson τιμές (1.6 goals home / 1.3 goals away)
            p1, px, p2, pgg = calc_probs(1.6, 1.3) 
            
            # Αν είναι ενεργό το Top Picks, φίλτραρε
            if top_picks and not any(p > 0.7 for p in [p1, p2, pgg]):
                continue
                
            # Ώρα Ελλάδος (+2)
            gr_time = (row['date_dt'] + timedelta(hours=2)).strftime('%d/%m | %H:%M')
            
            with st.expander(f"⏰ {gr_time} - {row['home']} vs {row['away']}"):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Άσσος", f"{round(p1*100)}%", delta="TOP" if p1 > 0.7 else None)
                col2.metric("Ισοπαλία", f"{round(px*100)}%")
                col3.metric("Διπλό", f"{round(p2*100)}%", delta="TOP" if p2 > 0.7 else None)
                col4.metric("Goal-Goal", f"{round(pgg*100)}%")
else:
    st.info("Επίλεξε ένα πρωτάθλημα από το μενού αριστερά για να ξεκινήσεις.")
