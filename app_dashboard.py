import streamlit as st
import pandas as pd
import sqlite3
import os

st.set_page_config(page_title="My AI Betting App", layout="wide")
st.title("⚽ Τα Προγνωστικά μου")

def load_data():
    db_path = 'betting_app.db'
    # Ελέγχουμε αν υπάρχει το αρχείο της βάσης
    if not os.path.exists(db_path):
        return pd.DataFrame() 
    
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query("SELECT * FROM matches", conn)
    except:
        # Αν ο πίνακας δεν υπάρχει ακόμα
        df = pd.DataFrame()
    conn.close()
    return df

data = load_data()

if data.empty:
    st.warning("⚠️ Η βάση δεδομένων είναι προσωρινά άδεια. Παρακαλώ τρέξτε το 'Run workflow' στο GitHub Actions και περιμένετε 1 λεπτό!")
else:
    st.success(f"Βρέθηκαν {len(data)} αγώνες!")
    st.dataframe(data)
