import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="Pro Football Predictor", layout="wide")

# --- ΡΥΘΜΙΣΕΙΣ API ---
API_KEY =a1a4edf072dc4b2c8153fced44c88de9
LEAGUES = {'PL': 'Premier League', 'PD': 'La Liga', 'SA': 'Serie A', 'BL1': 'Bundesliga'}

@st.cache_data(ttl=3600) # Αποθήκευση δεδομένων για 1 ώρα για ταχύτητα
def fetch_live_data():
    all_matches = []
    headers = {'X-Auth-Token': API_KEY}
    for code, name in LEAGUES.items():
        url = f"https://api.football-data.org/v4/competitions/{code}/matches"
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                for m in data.get('matches', []):
                    all_matches.append({
                        'date': m['utcDate'],
                        'league': name,
                        'home': m['homeTeam']['name'],
                        'away': m['awayTeam']['name']
                    })
        except: continue
    return pd.DataFrame(all_matches)

def calc_probs(h_l, a_l):
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2 = 1 - p1 - px
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    return p1, px, p2, pgg

# --- ΚΥΡΙΟ APP ---
st.title("⚽ Live Football Predictor")

if not API_KEY or API_KEY == "ΤΟ_API_KEY_ΣΟΥ":
    st.error("Πρέπει να βάλεις το API KEY στα Secrets του Streamlit!")
else:
    df = fetch_live_data()
    
    if not df.empty:
        df['date_dt'] = pd.to_datetime(df['date'])
        now = datetime.utcnow()
        
        # Φιλτράρισμα: Μόνο μελλοντικά ματς (επόμενες 3 μέρες)
        future_df = df[(df['date_dt'] > now) & (df['date_dt'] < now + timedelta(days=3))].sort_values('date_dt')
        
        st.sidebar.header("📍 Φίλτρα")
        sel_league = st.sidebar.selectbox("Πρωτάθλημα:", ["Όλα"] + list(LEAGUES.values()))
        top_picks = st.sidebar.toggle("🔥 Μόνο TOP PICKS (>70%)")

        if sel_league != "Όλα":
            future_df = future_df[future_df['league'] == sel_league]

        for _, row in future_df.iterrows():
            # Χρησιμοποιούμε default 1.5/1.2 αφού δεν έχουμε ιστορικά εδώ
            p1, px, p2, pgg = calc_probs(1.6, 1.3) 
            
            if top_picks and not any(p > 0.7 for p in [p1, p2, pgg]):
                continue
                
            gr_time = (row['date_dt'] + timedelta(hours=2)).strftime('%d/%m | %H:%M')
            with st.expander(f"⏰ {gr_time} - {row['home']} vs {row['away']} ({row['league']})"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Άσσος", f"{round(p1*100)}%", delta="TOP" if p1 > 0.7 else None)
                c2.metric("Ισοπαλία", f"{round(px*100)}%")
                c3.metric("Διπλό", f"{round(p2*100)}%", delta="TOP" if p2 > 0.7 else None)
                c4.metric("Goal-Goal", f"{round(pgg*100)}%")
    else:
        st.info("Φόρτωση δεδομένων... Αν αργεί, το API έχει πιάσει το όριο.")
