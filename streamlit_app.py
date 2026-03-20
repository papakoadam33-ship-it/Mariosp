import streamlit as st
import sqlite3
import pandas as pd
from scipy.stats import poisson

st.set_page_config(page_title="Football Predictor", layout="wide")

st.title("⚽ My Football App")

try:
    conn = sqlite3.connect('betting_app.db')
    df = pd.read_sql_query("SELECT * FROM matches", conn)
    conn.close()
    
    st.write("Σύνδεση επιτυχής!")
    st.dataframe(df)
    
except Exception as e:
    st.error(f"Κάτι δεν πάει καλά: {e}")
