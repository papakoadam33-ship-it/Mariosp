import streamlit as st
import sqlite3
import pandas as pd
from scipy.stats import poisson

st.set_page_config(page_title="Football Predictor", layout="wide")
st.title("⚽ Live Football Predictions")

try:
    conn = sqlite3.connect('betting_app.db')
    df = pd.read_sql_query("SELECT * FROM matches", conn)
    conn.close()

    if not df.empty:
        # Διόρθωση: Αν δεν υπάρχει στήλη 'league', τη δημιουργούμε προσωρινά
        if 'league' not in df.columns:
            df['league'] = "Premier League" # Ή όποιο πρωτάθλημα κατεβάζεις

        st.sidebar.header("🔍 Φίλτρα")
        
        # Φίλτρο Πρωταθλήματος
        leagues = sorted(df['league'].unique().tolist())
        selected_league = st.sidebar.selectbox("Επίλεξε Πρωτάθλημα:", ["Όλα"] + leagues)

        # Φιλτράρισμα
        display_df = df.copy()
        if selected_league != "Όλα":
            display_df = df[df['league'] == selected_league]

        for index, row in display_df.iterrows():
            # Χρήση της στήλης 'date' που μου είπες
            match_date = row.get('date', 'N/A')
            
            # Αν η ημερομηνία είναι πολύ μεγάλη (π.χ. 2024-05-12T15:00:00Z), την ομορφαίνουμε
            clean_date = str(match_date).replace('T', ' ').replace('Z', '')

            with st.expander(f"📅 {clean_date} | {row['home_team']} vs {row['away_team']}"):
                h_lambda = row.get('home_exp_goals', 1.5) 
                a_lambda = row.get('away_exp_goals', 1.2)

                # Υπολογισμοί
                prob_1 = sum([poisson.pmf(i, h_lambda) * sum([poisson.pmf(j, a_lambda) for j in range(i)]) for i in range(1, 10)])
                prob_x = sum([poisson.pmf(i, h_lambda) * poisson.pmf(i, a_lambda) for i in range(10)])
                prob_2 = 1 - prob_1 - prob_x
                prob_over_15 = 1 - sum([poisson.pmf(i, h_lambda + a_lambda) for i in range(2)])
                prob_over_25 = 1 - sum([poisson.pmf(i, h_lambda + a_lambda) for i in range(3)])
                prob_gg = (1 - poisson.pmf(0, h_lambda)) * (1 - poisson.pmf(0, a_lambda))

                c1, c2, c3 = st.columns(3)
                c1.metric("Άσσος (1)", f"{round(prob_1*100, 1)}%")
                c2.metric("Ισοπαλία (X)", f"{round(prob_x*100, 1)}%")
                c3.metric("Διπλό (2)", f"{round(prob_2*100, 1)}%")

                c4, c5, c6 = st.columns(3)
                c4.metric("Goal-Goal", f"{round(prob_gg*100, 1)}%")
                c5.metric("Over 1.5", f"{round(prob_over_15*100, 1)}%")
                c6.metric("Over 2.5", f"{round(prob_over_25*100, 1)}%")

        st.subheader("📝 Πίνακας Δεδομένων")
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("Η βάση είναι άδεια!")

except Exception as e:
    st.error(f"Σφάλμα: {e}")
