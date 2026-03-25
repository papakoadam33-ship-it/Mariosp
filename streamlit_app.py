import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

st.set_page_config(page_title="Pro Football Predictor", layout="wide")

# --- API CONFIG ---
API_KEY = "a963742bcd5642afbe8c842d057f25ad" 

LEAGUES = {'PL':'Premier League','PD':'La Liga','BL1':'Bundesliga','SA':'Serie A', 'FL1':'Ligue 1'}

@st.cache_data(ttl=300)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except: return {}

def calc_all(h_l, a_l):
    p1 = sum([poisson.pmf(i, h_l) * sum([poisson.pmf(j, a_l) for j in range(i)]) for i in range(1, 10)])
    px = sum([poisson.pmf(i, h_l) * poisson.pmf(i, a_l) for i in range(10)])
    p2 = max(0, 1 - p1 - px)
    pgg = (1 - poisson.pmf(0, h_l)) * (1 - poisson.pmf(0, a_l))
    po15 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(2)])
    po25 = 1 - sum([poisson.pmf(i, h_l + a_l) for i in range(3)])
    return p1, px, p2, pgg, po15, po25

# --- SIDEBAR & ΡΥΘΜΙΣΕΙΣ ---
st.sidebar.title("📍 Ρυθμίσεις")
sel_league_name = st.sidebar.selectbox("Πρωτάθλημα:", list(LEAGUES.values()))
top_picks = st.sidebar.toggle("🔥 TOP PICKS")
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

# --- ΠΙΝΑΚΑΣ ΒΑΘΜΟΛΟΓΙΑΣ (GOOGLE STYLE) ---
st.sidebar.markdown(f"### 🏆 Πίνακας {sel_league_name}")
st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")

if st_data and 'standings' in st_data:
    raw_table = st_data['standings'][0]['table']
    # Δημιουργία καθαρού DataFrame για να φαίνεται σαν πίνακας με κουτάκια
    df_data = []
    for t in raw_table:
        df_data.append({
            "Pos": t['position'],
            "Team": t['team']['shortName'],
            "Pts": t['points'],
            "GP": t['playedGames']
        })
    df = pd.DataFrame(df_data)
    # Εμφάνιση ως πίνακας στο Sidebar
    st.sidebar.table(df.set_index('Pos'))

# --- ΚΥΡΙΟ ΠΑΝΕΛ: ΑΓΩΝΕΣ ---
st.title(f"⚽ {sel_league_name} Matches")

# Τραβάμε ΟΛΟΥΣ τους αγώνες για να μη χάνουμε πρωταθλήματα
all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_matches = all_data.get('matches', [])

# Φιλτράρισμα: Δείξε LIVE ή SCHEDULED, αν δεν έχει τίποτα δείξε τα τελευταία 10 FINISHED
display_matches = [m for m in all_matches if m['status'] in ['SCHEDULED', 'TIMED', 'LIVE', 'IN_PLAY']]
if not display_matches:
    st.warning(f"Δεν υπάρχουν άμεσα ματς στην {sel_league_name}. Εμφάνιση πρόσφατων αποτελεσμάτων:")
    display_matches = [m for m in all_matches if m['status'] == 'FINISHED'][-10:]

for m in display_matches:
    h_t, a_t, h_id, a_id = m['homeTeam']['name'], m['awayTeam']['name'], m['homeTeam']['id'], m['awayTeam']['id']
    p1, px, p2, pgg, po15, po25 = calc_all(1.7, 1.2)
    
    if top_picks and not (p1 > 0.7 or p2 > 0.7 or po25 > 0.7): continue

    with st.expander(f"⭐ {m['utcDate'][:10]} | {h_t} vs {a_t}"):
        # 1. ΠΡΟΒΛΕΨΕΙΣ (ΟΡΙΖΟΝΤΙΑ)
        m_cols = st.columns(6)
        labels = ["1", "X", "2", "GG", "O1.5", "O2.5"]
        vals = [p1, px, p2, pgg, po15, po25]
        for i in range(6):
            m_cols[i].metric(labels[i], f"{round(vals[i]*100)}%")

        st.divider()
        
        # 2. ΦΟΡΜΑ (5 ΜΑΤΣ ΟΡΙΖΟΝΤΙΑ)
        for label, t_id, t_name in [("🏠 " + h_t, h_id, h_t), ("🚀 " + a_t, a_id, a_t)]:
            st.write(f"**{label} (Last 5)**")
            f_data = fetch_data(f"https://api.football-data.org/v4/teams/{t_id}/matches?status=FINISHED&limit=5")
            f_matches = f_data.get('matches', [])
            
            # Φτιάχνουμε 5 στήλες - Η μία δίπλα στην άλλη (Οριζόντια)
            f_cols = st.columns(5)
            for i, tm in enumerate(f_matches):
                is_h = tm['homeTeam']['name'] == t_name
                opp_logo = tm['awayTeam']['crest'] if is_h else tm['homeTeam']['crest']
                score = tm.get('score', {}).get('fullTime', {})
                hg, ag = score.get('home'), score.get('away')
                res_icon = "🟡" if hg == ag else ("🟢" if (is_h and hg > ag) or (not is_h and ag > hg) else "🔴")
                
                with f_cols[i]:
                    st.markdown(f"<div style='text-align:center'>{res_icon}<br><img src='{opp_logo}' width='22'></div>", unsafe_allow_html=True)
            st.write("")
