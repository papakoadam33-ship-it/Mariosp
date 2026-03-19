import sqlite3
import pandas as pd
from scipy.stats import poisson

def calculate_probability(home_expectancy, away_expectancy):
    max_goals = 10
    prob_over_25 = 0
    for h in range(max_goals):
        for a in range(max_goals):
            prob = poisson.pmf(h, home_expectancy) * poisson.pmf(a, away_expectancy)
            if h + a > 2.5:
                prob_over_25 += prob
    return prob_over_25

def run_predictions():
    conn = sqlite3.connect('betting_app.db')
    # Παίρνουμε τους αγώνες που δεν έχουν γίνει ακόμα
    query = "SELECT match_id, home_team, away_team FROM matches WHERE home_goals IS NULL"
    df = pd.read_sql_query(query, conn)
    
    predictions = []
    for index, row in df.iterrows():
        # Εδώ βάζουμε ενδεικτικά xG (1.5 για γηπεδούχο, 1.2 για φιλοξενούμενο)
        # Στο μέλλον εδώ θα μπαίνει ο μέσος όρος που υπολογίζει το AI
        p_over = calculate_probability(1.5, 1.2)
        predictions.append({
            'Match': f"{row['home_team']} vs {row['away_team']}",
            'Over 2.5 Prob': f"{p_over:.1%}",
            'Fair Odds': round(1/p_over, 2)
        })
    
    conn.close()
    return predictions

if __name__ == "__main__":
    preds = run_predictions()
    for p in preds:
        print(p)

