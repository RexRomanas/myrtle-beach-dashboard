from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from PIL import Image, ImageDraw, ImageFont


def create_retry_session():
    """Creates a requests session that automatically retries failed HTTP requests."""
    session = requests.Session()
    
    # Configure retry logic: 
    # Try up to 4 times. Handle 500, 502, 503, 504 errors.
    # Backoff factor 1 means it waits: 1s, 2s, 4s between tries.
    retries = Retry(
        total=4,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False
    )
    
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def get_tide_data(session):
    """Fetches high/low tide predictions from NOAA for Myrtle Beach (Springmaid Pier Station: 8661070)."""
    station_id = "8661070"
    base_url = "https://noaa.gov"

    today = datetime.now()
    tomorrow = today + timedelta(days=1)

    params = {
        "begin_date": today.strftime("%Y%m%d"),
        "end_date": tomorrow.strftime("%Y%m%d"),
        "station": station_id,
        "product": "predictions",
        "datum": "MLLW",
        "time_zone": "lst_ldt",  # Local standard/daylight time
        "interval": "hilo",      # High and low tides only
        "units": "english",
        "application": "GithubDashboard",
        "format": "json"
    }

    try:
        response = session.get(base_url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"NOAA API Error after retries: {response.status_code}")
            return []
        
        data = response.json()
        return data.get("predictions", [])
    except Exception as e:
        print(f"Error fetching tide data: {e}")
        return []


def get_weather_data(session):
    """Fetches weather data from Open-Meteo for Myrtle Beach coordinates in Fahrenheit."""
    base_url = "https://open-meteo.com"
    
    params = {
        "latitude": 33.6891,
        "longitude": -78.8867,
        "hourly": "temperature_2m",
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "fahrenheit",
        "timezone": "auto"
    }

    try:
        response = session.get(base_url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"Open-Meteo Error after retries: {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None


def draw_dashboard(tides, weather):
    """Draws an 800x480 black and white layout."""
    img = Image.new("L", (800, 480), 255)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # Draw grid panels
    draw.line([(400, 0), (400, 480)], fill=0, width=2)  # Vertical split
    draw.line([(0, 240), (800, 240)], fill=0, width=1)  # Horizontal split

    today_str = datetime.now().strftime("%Y-%m-%d")
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # --- TOP LEFT: TODAY'S WEATHER ---
    draw.text((20, 15), "TODAY'S WEATHER", fill=0)
    if weather and "daily" in weather and "hourly" in weather:
        max_t = weather["daily"]["temperature_2m_max"][0]
        min_t = weather["daily"]["temperature_2m_min"][0]
        draw.text((20, 40), f"High: {max_t}F  |  Low: {min_t}F", fill=0)

        hourly_temps = weather["hourly"]["temperature_2m"]
        
        # Pull explicit array slices for 9am, 3pm, and 9pm safely
        draw.text((20, 80), f"Morning (9am):   {hourly_temps[9]}F", fill=0)
        draw.text((20, 120), f"Afternoon (3pm): {hourly_temps[15]}F", fill=0)
        draw.text((20, 160), f"Evening (9pm):   {hourly_temps[21]}F", fill=0)
    else:
        draw.text((20, 40), "Weather data missing or unavailable.", fill=0)

    # --- BOTTOM LEFT: TOMORROW'S WEATHER ---
    draw.text((20, 255), "TOMORROW'S WEATHER", fill=0)
    if weather and "daily" in weather:
        max_t_tom = weather["daily"]["temperature_2m_max"][1]
        min_t_tom = weather["daily"]["temperature_2m_min"][1]
        
        draw.text((20, 290), f"High: {max_t_tom}F", fill=0)
        draw.text((20, 330), f"Low: {min_t_tom}F", fill=0)
    else:
        draw.text((20, 290), "Weather data unavailable.", fill=0)

    # --- RIGHT PANEL: TIDES (TODAY & TOMORROW) ---
    draw.text((420, 15), f"TIDES: TODAY ({today_str})", fill=0)
    draw.text((420, 255), f"TIDES: TOMORROW ({tomorrow_str})", fill=0)

    today_y = 50
    tomorrow_y = 290

    if tides:
        for t in tides:
            t_time_str = t["t"]  # Structure: "2026-06-27 04:12"
            t_type = "HIGH" if t["type"] == "H" else "LOW"
            t_height = t["v"]

            # Split by space and take the second index to extract HH:MM cleanly
            time_part = t_time_str.split(" ")[1] if " " in t_time_str else t_time_str
            display_text = f"{time_part} - {t_type} ({t_height} ft)"

            if t_time_str.startswith(today_str):
                if today_y < 220:
                    draw.text((420, today_y), display_text, fill=0)
                    today_y += 35
            elif t_time_str.startswith(tomorrow_str):
                if tomorrow_y < 460:
                    draw.text((420, tomorrow_y), display_text, fill=0)
                    tomorrow_y += 35
    else:
        draw.text((420, 50), "Tide metrics unavailable.", fill=0)

    # Footer timestamp
    draw.text((10, 460), f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", fill=0)

    # Convert mapping configuration array to raw binary monochrome image
    img_bw = img.convert("1")
    img_bw.save("dashboard.png")
    print("Dashboard image 'dashboard.png' rendered successfully.")


if __name__ == "__main__":
    # Create the network session with automatic retry rules built-in
    http_session = create_retry_session()
    
    tide_predictions = get_tide_data(http_session)
    weather_forecast = get_weather_data(http_session)
    
    draw_dashboard(tide_predictions, weather_forecast)
