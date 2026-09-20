"""
Mozzart Placed Tickets Archiver and Training Dataset Builder.
Archives real user-placed betting tickets from Mozzart Bet into structured
training datasets for calibration, backtesting, and model updating.
"""

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List

# Ticket 1 (Screenshot 2: Šifra 1137024777052893)
TICKET_1 = {
    "ticket_id": "1137024777052893",
    "timestamp": "2026-09-21 00:39:15",
    "bookmaker": "Mozzart Bet",
    "status": "PENDING",
    "name": "SIGURICA / VALUE BANKERI",
    "max_payout_rsd": 99.28,
    "total_odds": 1.9934,
    "legs": [
        {
            "match": "Criciuma vs Operario PR",
            "home_team": "Criciuma",
            "away_team": "Operario PR",
            "league": "Brazil 2",
            "start_time": "Uto 00:30",
            "market_type": "double_chance",
            "selection": "1X",
            "mozzart_desc": "Krikuma će pobediti ili će se meč završiti nerešenim rezultatom",
            "odds": 1.14,
            "p_model": 0.8482,
            "implied_prob_devigged": 0.8350,
            "edge": 0.0132,
            "xg_home": 1.45,
            "xg_away": 0.85,
            "predicted_score": "1-0",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "Malacateco vs Deportivo Mixco",
            "home_team": "Malacateco",
            "away_team": "Deportivo Mixco",
            "league": "Gvatemala 1 - Apertura",
            "start_time": "Pon 03:00",
            "market_type": "double_chance",
            "selection": "1X",
            "mozzart_desc": "Malakateko će pobediti ili će se meč završiti nerešenim rezultatom",
            "odds": 1.14,
            "p_model": 0.8455,
            "implied_prob_devigged": 0.8340,
            "edge": 0.0115,
            "xg_home": 1.65,
            "xg_away": 0.80,
            "predicted_score": "2-0",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "Olimpia Tegucigalpa vs Independiente Siguatepeque",
            "home_team": "Olimpia Tegucigalpa",
            "away_team": "Independiente Siguatepeque",
            "league": "Honduras 1 - Apertura",
            "start_time": "Pon 01:15",
            "market_type": "double_chance",
            "selection": "12",
            "mozzart_desc": "Olimpija Tegusigalpa ili Independiente Siguatepeque će pobediti na meču",
            "odds": 1.15,
            "p_model": 0.8361,
            "implied_prob_devigged": 0.8250,
            "edge": 0.0111,
            "xg_home": 1.70,
            "xg_away": 0.70,
            "predicted_score": "2-0",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "Philippines M23 vs Kuwait M23",
            "home_team": "Philippines M23",
            "away_team": "Kuwait M23",
            "league": "Azijske igre",
            "start_time": "Uto 07:00",
            "market_type": "double_chance",
            "selection": "X2",
            "mozzart_desc": "Kuvajt M23 će pobediti ili će se meč završiti nerešenim rezultatom",
            "odds": 1.13,
            "p_model": 0.8387,
            "implied_prob_devigged": 0.8310,
            "edge": 0.0077,
            "xg_home": 0.75,
            "xg_away": 1.60,
            "predicted_score": "0-2",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "Trento vs Pro Vercelli",
            "home_team": "Trento",
            "away_team": "Pro Vercelli",
            "league": "Italija 3 A",
            "start_time": "Pon 20:30",
            "market_type": "double_chance",
            "selection": "1X",
            "mozzart_desc": "Trento će pobediti ili će se meč završiti nerešenim rezultatom",
            "odds": 1.18,
            "p_model": 0.8177,
            "implied_prob_devigged": 0.8050,
            "edge": 0.0127,
            "xg_home": 1.35,
            "xg_away": 0.85,
            "predicted_score": "1-0",
            "actual_score": None,
            "outcome": None
        }
    ]
}

