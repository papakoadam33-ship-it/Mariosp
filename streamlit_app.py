import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
from datetime import datetime, timedelta

st.set_page_config(page_title="Pro Football Predictor", layout="wide")

# --- ΡΥΘΜΙΣΕΙΣ API ---
API_KEY = "ala4edf072dc4b2c8153fced44c88de9" 

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
    
    # Ζητάμε μόνο αγώνες που πρόκειται να γίνουν (SCHEDULED) 
    # για να αποφύγουμε το Error 400 του Free Tier
    today = datetime.utcnow().strftime('%Y-%m-%d')
    end_date = (datetime.utcnow() + timedelta(days=10)).strftime('%Y-%m-%d')
    
    url = f"https://api.football-data.org/v4/competitions/{league_code}/matches?dateFrom={today}&dateTo={end_date}&status=SCHEDULED"
    
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

# --- KYPIO APP ---
st.title("⚽ Pro Football Predictor")

st.sidebar.header("📍 Φίλτρα")
sel_league_name = st.sidebar.selectbox("Επίλεξε Πρωτάθλημα:", list(LEAGUES.values()))
top_picks = st.sidebar.toggle("🔥 Μόνο TOP PICKS (Value > 70%)")

# Εύρεση κωδικού
sel_league_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

df = fetch_live_data(sel_league_code)

if not df.empty:
    # Διόρθωση σφάλματος ημερομηνίας (κάνει τις ημερομηνίες συγκρίσιμες)
    df['date_dt'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    now = datetime.utcnow()
    
    # Κρατάμε μόνο μελλοντικά ματς (επόμενες 2 μέρες για το κουμπί σου)
    limit = now + timedelta(days=2)
    if top_picks:
        display_df = df[(df['date_dt'] >= now) & (df['date_dt'] <= limit)].sort_values('date_dt')
    else:
        display_df = df[df['date_dt'] >= now].sort_values('date_dt')

    if display_df.empty:
        st.info("Δεν βρέθηκαν προσεχείς αγώνες για αυτές τις ρυθμίσεις.")
    else:
        for _, row in display_df.iterrows():
            # Πρόβλεψη Poisson
            p1, px, p2, pgg, po25 = calc_probs(1.7, 1.2) 
            
            # Αν πατηθεί το κουμπί, δείξε μόνο αν κάποιο σημείο είναι > 70%
            is_val = any(p > 0.7 for p in [p1, p2, po25])
            if top_picks and not is_val:
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
    st.warning("Το API δεν έστειλε δεδομένα. Περίμενε 1 λεπτό και άλλαξε πρωτάθλημα.")
