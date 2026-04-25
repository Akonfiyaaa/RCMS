import random
import requests
from Backend.config import GOOGLE_MAPS_API_KEY

def get_traffic_density(origin_lat, origin_lng):
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"

    # 🔹 ~300m offset (approx)
    dest_lat = origin_lat + random.uniform(0.0015, 0.0025)
    dest_lng = origin_lng + random.uniform(0.0015, 0.0025)

    params = {
        "origins": f"{origin_lat},{origin_lng}",
        "destinations": f"{dest_lat},{dest_lng}",
        "departure_time": "now",
        "key": GOOGLE_MAPS_API_KEY
    }

    try:
        response = requests.get(url, params=params).json()

        element = response["rows"][0]["elements"][0]

        if element["status"] != "OK":
            return 5  # fallback

        duration = element["duration_in_traffic"]["value"]  # seconds

        # 🎯 Your rule:
        # 300m taking ≥ 300 sec (~5 min) → traffic = 10

        max_time = 300  # 3 minutes (worst case)
        min_time = 30   # 30 sec = free flow

        # Clamp duration within range
        duration = max(min_time, min(duration, max_time))

        # 🔥 Linear scaling (1 → 10)
        traffic_score = 1 + ((duration - min_time) / (max_time - min_time)) * 9

        return round(traffic_score, 1)

    except:
        return 3  # neutral fallback