# Ticket 2 (Screenshot 1: Šifra 1137024772928642)
TICKET_2 = {
    "ticket_id": "1137024772928642",
    "timestamp": "2026-09-21 00:44:34",
    "bookmaker": "Mozzart Bet",
    "status": "PENDING",
    "name": "MEGA KOMBO VALUE (Top Picks)",
    "max_payout_rsd": 40388.50,
    "total_odds_raw": 42.4293,
    "legs": [
        {
            "match": "Montana vs Hebar",
            "home_team": "Montana",
            "away_team": "Hebar",
            "league": "Bugarska 2",
            "start_time": "Pon 18:30",
            "market_type": "1X2",
            "selection": "1",
            "mozzart_desc": "Montana će pobediti na meču",
            "odds": 1.90,
            "p_model": 0.5360,
            "implied_prob_devigged": 0.5050,
            "edge": 0.0310,
            "xg_home": 1.50,
            "xg_away": 0.95,
            "predicted_score": "1-0",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "Malacateco vs Deportivo Mixco",
            "home_team": "Malacateco",
            "away_team": "Deportivo Mixco",
            "league": "Gvatemala 1 - Apertura",
            "start_time": "Pon 03:00",
            "market_type": "1X2",
            "selection": "1",
            "mozzart_desc": "Malakateko će pobediti na meču",
            "odds": 1.70,
            "p_model": 0.6003,
            "implied_prob_devigged": 0.5650,
            "edge": 0.0353,
            "xg_home": 1.65,
            "xg_away": 0.80,
            "predicted_score": "2-0",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "Guabira vs SA Bulo Bulo",
            "home_team": "Guabira",
            "away_team": "SA Bulo Bulo",
            "league": "Bolivija Liga Kup",
            "start_time": "Uto 00:00",
            "market_type": "total_goals",
            "selection": "2+",
            "mozzart_desc": "Zbir golova na meču će biti veći od navedene margine (1.5)",
            "odds": 1.18,
            "p_model": 0.8012,
            "implied_prob_devigged": 0.7920,
            "edge": 0.0092,
            "xg_home": 1.80,
            "xg_away": 0.90,
            "predicted_score": "2-0",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "Redditch vs Rc Warwick",
            "home_team": "Redditch",
            "away_team": "Rc Warwick",
            "league": "Engleska 7 - Central",
            "start_time": "Pon 20:45",
            "market_type": "total_goals",
            "selection": "2+",
            "mozzart_desc": "Zbir golova na meču će biti veći od navedene margine (1.5)",
            "odds": 1.20,
            "p_model": 0.7869,
            "implied_prob_devigged": 0.7780,
            "edge": 0.0089,
            "xg_home": 1.70,
            "xg_away": 0.90,
            "predicted_score": "2-0",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "HB Koge vs Hobro IK",
            "home_team": "HB Koge",
            "away_team": "Hobro IK",
            "league": "Danska 2",
            "start_time": "Pon 19:00",
            "market_type": "total_goals",
            "selection": "2+",
            "mozzart_desc": "Zbir golova na meču će biti veći od navedene margine (1.5)",
            "odds": 1.20,
            "p_model": 0.7841,
            "implied_prob_devigged": 0.7760,
            "edge": 0.0081,
            "xg_home": 1.35,
            "xg_away": 1.25,
            "predicted_score": "1-1",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "Olimpia Tegucigalpa vs Independiente Siguatepeque",
            "home_team": "Olimpia Tegucigalpa",
            "away_team": "Independiente Siguatepeque",
            "league": "Honduras 1 - Apertura",
            "start_time": "Pon 01:15",
            "market_type": "1X2",
            "selection": "1",
            "mozzart_desc": "Olimpija Tegusigalpa će pobediti na meču",
            "odds": 1.33,
            "p_model": 0.7624,
            "implied_prob_devigged": 0.7300,
            "edge": 0.0324,
            "xg_home": 1.70,
            "xg_away": 0.70,
            "predicted_score": "2-0",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "Velez Sarsfield vs Tigre",
            "home_team": "Velez Sarsfield",
            "away_team": "Tigre",
            "league": "Argentina 1 - Klausura",
            "start_time": "Pon 02:30",
            "market_type": "double_chance",
            "selection": "1X",
            "mozzart_desc": "Velez Sarsfield će pobediti ili će se meč završiti nerešenim rezultatom",
            "odds": 1.30,
            "p_model": 0.7651,
            "implied_prob_devigged": 0.7420,
            "edge": 0.0231,
            "xg_home": 1.25,
            "xg_away": 0.75,
            "predicted_score": "1-0",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "Lanus vs Estudiantes de La Plata",
            "home_team": "Lanus",
            "away_team": "Estudiantes de La Plata",
            "league": "Argentina 1 - Klausura",
            "start_time": "Uto 02:15",
            "market_type": "double_chance",
            "selection": "1X",
            "mozzart_desc": "Lanus će pobediti ili će se meč završiti nerešenim rezultatom",
            "odds": 1.31,
            "p_model": 0.7533,
            "implied_prob_devigged": 0.7380,
            "edge": 0.0153,
            "xg_home": 1.20,
            "xg_away": 0.80,
            "predicted_score": "1-0",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "Dolomiti Bellunesi vs Lumezzane",
            "home_team": "Dolomiti Bellunesi",
            "away_team": "Lumezzane",
            "league": "Italija 3 A",
            "start_time": "Pon 20:30",
            "market_type": "double_chance",
            "selection": "1X",
            "mozzart_desc": "Dolomiti će pobediti ili će se meč završiti nerešenim rezultatom",
            "odds": 1.30,
            "p_model": 0.7411,
            "implied_prob_devigged": 0.7350,
            "edge": 0.0061,
            "xg_home": 1.20,
            "xg_away": 0.80,
            "predicted_score": "1-0",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "LDU Quito vs Universidad Catolica",
            "home_team": "LDU Quito",
            "away_team": "Universidad Catolica",
            "league": "Ekvador 1",
            "start_time": "Pon 01:30",
            "market_type": "double_chance",
            "selection": "1X",
            "mozzart_desc": "LDU Kvito će pobediti ili će se meč završiti nerešenim rezultatom",
            "odds": 1.30,
            "p_model": 0.7320,
            "implied_prob_devigged": 0.7290,
            "edge": 0.0030,
            "xg_home": 1.30,
            "xg_away": 1.00,
            "predicted_score": "1-1",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "Nueva Chicago vs Patronato",
            "home_team": "Nueva Chicago",
            "away_team": "Patronato",
            "league": "Argentina 2",
            "start_time": "Uto 00:00",
            "market_type": "double_chance",
            "selection": "1X",
            "mozzart_desc": "Novi Čikago će pobediti ili će se meč završiti nerešenim rezultatom",
            "odds": 1.32,
            "p_model": 0.7288,
            "implied_prob_devigged": 0.7210,
            "edge": 0.0078,
            "xg_home": 1.20,
            "xg_away": 0.75,
            "predicted_score": "1-0",
            "actual_score": None,
            "outcome": None
        },
        {
            "match": "Sportist Svoge vs Vihren Sandanski",
            "home_team": "Sportist Svoge",
            "away_team": "Vihren Sandanski",
            "league": "Bugarska 2",
            "start_time": "Pon 16:00",
            "market_type": "1X2",
            "selection": "2",
            "mozzart_desc": "Vihren Sandanski će pobediti na meču",
            "odds": 1.53,
            "p_model": 0.6402,
            "implied_prob_devigged": 0.6120,
            "edge": 0.0282,
            "xg_home": 0.80,
            "xg_away": 1.45,
            "predicted_score": "0-1",
            "actual_score": None,
            "outcome": None
        }
    ]
}


