import requests
import sqlite3
import os

API_KEY = os.environ.get('FOOTBALL_API_KEY')
# Λίστα με τα πρωταθλήματα που θέλουμε
LEAGUES = {
    'PL': 'Premier League',
    'PD': 'La Liga',
    'SA': 'Serie A',
    'BL1': 'Bundesliga'
}

def init_db():
    conn = sqlite3.connect('betting_app.db')
    cursor = conn.cursor()
    # Προσθέσαμε τη στήλη 'league'
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
        print("❌ Σφάλμα: Λείπει το API KEY!")
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
                for match in data.get('matches', []):
                    m_id = match['id']
                    # Παίρνουμε την ημερομηνία και την καθαρίζουμε λίγο
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
                print(f"✅ Ενημερώθηκε το: {name}")
            else:
                print(f"⚠️ Σφάλμα στο {name}: {response.status_code}")
        except Exception as e:
            print(f"❌ Κάτι πήγε στραβά στο {name}: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    fetch_data()
