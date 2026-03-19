import requests
import sqlite3
import os

# Εδώ παίρνουμε το κλειδί που έβαλες στα Secrets
API_KEY = os.environ.get('FOOTBALL_API_KEY')
# Αυτή η διεύθυνση είναι για το Football-Data.org
BASE_URL = "https://api.football-data.org/v4/competitions/PL/matches"

def init_db():
    conn = sqlite3.connect('betting_app.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY,
            date TEXT,
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
        print("Σφάλμα: Λείπει το API KEY από τα Secrets!")
        return

    headers = {'X-Auth-Token': API_KEY}
    try:
        response = requests.get(BASE_URL, headers=headers)
        if response.status_code == 200:
            data = response.json()
            conn = init_db()
            cursor = conn.cursor()
            
            for match in data.get('matches', []):
                m_id = match['id']
                date = match['utcDate']
                home = match['homeTeam']['name']
                away = match['awayTeam']['name']
                # Χειρισμός για αγώνες που δεν έχουν γίνει ακόμα
                score = match.get('score', {}).get('fullTime', {})
                h_goals = score.get('home')
                a_goals = score.get('away')
                
                cursor.execute('''
                    INSERT OR REPLACE INTO matches (match_id, date, home_team, away_team, home_goals, away_goals)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (m_id, date, home, away, h_goals, a_goals))
                
            conn.commit()
            conn.close()
            print("✅ Η βάση ενημερώθηκε επιτυχώς!")
        else:
            print(f"❌ Σφάλμα API: {response.status_code}. Ελέγξτε το Key σας.")
    except Exception as e:
        print(f"❌ Κάτι πήγε στραβά: {e}")

if __name__ == "__main__":
    fetch_data()