def build_archive():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    training_dir = os.path.join(base_dir, "data", "training")
    os.makedirs(training_dir, exist_ok=True)

    archive_data = {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "source": "Mozzart Bet Live Wagers",
            "description": "Archived tickets and quantitative feature vectors for model calibration and supervised retraining.",
            "tickets_count": 2,
            "total_legs_count": len(TICKET_1["legs"]) + len(TICKET_2["legs"]),
            "status": "PENDING_MATCH_OUTCOMES"
        },
        "tickets": [TICKET_1, TICKET_2]
    }

    # 1. Save placed tickets JSON
    json_path = os.path.join(training_dir, "placed_tickets_archive.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(archive_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved JSON archive: {json_path}")

    # 2. Save flat training dataset CSV
    csv_path = os.path.join(training_dir, "mozzart_training_dataset.csv")
    csv_rows = []
    sample_id = 1

    for t in [TICKET_1, TICKET_2]:
        for leg in t["legs"]:
            csv_rows.append({
                "sample_id": sample_id,
                "ticket_id": t["ticket_id"],
                "ticket_name": t["name"],
                "match": leg["match"],
                "home_team": leg["home_team"],
                "away_team": leg["away_team"],
                "league": leg["league"],
                "start_time": leg["start_time"],
                "market_type": leg["market_type"],
                "selection": leg["selection"],
                "odds": leg["odds"],
                "p_model": leg["p_model"],
                "implied_prob_devigged": leg["implied_prob_devigged"],
                "edge": leg["edge"],
                "xg_home": leg["xg_home"],
                "xg_away": leg["xg_away"],
                "predicted_score": leg["predicted_score"],
                "actual_score": "",
                "outcome_win": "",
                "status": "PENDING"
            })
            sample_id += 1

    fieldnames = list(csv_rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"✅ Saved training CSV: {csv_path} ({len(csv_rows)} samples)")

    # 3. Save JSONL version for streaming training loops
    jsonl_path = os.path.join(training_dir, "mozzart_training_dataset.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for row in csv_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"✅ Saved training JSONL: {jsonl_path}")


if __name__ == "__main__":
    build_archive()
