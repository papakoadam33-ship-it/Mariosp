import streamlit as st
import sqlite3
import pandas as pd
from scipy.stats import poisson  # Εδώ είναι το μυστικό, με δύο s!

st.set_page_config(page_title="Pro Bet Predictor", layout="wide")

st.title("⚽ Football Prediction Dashboard")

try:
    conn = sqlite3.connect('betting_app.db')
    df = pd.read_sql_query("SELECT * FROM matches", conn)
    conn.close()

    st.sidebar.header("🔍 Φίλτρα")
    teams = sorted(list(set(df['home_team'].tolist() + df['away_team'].tolist())))
    sel_team = st.sidebar.selectbox("Ομάδα:", ["Όλες"] + teams)

    if sel_team != "Όλες":
        df = df[(df['home_team'] == sel_team) | (df['away_team'] == sel_team)]

    for index, row in df.iterrows():
        with st.expander(f"📅 {row['home_team']} vs {row['away_team']}"):
            c1, c2, c3 = st.columns(3)
            
            # Υπολογισμός Poisson (με δύο s παντού)
            home_goals = 1.5 # Μέσος όρος γκολ
            away_goals = 1.2
            
            prob_1 = round(sum([poisson.pmf(i, home_goals) * sum([poisson.pmf(j, away_goals) for j in range(i)]) for i in range(1, 10)]) * 100, 1)
            prob_x = round(sum([poisson.pmf(i, home_goals) * poisson.pmf(i, away_goals) for i in range(10)]) * 100, 1)
            prob_2 = round(100 - prob_1 - prob_x, 1)

            c1.metric("Πιθανότητα 1", f"{prob_1}%")
            c2.metric("Πιθανότητα Χ", f"{prob_x}%")
            c3.metric("Πιθανότητα 2", f"{prob_2}%")

    st.dataframe(df)

except Exception as e:
    st.error(f"Κάτι πήγε λάθος: {e}")
