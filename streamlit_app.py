import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

st.set_page_config(page_title="Pro Football Predictor LIVE", layout="wide")

API_KEY = "a963742bcd5642afbe8c842d057f25ad" 

LEAGUES = {'PL':'Premier League','PD':'La Liga','BL1':'Bundesliga','SA':'Serie A','FL1':'Ligue 1','CL':'Champions League','DED':'Eredivisie','ELC':'Championship'}

@st.cache_data(ttl=60) # Μικρότερο TTL για φρεσκάρισμα στο Live
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except: return {}

def get_advanced_stats(matches, team_name, standings):
    if not matches: return 1.2
    total_goals = 0
    ranks = {t['team']['name']: t['position'] for t in standings} if standings else {}
    current_rank = ranks.get(team_name, 10)
    quality_bonus = (21 - current_rank) / 20 
    valid_matches = 0
    for m in matches:
        score = m.get('score', {}).get('fullTime', {})
        if score.get('home') is not None:
            is_h = m['homeTeam']['name'] == team_name
            total_goals += score.get('home') if is_h else score.get('away')
            valid_matches += 1
    avg_goals = total_goals / valid_matches if valid_matches > 0 else 1.2
    return max(0.5, (avg_goals * 0.6) + (quality_bonus * 0.4)) 

def calc_live_probs(h_l, a_l, current_h, current_a, status):
    # Υπολογισμός εναπομείναντα χρόνου (χονδρικά)
    rem_time_factor = 1.0
    if status == 'IN_PLAY': rem_time_factor = 0.5 # Αν δεν έχουμε ακριβές λεπτό, υποθέτουμε ημίχρονο
    
    h_l_rem, a_l_rem = h_l * rem_time_factor, a_l * rem_time_factor
    
    # Πιθανότητες για τα γκολ που ΑΠΟΜΕΝΟΥΝ
    p_more_0 = 1 - poisson.pmf(0, h_l_rem + a_l_rem)
    p_more_1 = 1 - sum([poisson.pmf(i, h_l_rem + a_l_rem) for i in range(2)])
    
    # 1X2 Πιθανότητες (βασισμένες στο τρέχον σκορ + Poisson για τα υπόλοιπα)
    # Απλοποιημένο μοντέλο για Live
    p1 = 0.7 if current_h > current_a else (0.1 if current_a > current_h else 0.3)
    px = 0.2
    p2 = 1 - p1 - px
    
    return p1, px, p2, p_more_0, p_more_1

# --- SIDEBAR ---
st.sidebar.title("📍 LIVE Control")
sel_league_name = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_list = st_data.get('standings', [{}])[0].get('table', []) if st_data else []

# --- MAIN ---
st.title(f"⚽ Live Analysis: {sel_league_name}")
all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = all_data.get('matches', [])
# Φιλτράρουμε για να δείχνει πρώτα τα Live και μετά τα επόμενα
live_m = [m for m in all_m if m['status'] in ['IN_PLAY', 'PAUSED', 'LIVE']]
upcoming_m = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED']][:10]
display_m = live_m + upcoming_m

for m in display_m:
    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    status = m['status']
    score = m.get('score', {}).get('fullTime', {})
    cur_h, cur_a = score.get('home', 0), score.get('away', 0)
    total_cur = cur_h + cur_a
    
    # Header display
    if status in ['IN_PLAY', 'PAUSED']:
        title = f"🔴 LIVE: {h_t} {cur_h} - {cur_a} {a_t}"
    else:
        title = f"📅 {m['utcDate'][:10]} | {h_t} vs {a_t}"

    h_f_data = fetch_data(f"https://api.football-data.org/v4/teams/{m['homeTeam']['id']}/matches?status=FINISHED&limit=5&competitions={sel_code}")
    a_f_data = fetch_data(f"https://api.football-data.org/v4/teams/{m['awayTeam']['id']}/matches?status=FINISHED&limit=5&competitions={sel_code}")
    
    h_l = get_advanced_stats(h_f_data.get('matches', []), h_t, standings_list)
    a_l = get_advanced_stats(a_f_data.get('matches', []), a_t, standings_list)
    
    p1, px, p2, pgg, po15, po25 = 0,0,0,0,0,0
    
    with st.expander(title):
        if status in ['IN_PLAY', 'PAUSED']:
            # Live Logic
            p1, px, p2, p_rem_1, p_rem_2 = calc_live_probs(h_l, a_l, cur_h, cur_a, status)
            cols = st.columns(6)
            cols[0].metric("1", "LIVE")
            cols[1].metric("X", "LIVE")
            cols[2].metric("2", "LIVE")
            
            # Έλεγχος για Over 1.5
            if total_cur < 1.5:
                cols[4].metric("O1.5", f"{round(p_rem_1*100)}%")
            else:
                cols[4].write("✅ O1.5")
            
            # Έλεγχος για Over 2.5
            if total_cur < 2.5:
                # Υπολογίζουμε πόσα γκολ λείπουν
                needed = 2.5 - total_cur
                cols[5].metric("O2.5", "🔥" if p_rem_1 > 0.6 else "⏳")
            else:
                cols[5].write("✅ O2.5")
        else:
            # Pre-match Logic (όπως πριν)
            p1, px, p2, pgg, po15, po25 = 0.3, 0.3, 0.4, 0.5, 0.6, 0.4 # Placeholder για ταχύτητα
            # (Εδώ τρέχεις το κανονικό calc_all)
