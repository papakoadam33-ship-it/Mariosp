import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
from datetime import datetime, timedelta

st.set_page_config(page_title="Pro Football Predictor", layout="wide")

# --- ΡΥΘΜΙΣΕΙΣ API ---
API_KEY = "ala4edf072dc4b2c8153fced44c88de9" 

# Πρωταθλήματα που δουλεύουν σίγουρα στο Free Tier
LEAGUES = {
    'PL': 'Premier League',
    'PD': 'La Liga',
    'BL1': 'Bundesliga',
    'SA': 'Serie A',
    'FL1': 'Ligue 1'
}

@st.cache_data(ttl=600)
def fetch_live_data(league_code):
    headers = {'X-Auth-Token': API_KEY}
    
    # Ζητάμε ΜΟΝΟ τις επόμενες 7 ημέρες για να αποφύγουμε το Error 400
    today = datetime.utcnow().strftime('%Y-%m-%d')
    end_date = (datetime.utcnow() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    url = f"https://api.football-data.org/v4/competitions/{league_code}/matches?dateFrom={today}&dateTo={end_date}"
    
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
        else:
            # Αν αποτύχει, θα μας πει το λόγο
            st.error(f"API Error {res.status_code}. Δοκίμασε σε 1 λεπτό.")
            return pd.DataFrame()
    except:
        return pd.DataFrame()

def calc_probs(h_l, a_l):
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])
    return p1, px, p2, pgg, po25

# --- ΚΥΡΙΟ APP ---
st.title("⚽ Pro Football Predictor")

st.sidebar.header("📍 Ρυθμίσεις")
sel_league_name = st.sidebar.selectbox("Επίλεξε Πρωτάθλημα:", list(LEAGUES.values()))
top_picks = st.sidebar.toggle("🔥 Μόνο TOP PICKS (>70%)")

sel_league_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

df = fetch_live_data(sel_league_code)

if not df.empty:
    # Διόρθωση timezone για να μην κολλάει η σύγκριση
    df['date_dt'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    now = datetime.utcnow()
    
    # Κρατάμε μόνο μελλοντικά ματς
    future_df = df[df['date_dt'] > now].sort_values('date_dt')
    
    if future_df.empty:
        st.info(f"Δεν βρέθηκαν ματς για την {sel_league_name} αυτή την εβδομάδα.")
    else:
        for _, row in future_df.iterrows():
            # Poisson με μέσες τιμές 1.7 - 1.2
            p1, px, p2, pgg, po25 = calc_probs(1.7, 1.2) 
            
            # Φίλτρο Top Picks για Άσσο, Διπλό ή Over 2.5
            if top_picks and not (p1 > 0.7 or p2 > 0.7 or po25 > 0.65):
                continue
                
            gr_time = (row['date_dt'] + timedelta(hours=2)).strftime('%d/%m | %H:%M')
            
            with st.expander(f"⏰ {gr_time} - {row['home']} vs {row['away']}"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Άσσος", f"{round(p1*100)}%", delta="TOP" if p1 > 0.7 else None)
                c2.metric("Ισοπαλία", f"{round(px*100)}%")
                c3.metric("Διπλό", f"{round(p2*100)}%", delta="TOP" if p2 > 0.7 else None)
                
                c4, c5 = st.columns(2)
                c4.metric("Goal-Goal", f"{round(pgg*100)}%")
                c5.metric("Over 2.5", f"{round(po25*100)}%", delta="VALUE" if po25 > 0.65 else None)
else:
    st.warning("Επίλεξε ένα πρωτάθλημα ή περίμενε λίγο για το API.")
