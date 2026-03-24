import streamlit as st
import sqlite3
import pandas as pd
from scipy.stats import poisson

st.set_page_config(page_title="Pro Football Predictor", layout="wide")
st.title("⚽ Live Football Predictions & Value Finder")

try:
    conn = sqlite3.connect('betting_app.db')
    df = pd.read_sql_query("SELECT * FROM matches", conn)
    conn.close()

    if not df.empty:
        st.sidebar.header("🔍 Φίλτρα")
        teams = sorted(list(set(df['home_team'].tolist() + df['away_team'].tolist())))
        selected_team = st.sidebar.selectbox("Διάλεξε Ομάδα:", ["Όλες"] + teams)

        display_df = df.copy()
        if selected_team != "Όλες":
            display_df = df[(df['home_team'] == selected_team) | (df['away_team'] == selected_team)]

        for index, row in display_df.iterrows():
            with st.expander(f"📅 {row['home_team']} vs {row['away_team']}"):
                h_lambda = row.get('home_exp_goals', 1.5) 
                a_lambda = row.get('away_exp_goals', 1.2)

                # Πραγματικοί υπολογισμοί Poisson
                prob_1 = sum([poisson.pmf(i, h_lambda) * sum([poisson.pmf(j, a_lambda) for j in range(i)]) for i in range(1, 10)])
                prob_x = sum([poisson.pmf(i, h_lambda) * poisson.pmf(i, a_lambda) for i in range(10)])
                prob_2 = 1 - prob_1 - prob_x
                prob_over_25 = 1 - sum([poisson.pmf(i, h_lambda + a_lambda) for i in range(3)])

                col1, col2, col3, col4 = st.columns(4)
                
                # Λειτουργία Alert (Πράσινο αν είναι > 70%)
                def get_delta(prob):
                    return "VALUE" if prob > 0.70 else None

                col1.metric("Άσσος (1)", f"{round(prob_1*100, 1)}%", delta=get_delta(prob_1))
                col2.metric("Ισοπαλία (X)", f"{round(prob_x*100, 1)}%", delta=get_delta(prob_x))
                col3.metric("Διπλό (2)", f"{round(prob_2*100, 1)}%", delta=get_delta(prob_2))
                col4.metric("Over 2.5", f"{round(prob_over_25*100, 1)}%", delta=get_delta(prob_over_25))

        st.subheader("📝 Πίνακας Δεδομένων")
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("Η βάση είναι άδεια!")

except Exception as e:
    st.error(f"Σφάλμα: {e}")

