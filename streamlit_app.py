import streamlit as st
import sqlite3
import pandas as pd
from scipy.stats import poisson
from datetime import datetime

st.set_page_config(page_title="Ultimate Football Predictor", layout="wide")
st.title("🏆 Pro Betting Dashboard")

try:
    conn = sqlite3.connect('betting_app.db')
    df = pd.read_sql_query("SELECT * FROM matches", conn)
    conn.close()

    if not df.empty:
        # --- Sidebar Φίλτρα ---
        st.sidebar.header("📍 Επιλογές")
        
        # 1. Φίλτρο Πρωταθλήματος
        leagues = sorted(df['league'].unique().tolist()) if 'league' in df.columns else ["Δεν βρέθηκαν"]
        selected_league = st.sidebar.selectbox("Επίλεξε Πρωτάθλημα:", ["Όλα"] + leagues)

        # 2. Φίλτρο Ομάδας
        all_teams = sorted(list(set(df['home_team'].tolist() + df['away_team'].tolist())))
        selected_team = st.sidebar.selectbox("Επίλεξε Ομάδα:", ["Όλες"] + all_teams)

        # Φιλτράρισμα δεδομένων
        mask = pd.Series([True] * len(df))
        if selected_league != "Όλα":
            mask &= (df['league'] == selected_league)
        if selected_team != "Όλες":
            mask &= ((df['home_team'] == selected_team) | (df['away_team'] == selected_team))
        
        filtered_df = df[mask]

        for index, row in filtered_df.iterrows():
            # Διαχείριση ώρας (Μετατροπή σε ώρα Ελλάδος αν χρειάζεται)
            match_time = row.get('match_date', 'N/A')
            
            with st.expander(f"⏰ {match_time} | {row['home_team']} vs {row['away_team']} ({row.get('league', 'Ligue')})"):
                h_lambda = row.get('home_exp_goals', 1.5) 
                a_lambda = row.get('away_exp_goals', 1.2)

                # --- Υπολογισμοί Poisson ---
                # 1-X-2
                prob_1 = sum([poisson.pmf(i, h_lambda) * sum([poisson.pmf(j, a_lambda) for j in range(i)]) for i in range(1, 10)])
                prob_x = sum([poisson.pmf(i, h_lambda) * poisson.pmf(i, a_lambda) for i in range(10)])
                prob_2 = 1 - prob_1 - prob_x
                
                # Over 1.5 & Over 2.5
                prob_over_15 = 1 - sum([poisson.pmf(i, h_lambda + a_lambda) for i in range(2)])
                prob_over_25 = 1 - sum([poisson.pmf(i, h_lambda + a_lambda) for i in range(3)])
                
                # Goal-Goal (Πιθανότητα να ΜΗΝ βάλει καμία ομάδα 0 γκολ)
                prob_gg = (1 - poisson.pmf(0, h_lambda)) * (1 - poisson.pmf(0, a_lambda))

                # --- Εμφάνιση Metrics ---
                c1, c2, c3 = st.columns(3)
                c1.metric("Άσσος (1)", f"{round(prob_1*100, 1)}%")
                c2.metric("Ισοπαλία (X)", f"{round(prob_x*100, 1)}%")
                c3.metric("Διπλό (2)", f"{round(prob_2*100, 1)}%")

                c4, c5, c6 = st.columns(3)
                c4.metric("Goal-Goal", f"{round(prob_gg*100, 1)}%")
                c5.metric("Over 1.5", f"{round(prob_over_15*100, 1)}%")
                c6.metric("Over 2.5", f"{round(prob_over_25*100, 1)}%")

        st.subheader("📊 Αναλυτικά Στοιχεία")
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.warning("Δεν υπάρχουν αγώνες στη βάση.")

except Exception as e:
    st.error(f"Σφάλμα: {e}")


