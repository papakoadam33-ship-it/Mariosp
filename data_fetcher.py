import requests
import sqlite3
import os
import time

# Παίρνει το API KEY από τα Secrets του GitHub
API_KEY = os.environ.get('FOOTBALL_API_KEY')

# Λίστα με τα πρωταθλήματα που επιτρέπει το ΔΩΡΕΑΝ πακέτο
LEAGUES = {
    'PL': 'Premier League',
    'PD': 'La Liga',
    'SA': 'Serie A',
    'BL1': 'Bundesliga',
    'FL1': 'Ligue 1',
    'PPL': 'Primeira Liga'
}

def init_db():
    conn = sqlite3.connect('betting_app.db')
    cursor = conn.cursor()
    # Δημιουργία πίνακα με τη στήλη 'league'
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY,
            date TEXT,
            league TEXT,
            home_team TEXT,
            away_team TEXT,
            home_goals INTEGER,
            away_goals INTEGER
        )
    ''')
    conn.commit()
    return conn

def fetch_data():
    if not API_KEY:
        print("❌ Σφάλμα: Λείπει το API KEY στα Secrets!")
        return

    conn = init_db()
    cursor = conn.cursor()
    headers = {'X-Auth-Token': API_KEY}

    for code, name in LEAGUES.items():
        url = f"https://api.football-data.org/v4/competitions/{code}/matches"
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                matches_found = data.get('matches', [])
                
                for match in matches_found:
                    m_id = match['id']
                    # Καθαρισμός ημερομηνίας
                    date = match['utcDate'].replace('T', ' ').replace('Z', '')
                    home = match['homeTeam']['name']
                    away = match['awayTeam']['name']
                    
                    score = match.get('score', {}).get('fullTime', {})
                    h_goals = score.get('home')
                    a_goals = score.get('away')

                    cursor.execute('''
                        INSERT OR REPLACE INTO matches 
                        (match_id, date, league, home_team, away_team, home_goals, away_goals)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (m_id, date, name, home, away, h_goals, a_goals))
                
                print(f"✅ Ενημερώθηκε επιτυχώς: {name}")
            
            elif response.status_code == 429:
                print(f"⚠️ Όριο API στο {name}. Περίμενε...")
            else:
                print(f"⚠️ Σφάλμα {response.status_code} στο {name}")

        except Exception as e:
            print(f"❌ Σφάλμα στο {name}: {e}")
        
        # ΠΟΛΥ ΣΗΜΑΝΤΙΚΟ: Περιμένουμε 15 δευτερόλεπτα για να μην μας "κλειδώσει" το API
        time.sleep(15)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    fetch_data()
