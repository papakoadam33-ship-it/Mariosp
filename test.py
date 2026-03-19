import requests
import sqlite3
import os

API_KEY = os.environ.get('FOOTBALL_API_KEY')
BASE_URL = "https://api.football-data.org/v4/competitions/PL/matches"

def fetch_data():
    headers = {'X-Auth-Token': API_KEY}
    response = requests.get(BASE_URL, headers=headers)
    if response.status_code == 200:
        print("✅ Επιτυχία! Το API απάντησε.")
    else:
        print(f"❌ Σφάλμα: {response.status_code}")

if __name__ == "__main__":
    fetch_data()

