import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import poisson

st.set_page_config(page_title="Pro Bet Predictor", layout="wide")

# --- ΣΤΥΛ ΚΑΙ ΧΡΩΜΑΤΑ ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Pro Football Predictor & Dashboard")

# --- ΣΥΝΔΕΣΗ ΜΕ ΒΑΣΗ ---
try:
    conn = sqlite3.connect('betting_app.db')
    df = pd.read_sql_query("SELECT * FROM matches", conn)
    conn.close()

    # --- ΦΙΛΤΡΑ ΣΤΗΝ ΠΛΕΥΡΙΚΗ ΜΠΑΡΑ ---
    st.sidebar.header("🔍 Φίλτρα Αναζήτησης")
    all_teams = sorted(list(set(df['home_team'].tolist() + df['away_team'].tolist())))
    selected_team = st.sidebar.selectbox("Διάλεξε Ομάδα:", ["Όλες"] + all_teams)

    if selected_team != "Όλες":
        df = df[(df['home_team'] == selected_team) | (df['away_team'] == selected_team)]

    # --- ΠΡΟΓΝΩΣΤΙΚΑ (Ο αλγόριθμος Poisson) ---
    def calculate_probs(home_goals_avg, away_goals_avg):
        # Απλοποιημένο μοντέλο πρόβλεψης
        home_prob = sum([poisson.pmf(i, home_goals_avg) * sum([poisson.pmf(j, away_goals_avg) for j in range(i)]) for i in range(1, 10)])
        draw_prob = sum([poisson.pmf(i, home_goals_avg) * poisson.pmf(i, away_goals_avg) for i in range(10)])
        away_prob = 1 - home_prob - draw_prob
        return round(home_prob*100, 1), round(draw_prob*100, 1), round(away_prob*100, 1)

    # --- ΕΜΦΑΝΙΣΗ ΑΓΩΝΩΝ ---
    st.subheader(f"📅 Αγώνες: {selected_team if selected_team != 'Όλες' else 'Όλοι'}")
    
    for index, row in df.iterrows():
        with st.expander(f"⚽ {row['home_team']} vs {row['away_team']} ({row['date'][:10]})"):
            col1, col2, col3 = st.columns(3)
            
            # Εδώ βάζουμε τυχαία averages για το παράδειγμα (θα μπορούσες να τα παίρνεις από τα στατιστικά σου)
            p1, px, p2 = calculate_probs(1.6, 1.2) 
            
            col1.metric("Πιθανότητα 1", f"{p1}%")
            col2.metric("Πιθανότητα Χ", f"{px}%")
            col3.metric("Πιθανότητα 2", f"{p2}%")
            
            # Over / Under 2.5 Prediction
            prob_over = round((1 - (poisson.pmf(0, 2.8) + poisson.pmf(1, 2.8) + poisson.pmf(2, 2.8))) * 100, 1)
            st.progress(prob_over / 100, text=f"Πιθανότητα Over 2.5: {prob_over}%")

    st.subheader("📝 Αναλυτικά Δεδομένα")
    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Περίμενε να φορτώσουν τα δεδομένα... {e}")
