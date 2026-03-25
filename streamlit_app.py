import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

st.set_page_config(page_title="Pro Football Predictor", layout="wide")

# --- API CONFIG ---
API_KEY ="a963742bcd5642afbe8c842d057f25ad" 

LEAGUES = {'PL':'Premier League','PD':'La Liga', 'BL1':'Bundesliga', 'SA':'Serie A', 'FL1':'Ligue 1'}

@st.cache_data(ttl=300)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except: return {}

# --- ΠΡΟΧΩΡΗΜΕΝΟΣ ΥΠΟΛΟΓΙΣΜΟΣ ΠΙΘΑΝΟΤΗΤΩΝ (STRENGTH FACTOR) ---
def get_advanced_stats(matches, team_name, standings):
    if not matches: return 1.2, 10
    
    total_goals = 0
    strength_points = 0
    
    # Φτιάχνουμε ένα λεξικό με τις θέσεις των ομάδων για να ξέρουμε αν ο αντίπαλος ήταν δυνατός
    ranks = {t['team']['name']: t['position'] for t in standings}
    
    for m in matches:
        is_h = m['homeTeam']['name'] == team_name
        opp_name = m['awayTeam']['name'] if is_h else m['homeTeam']['name']
        
        # 1. Γκολ
        g = m['score']['fullTime']['home'] if is_h else m['score']['fullTime']['away']
        total_goals += g if g is not None else 0
        
        # 2. Ποιότητα Αντιπάλου (Αν κέρδισε ομάδα στην 5άδα, παίρνει extra "δύναμη")
        opp_rank = ranks.get(opp_name, 10)
        if (is_h and m['score']['fullTime']['home'] > m['score']['fullTime']['away']) or \
           (not is_h and m['score']['fullTime']['away'] > m['score']['fullTime']['home']):
            strength_points += (20 - opp_rank) # Όσο πιο μικρό το rank (π.χ. 1η θέση), τόσο πιο πολλοί πόντοι
            
    avg_goals = total_goals / len(matches)
    # Η "δύναμη" επηρεάζει το λ (Poisson)
    final_lambda = avg_goals + (strength_points / 100)
    return final_lambda

def calc_all(h_l, a_l):
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po15 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(2)])
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])
    return p1, px, p2, pgg, po15, po25

# --- UI ---
st.sidebar.title("📍 Ρυθμίσεις")
sel_league_name = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
top_picks = st.sidebar.toggle("🔥 TOP PICKS")
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# --- 1. ΠΡΑΓΜΑΤΙΚΟΣ ΠΙΝΑΚΑΣ GOOGLE STYLE ---
st.sidebar.markdown(f"### 🏆 Βαθμολογία {sel_league_name}")
st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_list = []
if st_data and 'standings' in st_data:
    standings_list = st_data['standings'][0]['table']
    df_list = []
    for t in standings_list:
        df_list.append({
            "Θ": t['position'],
            "Ομάδα": t['team']['shortName'],
            "Β": t['points']
        })
    # Εδώ είναι ο "κανονικός" πίνακας με κουτάκια
    st.sidebar.table(pd.DataFrame(df_list).set_index('Θ'))

# --- 2. ΑΓΩΝΕΣ & ΠΡΟΒΛΕΨΕΙΣ ---
st.title(f"⚽ {sel_league_name}")
all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = all_data.get('matches', [])
display_m = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED', 'LIVE']][:15]
if not display_m: display_m = [m for m in all_m if m['status'] == 'FINISHED'][-10:]

for m in display_m:
    h_t, a_t, h_id, a_id = m['homeTeam']['name'], m['awayTeam']['name'], m['homeTeam']['id'], m['awayTeam']['id']
    
    h_f = fetch_data(f"https://api.football-data.org/v4/teams/{h_id}/matches?status=FINISHED&limit=5")
    a_f = fetch_data(f"https://api.football-data.org/v4/teams/{a_id}/matches?status=FINISHED&limit=5")
    
    h_lambda = get_advanced_stats(h_f.get('matches', []), h_t, standings_list)
    a_lambda = get_advanced_stats(a_f.get('matches', []), a_t, standings_list)
    
    p1, px, p2, pgg, po15, po25 = calc_all(h_lambda, a_lambda)
    if top_picks and not (p1 > 0.7 or p2 > 0.7 or po25 > 0.7): continue

    with st.expander(f"⭐ {m['utcDate'][:10]} | {h_t} vs {a_t}"):
        cols = st.columns(6)
        labels = ["1", "X", "2", "GG", "O1.5", "O2.5"]
        vals = [p1, px, p2, pgg, po15, po25]
        for i in range(6): cols[i].metric(labels[i], f"{round(vals[i]*100)}%")

        st.divider()
        
        # 3. ΦΟΡΜΑ ΟΡΙΖΟΝΤΙΑ: 🟢 ΔΙΠΛΑ ΣΤΟ ΣΗΜΑ
        for label, f_matches, t_name in [("🏠 " + h_t, h_f.get('matches', []), h_t), ("🚀 " + a_t, a_f.get('matches', []), a_t)]:
            st.write(f"**{label}**")
            # Χρησιμοποιούμε στήλες για να είναι το ένα ΔΙΠΛΑ στο άλλο
            f_cols = st.columns(5)
            for i, tm in enumerate(f_matches):
                is_h = tm['homeTeam']['name'] == t_name
                opp_logo = tm['awayTeam']['crest'] if is_h else tm['homeTeam']['crest']
                hg, ag = tm['score']['fullTime']['home'], tm['score']['fullTime']['away']
                icon = "🟡" if hg == ag else ("🟢" if (is_h and hg > ag) or (not is_h and ag > hg) else "🔴")
                
                with f_cols[i]:
                    # Εδώ είναι το "μαγικό": Icon και Logo στην ίδια σειρά οριζόντια
                    st.markdown(f"<div style='display: flex; align-items: center; gap: 5px;'>{icon} <img src='{opp_logo}' width='20'></div>", unsafe_allow_html=True)
