import streamlit as st
import sqlite3
import pandas as pd
from scipy.stats import poisson

# Η ρύθμιση σελίδας πρέπει να είναι ΠΡΩΤΗ
st.set_page_config(page_title="Pro Football Predictor", layout="wide")

st.title("⚽ Football Prediction Dashboard")

try:
    conn = sqlite3.connect('betting_app.db')
    df = pd.read_sql_query("SELECT * FROM matches", conn)
    conn.close()

    if not df.empty:
        st.sidebar.header("🔍 Φίλτρα")
        all_teams = sorted(list(set(df['home_team'].tolist() + df['away_team'].tolist())))
        selected_team = st.sidebar.selectbox("Διάλεξε Ομάδα:", ["Όλες"] + all_teams)

        if selected_team != "Όλες":
            df = df[(df['home_team'] == selected_team) | (df['away_team'] == selected_team)]

        for index, row in df.iterrows():
            with st.expander(f"📅 {row['home_team']} vs {row['away_team']}"):
                c1, c2, c3 = st.columns(3)
                # Εδώ υπολογίζουμε μια βασική πρόβλεψη Poisson για 1-X-2
                h_prob = round(poisson.pmf(2, 1.5) * 100, 1)
                c1.metric("Πιθανότητα 1", f"{h_prob}%")
                c2.metric("Πιθανότητα Χ", "25.0%")
                c3.metric("Πιθανότητα 2", "30.0%")
        
        st.subheader("📝 Αναλυτικά Στοιχεία")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Η βάση δεδομένων είναι άδεια. Τρέξε το GitHub Action!")

except Exception as e:
    st.error(f"Σφάλμα: {e}")

