import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="My AI Betting App", layout="wide")

st.title("⚽ Τα Προγνωστικά μου")

def load_data():
    conn = sqlite3.connect('betting_app.db')
    df = pd.read_sql_query("SELECT * FROM matches", conn)
    conn.close()
    return df

data = load_data()

if data.empty:
    st.warning("Η βάση δεδομένων είναι άδεια. Περίμενε να τρέξει ο data_fetcher!")
else:
    st.write("### Λίστα Αγώνων από τη Βάση")
    st.dataframe(data)

