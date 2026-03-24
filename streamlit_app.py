import streamlit as st
import sqlite3
import pandas as pd
from scipy.stats import poisson
from datetime import datetime, timedelta

st.set_page_config(page_title="Pro Football Predictor", layout="wide")

# --- ΣΥΝΑΡΤΗΣΗ ΥΠΟΛΟΓΙΣΜΟΥ ---
def calculate_probs(h_lambda, a_lambda):
    h_lambda = h_lambda if h_lambda is not None else 1.5
    a_lambda = a_lambda if a_lambda is not None else 1.2
    
    p1 = sum([poisson.pmf(i, h_lambda) * sum([poisson.pmf(j, a_lambda) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_lambda) * poisson.pmf(i, a_lambda) for i in range(10)])
    p2 = 1 - p1 - px
    p_gg = (1 - poisson.pmf(0, h_lambda)) * (1 - poisson.pmf(0, a_lambda))
    po25 = 1 - sum([poisson.pmf(i, h_lambda + a_lambda) for i in range(3)])
    return p1, px, p2, p_gg, po25

# --- ΦΟΡΤΩΣΗ ΔΕΔΟΜΕΝΩΝ ---
try:
    conn = sqlite3.connect('betting_new.db')
    df = pd.read_sql_query("SELECT * FROM matches", conn)
    conn.close()

    if not df.empty:
        # Μετατροπή ημερομηνίας και φιλτράρισμα για ΜΕΛΛΟΝΤΙΚΑ ματς
        df['date_dt'] = pd.to_datetime(df['date'])
        now_utc = datetime.utcnow()
        # Κρατάμε μόνο αγώνες που δεν έχουν ξεκινήσει ακόμα
        df = df[df['date_dt'] > now_utc].sort_values('date_dt')

        st.title("⚽ Live Football Predictions")
        
        # --- SIDEBAR & TOP PICKS ---
        st.sidebar.header("🔥 Στρατηγική")
        top_picks_only = st.sidebar.toggle("Δείξε μόνο TOP PICKS (Value > 70%)")
        
        leagues = sorted(df['league'].unique().tolist()) if 'league' in df.columns else []
        selected_league = st.sidebar.selectbox("Πρωτάθλημα:", ["Όλα"] + leagues)

        # Φιλτράρισμα βάσει επιλογών
        display_df = df.copy()
        if selected_league != "Όλα":
            display_df = display_df[display_df['league'] == selected_league]
        
        # Περιορισμός σε αγώνες των επόμενων 48 ωρών για το κουμπί
        if top_picks_only:
            limit_date = now_utc + timedelta(days=2)
            display_df = display_df[display_df['date_dt'] <= limit_date]

        for index, row in display_df.iterrows():
            p1, px, p2, pgg, po25 = calculate_probs(row.get('home_goals'), row.get('away_goals'))
            
            # Έλεγχος αν υπάρχει κάποια πρόβλεψη πάνω από 70%
            is_value = any(p > 0.70 for p in [p1, p2, pgg, po25])
            
            if top_picks_only and not is_value:
                continue

            # Ώρα Ελλάδος
            gr_time = (row['date_dt'] + timedelta(hours=2)).strftime('%d/%m | %H:%M')

            with st.expander(f"📅 {gr_time} - {row['home_team']} vs {row['away_team']}"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Άσσος (1)", f"{round(p1*100,1)}%", delta="TOP" if p1 > 0.7 else None)
                col2.metric("Ισοπαλία (X)", f"{round(px*100,1)}%")
                col3.metric("Διπλό (2)", f"{round(p2*100,1)}%", delta="TOP" if p2 > 0.7 else None)
                
                col4, col5 = st.columns(2)
                col4.metric("Goal-Goal", f"{round(pgg*100,1)}%", delta="VALUE" if pgg > 0.7 else None)
                col5.metric("Over 2.5", f"{round(po25*100,1)}%", delta="VALUE" if po25 > 0.7 else None)

    else:
        st.warning("Δεν βρέθηκαν μελλοντικοί αγώνες στη βάση.")
except Exception as e:
    st.error(f"Σφάλμα: {e}")
