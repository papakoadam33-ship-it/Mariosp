import streamlit as st
import requests
from scipy.stats import poisson
import pandas as pd

# Ρύθμιση σελίδας
st.set_page_config(page_title="Pro Predictor v16.37", layout="wide")

# --- CSS (Αμετάβλητο) ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), 
        url("https://images.unsplash.com/photo-1504450758481-7338eba7524a?q=80&w=2069&auto=format&fit=crop");
        background-size: cover; background-attachment: fixed;
    }
    [data-testid="stSidebar"] { background-color: #2b2b2b !important; }
    div[data-baseweb="select"] * { color: #000000 !important; }
    .sidebar-white-text { color: #ffffff !important; font-weight: bold; }
    h1, h2, h3, [data-testid="stMarkdownContainer"] p { color: #ffffff !important; }
    .matchday-divider {
        border: 0; height: 3px;
        background: linear-gradient(to right, transparent, #00ff88, #ffffff, #00ff88, transparent);
        margin: 40px 0 20px 0;
    }
    .prediction-box {
        background: rgba(255, 255, 255, 0.08) !important; 
        padding: 8px 5px; border-radius: 8px; text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.15); backdrop-filter: blur(3px);
        margin-bottom: 5px;
    }
    [data-testid="stElementToolbar"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

API_KEY = "a963742bcd5642afbe8c842d057f25ad" 
LEAGUES = {'PL':'Premier League', 'PD':'La Liga', 'BL1':'Bundesliga', 'SA':'Serie A', 'FL1':'Ligue 1', 'CL':'Champions League', 'DED':'Eredivisie', 'ELC':'Championship'}

@st.cache_data(ttl=60)
def fetch_data(url):
    headers = {'X-Auth-Token': API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except: return {}

def calculate_form_modifier(team_name, standings_dict):
    stats = standings_dict.get(team_name, {})
    form = stats.get('form', "")
    pos = stats.get('pos', 10)
    modifier = 1.0
    if not form: return modifier
    last_results = form.replace(',', '').split()
    for res in last_results[:3]:
        if res == 'W': modifier += 0.05 if pos > 10 else 0.02
        elif res == 'L': modifier -= 0.05 if pos < 6 else 0.02
    return modifier

# --- SIDEBAR ---
st.sidebar.markdown('<p class="sidebar-white-text" style="font-size:25px;">⚙️ Ρυθμίσεις</p>', unsafe_allow_html=True)
league_names = list(LEAGUES.values())
sel_league_name = st.sidebar.selectbox("Επιλέξτε Πρωτάθλημα:", league_names)
sel_code = [k for k, v in LEAGUES.items() if v == sel_league_name][0]

st_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/standings")
standings_dict = {}
if st_data and 'standings' in st_data:
    st_table = st_data['standings'][0]['table']
    for t in st_table:
        standings_dict[t['team']['name']] = {
            'gf': t['goalsFor']/t['playedGames'] if t['playedGames']>0 else 1.2, 
            'ga': t['goalsAgainst']/t['playedGames'] if t['playedGames']>0 else 1.2,
            'pos': t['position'], 'form': t.get('form', "") 
        }
    df = pd.DataFrame([{"#": t['position'], "Team": t['team']['shortName'], "Pts": t['points']} for t in st_table])
    st.sidebar.markdown("---")
    st.sidebar.markdown('<p class="sidebar-white-text">📊 Βαθμολογία</p>', unsafe_allow_html=True)
    st.sidebar.dataframe(df, hide_index=True, use_container_width=True)

# --- MAIN ---
st.markdown(f'<h1 style="text-align:center;">⚽ {sel_league_name} Analysis</h1>', unsafe_allow_html=True)

all_data = fetch_data(f"https://api.football-data.org/v4/competitions/{sel_code}/matches")
matches = all_data.get('matches', [])
display_m = [m for m in matches if m['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY', 'PAUSED']][:30]

for i, m in enumerate(display_m):
    if i > 0 and i % (len(standings_dict) // 2) == 0:
        st.markdown('<div class="matchday-divider"></div>', unsafe_allow_html=True)

    status = m['status']
    is_live = status in ['IN_PLAY', 'PAUSED']
    h_score = m['score']['fullTime']['home'] if m['score']['fullTime']['home'] is not None else 0
    a_score = m['score']['fullTime']['away'] if m['score']['fullTime']['away'] is not None else 0
    
    h_t, a_t = m['homeTeam']['name'], m['awayTeam']['name']
    h_stats = standings_dict.get(h_t, {'gf':1.2, 'ga':1.2, 'pos':10, 'form':''})
    a_stats = standings_dict.get(a_t, {'gf':1.2, 'ga':1.2, 'pos':10, 'form':''})
    
    h_fmod, a_fmod = calculate_form_modifier(h_t, standings_dict), calculate_form_modifier(a_t, standings_dict)
    time_factor = 0.5 if is_live else 1.0
    h_l = ((h_stats['gf'] + a_stats['ga'])/2) * time_factor * h_fmod
    a_l = ((a_stats['gf'] + h_stats['ga'])/2) * time_factor * a_fmod
    
    p1 = sum([poisson.pmf(k, h_l) * sum([poisson.pmf(j, a_l) for j in range(k + (h_score - a_score))]) for k in range(0, 6)])
    px = sum([poisson.pmf(k, h_l) * poisson.pmf(k + (h_score - a_score), a_l) for k in range(0, 6)])
    p2 = max(0, 1 - p1 - px)
    current_total = h_score + a_score
    po25_val = 1 - sum([poisson.pmf(k, h_l + a_l) for k in range(max(0, 3 - current_total))])
    po15_val = 1 - sum([poisson.pmf(k, h_l + a_l) for range(max(0, 2 - current_total))]) if 'range' in locals() else 0 # Fix for syntax
    po15_val = 1 - sum([poisson.pmf(k, h_l + a_l) for k in range(max(0, 2 - current_total))])
    pgg_val = (1-poisson.pmf(0, h_l + (1 if h_score > 0 else 0))) * (1-poisson.pmf(0, a_l + (1 if a_score > 0 else 0)))

    # --- NEW VALUE LOGIC ---
    alert_emoji, alert_msg = "", ""
    if p1 > 0.75: 
        alert_emoji, alert_msg = "💎", "High Confidence: Home Win"
    elif p1 + px > 0.60 and h_stats['pos'] > a_stats['pos'] + 5:
        alert_emoji, alert_msg = "🔥", f"Value Opportunity: 1X Underdog ({round((p1+px)*100)}%)"
    elif p2 + px > 0.60 and a_stats['pos'] > h_stats['pos'] + 5:
        alert_emoji, alert_msg = "🔥", f"Value Opportunity: X2 Underdog ({round((p2+px)*100)}%)"
    elif p2 > 0.65:
        alert_emoji, alert_msg = "🔥", "Value Opportunity: Away Win"
    elif po25_val > 0.75:
        alert_emoji, alert_msg = "🔥", "Value Opportunity: Over 2.5"

    title = f"{alert_emoji} " + (f"🔴 LIVE {h_score}-{a_score} | {m['homeTeam']['shortName']} vs {m['awayTeam']['shortName']}" if is_live else f"📅 {m['utcDate'][:10]} | {m['homeTeam']['shortName']} vs {m['awayTeam']['shortName']}")
    
    with st.expander(title):
        if alert_msg:
            st.markdown(f'<p style="color:#00ff88; font-weight:bold; font-size:14px;">🌟 {alert_msg}</p>', unsafe_allow_html=True)
        
        cols1 = st.columns(6)
        res_list = [("1", p1), ("X", px), ("2", p2), ("GG", pgg_val), ("O1.5", po15_val), ("O2.5", po25_val)]
        for idx, (lbl, val) in enumerate(res_list):
            happened = (lbl=="GG" and h_score>0 and a_score>0) or (lbl=="O1.5" and current_total>1) or (lbl=="O2.5" and current_total>2)
            val_perc = round(val * 100)
            display_text = "✅" if happened else f"{val_perc}%"
            color = "#00ff88" if (happened or val_perc > 65) else "#ffffff"
            cols1[idx].markdown(f'<div class="prediction-box"><small style="color:#bbb; font-size:11px;">{lbl}</small><br><span style="color:{color}; font-size:15px; font-weight:bold;">{display_text}</span></div>', unsafe_allow_html=True)
        
        # HT & Scores row
        st.markdown('<p style="font-size:12px; color:#aaa; margin-top:10px;">HT & Probable Scores</p>', unsafe_allow_html=True)
        cols2 = st.columns(6)
        p1_ht = sum([poisson.pmf(k, h_l*0.45) * sum([poisson.pmf(j, a_l*0.45) for j in range(k)]) for k in range(1, 5)])
        px_ht = sum([poisson.pmf(k, h_l*0.45) * poisson.pmf(k, a_l*0.45) for k in range(5)])
        p2_ht = max(0, 1 - p1_ht - px_ht)
        for idx, (l, v) in enumerate([("HT 1", p1_ht), ("HT X", px_ht), ("HT 2", p2_ht)]):
            cols2[idx].markdown(f'<div class="prediction-box"><small style="color:#bbb; font-size:10px;">{l}</small><br><span style="color:#fff; font-size:14px;">{round(v*100)}%</span></div>', unsafe_allow_html=True)
        
        scores = sorted([(f"{h+h_score}-{a+a_score}", poisson.pmf(h,h_l)*poisson.pmf(a,a_l)) for h in range(4) for a in range(4)], key=lambda x:x[1], reverse=True)[:3]
        for i in range(3):
            s_lbl, s_prob = scores[i]
            s_perc = round(s_prob * 100)
            score_color = "#00ff88" if s_perc > 15 else "#ffffff"
            cols2[3+i].markdown(f'<div class="prediction-box"><small style="color:#bbb; font-size:9px;">Exact Score</small><br><span style="color:{score_color}; font-size:13px; font-weight:bold;">{s_lbl} ({s_perc}%)</span></div>', unsafe_allow_html=True)

            
