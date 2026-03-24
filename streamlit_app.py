import streamlit as st
import sqlite3
import pandas as pd
from scipy.stats import poisson
from datetime import datetime, timedelta

st.set_page_config(page_title="Pro Football Predictor", layout="wide")
st.title("⚽ Live Football Predictions")

try:
    conn = sqlite3.connect('betting_app.db')
    df = pd.read_sql_query("SELECT * FROM matches", conn)
    conn.close()

    if not df.empty:
        st.sidebar.header("📍 Επιλογές")
        
        # 1. Φίλτρο Πρωταθλήματος (Τώρα θα έχει Premier, La Liga κλπ)
        leagues = sorted(df['league'].unique().tolist()) if 'league' in df.columns else ["Premier League"]
        selected_league = st.sidebar.selectbox("Επίλεξε Πρωτάθλημα:", ["Όλα"] + leagues)

        # Φιλτράρισμα
        display_df = df.copy()
        if selected_league != "Όλα":
            display_df = df[df['league'] == selected_league]

        for index, row in display_df.iterrows():
            # --- Διαχείριση Ημερομηνίας & Ώρας Ελλάδος ---
            raw_date = row.get('date', 'N/A')
            try:
                # Μετατροπή σε ώρα Ελλάδος (+2 ώρες από το UTC του API)
                date_obj = datetime.strptime(raw_date, '%Y-%m-%d %H:%M:%S')
                greek_time = date_obj + timedelta(hours=2)
                display_date = greek_time.strftime('%d/%m/%Y %H:%M')
            except:
                display_date = raw_date

            with st.expander(f"⏰ {display_date} | {row['home_team']} vs {row['away_team']}"):
                # Χρησιμοποιούμε τα γκολ από τη βάση ή 1.5/1.2 ως default αν είναι κενά
                h_lambda = float(row['home_goals']) if row['home_goals'] is not None else 1.5
                a_lambda = float(row['away_goals']) if row['away_goals'] is not None else 1.2

                # --- Υπολογισμοί Poisson ---
                prob_1 = sum([poisson.pmf(i, h_lambda) * sum([poisson.pmf(j, a_lambda) for j in range(i)]) for i in range(1, 10)])
                prob_x = sum([poisson.pmf(i, h_lambda) * poisson.pmf(i, a_lambda) for i in range(10)])
                prob_2 = 1 - prob_1 - prob_x
                
                prob_over_15 = 1 - sum([poisson.pmf(i, h_lambda + a_lambda) for i in range(2)])
                prob_over_25 = 1 - sum([poisson.pmf(i, h_lambda + a_lambda) for i in range(3)])
                prob_gg = (1 - poisson.pmf(0, h_lambda)) * (1 - poisson.pmf(0, a_lambda))

                # Εμφάνιση Metrics
                c1, c2, c3 = st.columns(3)
                c1.metric("Άσσος (1)", f"{round(prob_1*100, 1)}%")
                c2.metric("Ισοπαλία (X)", f"{round(prob_x*100, 1)}%")
                c3.metric("Διπλό (2)", f"{round(prob_2*100, 1)}%")

                c4, c5, c6 = st.columns(3)
                c4.metric("Goal-Goal", f"{round(prob_gg*100, 1)}%")
                c5.metric("Over 1.5", f"{round(prob_over_15*100, 1)}%")
                c6.metric("Over 2.5", f"{round(prob_over_25*100, 1)}%")

        st.subheader("📊 Πίνακας Δεδομένων")
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("Η βάση ενημερώθηκε αλλά είναι ακόμα άδεια. Περίμενε 1-2 λεπτά.")

except Exception as e:
    st.error(f"Σφάλμα: {e}")
