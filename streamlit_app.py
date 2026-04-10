import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

st.set_page_config(page_title="Pro Football Predictor Ultra", layout="wide")

# --- CUSTOM CSS ΓΙΑ ΠΡΑΓΜΑΤΙΚΑ "ΨΑΓΜΕΝΟ" LOOK ---
st.markdown("""
    <style>
    /* Φόντο με απαλό gradient και εικόνα */
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    
    /* Στυλ για τις κάρτες των αγώνων */
    .stExpander {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 15px !important;
        margin-bottom: 10px !important;
    }
    
    /* Στυλ για τα νούμερα (Metrics) */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: bold !important;
    }
    
    h1 { color: #e94560 !important; text-align: center; font-weight: 800; }
    h3 { color: #0f3460 !important; }
    </style>
    """, unsafe_allow_html=True)

API_KEY = "a963742bcd5642afbe8c842d057f25ad" 
LEAGUES = {'PL':'Premier League','PD':'La Liga','BL1':'Bundesliga','SA':'Serie A','FL1':'Ligue 1','CL':'Champions League','DED':'Eredivisie','ELC':'Championship'}

@st.cache_data(ttl=300)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except: return {}

def calc_all(h_l, a_l, cur_h=0, cur_a=0, is_live=False):
    # Live Logic: Αν το ματς είναι Live, μειώνουμε το χρόνο (Poisson λ)
    time_factor = 0.4 if is_live else 1.0 # Υποθέτουμε ότι έχει περάσει το 60% του ματς στο Live
    h_l_rem = h_l * time_factor
    a_l_rem = a_l * time_factor

    # Πιθανότητες για τα γκολ που απομένουν
    p1_rem = sum([poisson.pmf(i, h_l_rem) * sum([poisson.pmf(j, a_l_rem) for j in range(i)]) for i in range(1, 10)])
    px_rem = sum([poisson.pmf(i, h_l_rem) * poisson.pmf(i, a_l_rem) for i in range(10)])
    p2_rem = max(0, 1 - p1_rem - px_rem)

    # Τελικό 1Χ2 συνδυασμένο με το τρέχον σκορ
    if is_live:
        if cur_h > cur_a: p1, px, p2 = 0.85, 0.10, 0.05
        elif cur_a > cur_h: p1, px, p2 = 0.05, 0.10, 0.85
        else: p1, px, p2 = 0.25, 0.50, 0.25
    else:
        p1, px, p2 = p1_rem, px_rem, p2_rem

    # Over 1.5/2.5 με βάση τα ήδη υπάρχοντα γκολ
    po15 = 1 - sum([poisson.pmf(i, h_l_rem + a_l_rem) for i in range(max(0, 2 - (cur_h + cur_a)))])
    po25 = 1 - sum([poisson.pmf(i, h_l_rem + a_l_rem) for i in range(max(0, 3 - (cur_h + cur_a)))])
    pgg = (1 - poisson.pmf(0, h_l_rem + cur_h)) * (1 - poisson.pmf(0, a_l_rem + cur_a))
    
    return p1, px, p2, pgg, po15, po25

# --- SIDEBAR ---
st.sidebar.markdown("# ⚙️ Settings")
sel_league_name = st.sidebar.selectbox("Choose League:", list(LEAGUES.values()))
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_dict = {}
if st_data and 'standings' in st_data:
    st_table = st_data['standings'][0]['table']
    for t in st_table:
        standings_dict[t['team']['name']] = {
            'gf': t['goalsFor'] / t['playedGames'] if t['playedGames'] > 0 else 1.2,
            'ga': t['goalsAgainst'] / t['playedGames'] if t['playedGames'] > 0 else 1.2
        }
    df_data = [{"#": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table]
    st.sidebar.table(pd.DataFrame(df_data).set_index('#'))

# --- MAIN ---
st.title(f"⚽ {sel_league_name} Pro Analysis")

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
all_m = all_data.get('matches', [])
display_m = [m for m in all_m if m['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY', 'PAUSED']][:20]

for m in display_m:
    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    status = m['status']
    is_live = status in ['IN_PLAY', 'PAUSED']
    score = m.get('score', {}).get('fullTime', {})
    cur_h, cur_a = (score.get('home') or 0), (score.get('away') or 0)
    
    h_stats = standings_dict.get(h_t, {'gf': 1.2, 'ga': 1.2})
    a_stats = standings_dict.get(a_t, {'gf': 1.2, 'ga': 1.2})
    h_l, a_l = (h_stats['gf'] + a_stats['ga'])/2, (a_stats['gf'] + h_stats['ga'])/2
    
    p1, px, p2, pgg, po15, po25 = calc_all(h_l, a_l, cur_h, cur_a, is_live)

    # Δημιουργία ωραίου τίτλου
    if is_live:
        header = f"🔴 LIVE | {cur_h} - {cur_a} | {h_t} vs {a_t}"
    else:
        header = f"⏳ {m['utcDate'][11:16]} | {h_t} vs {a_t}"

    with st.expander(header):
        cols = st.columns(6)
        lbls = ["1", "X", "2", "GG", "O 1.5", "O 2.5"]
        vals = [p1, px, p2, pgg, po15, po25]
        
        for i in range(6):
            val_perc = round(vals[i]*100)
            # Χρώμα ανάλογα με την πιθανότητα
            color = "normal" if val_perc < 65 else "inverse"
            
            if i == 4 and (cur_h + cur_a) >= 2:
                cols[i].success("✅ O1.5")
            elif i == 5 and (cur_h + cur_a) >= 3:
                cols[i].success("✅ O2.5")
            else:
                cols[i].metric(lbls[i], f"{val_perc}%", delta=None)

st.markdown("---")
st.caption("Data provided by Football-Data.org API. Probabilities based on Poisson Distribution.")
