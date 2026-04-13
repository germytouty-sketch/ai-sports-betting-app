import requests
import pandas as pd
import numpy as np
from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

# =========================
# CONFIG
# =========================
API_KEY = "YOUR_API_KEY"
SPORT = "soccer_epl"  # change to any supported sport
BANKROLL = 1000

# =========================
# ELO SYSTEM (simple rating)
# =========================
team_elo = {}

def get_elo(team):
    return team_elo.get(team, 1500)

def update_elo(team_a, team_b, result):
    k = 20
    ra = get_elo(team_a)
    rb = get_elo(team_b)

    ea = 1 / (1 + 10 ** ((rb - ra) / 400))
    eb = 1 / (1 + 10 ** ((ra - rb) / 400))

    team_elo[team_a] = ra + k * (result - ea)
    team_elo[team_b] = rb + k * ((1 - result) - eb)

# =========================
# DATA FETCHING
# =========================
def get_odds():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/"
    params = {
        "apiKey": API_KEY,
        "regions": "uk",
        "markets": "h2h"
    }
    res = requests.get(url, params=params)
    return res.json()

# =========================
# AI PREDICTION (ELO-based)
# =========================
def predict_prob(team_a, team_b):
    ra = get_elo(team_a)
    rb = get_elo(team_b)

    prob_a = 1 / (1 + 10 ** ((rb - ra) / 400))
    prob_b = 1 - prob_a

    return prob_a, prob_b

# =========================
# VALUE BET DETECTION
# =========================
def is_value(prob, odds):
    implied = 1 / odds
    return prob > implied

# =========================
# KELLY CRITERION (bet sizing)
# =========================
def kelly(prob, odds):
    b = odds - 1
    return max((prob * (b + 1) - 1) / b, 0)

# =========================
# MAIN ENDPOINT
# =========================
@app.get("/bets")
def get_bets():
    games = get_odds()
    results = []

    for game in games:
        home = game["home_team"]
        away = game["away_team"]

        prob_home, prob_away = predict_prob(home, away)

        try:
            outcomes = game["bookmakers"][0]["markets"][0]["outcomes"]
        except:
            continue

        for o in outcomes:
            team = o["name"]
            odds = o["price"]

            if team == home:
                prob = prob_home
            elif team == away:
                prob = prob_away
            else:
                continue

            value = is_value(prob, odds)
            bet_size = kelly(prob, odds) * BANKROLL

            results.append({
                "match": f"{home} vs {away}",
                "team": team,
                "odds": odds,
                "predicted_prob": round(prob, 3),
                "value_bet": value,
                "recommended_bet_$": round(bet_size, 2),
                "timestamp": datetime.now()
            })

    return results

# =========================
# TRACK PERFORMANCE (basic)
# =========================
history = []

@app.post("/result")
def add_result(team: str, won: bool):
    history.append({"team": team, "won": won})
    return {"status": "saved"}

@app.get("/performance")
def performance():
    if not history:
        return {"message": "No data yet"}

    wins = sum(1 for h in history if h["won"])
    total = len(history)

    return {
        "total_bets": total,
        "wins": wins,
        "win_rate": round(wins / total, 2)
    }
