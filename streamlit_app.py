import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Football Data Dashboard", layout="wide")

st.title("⚽ Live Football Data Dashboard")
st.write("Τα δεδομένα ενημερώνονται αυτόματα μέσω GitHub Actions!")

# Σύνδεση με τη βάση δεδομένων
try:
    conn = sqlite3.connect('betting_app.db')
    # Εδώ υποθέτουμε ότι ο πίνακας λέγεται 'matches' (άλλαξέ το αν το έχεις αλλιώς)
    query = "SELECT * FROM matches" 
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Εμφάνιση των δεδομένων
    st.subheader("Πρόσφατοι Αγώνες & Στατιστικά")
    st.dataframe(df, use_container_width=True)
    
    # Ένα απλό γράφημα (παράδειγμα)
    if 'status' in df.columns:
        st.subheader("Κατάσταση Αγώνων")
        st.bar_chart(df['status'].value_counts())

except Exception as e:
    st.error(f"Η βάση δεδομένων δεν βρέθηκε ή είναι άδεια. Περίμενε να τρέξει το πρώτο Update! Σφάλμα: {e}")

st.info("💡 Tip: Μπορείς να προσθέσεις φίλτρα για ομάδες ή ημερομηνίες!")
