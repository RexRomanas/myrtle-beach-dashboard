from datetime import datetime, timedelta
import requests
from PIL import Image, ImageDraw, ImageFont


def get_tide_data():
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
        "format": "json"
    }

    try:
        response = requests.get(base_url, params=params).json()
        return response.get("predictions", [])
    except Exception as e:
        print(f"Error fetching tide data: {e}")
        return []


def get_weather_data():
    """Fetches weather data from Open-Meteo for Myrtle Beach coordinates in Fahrenheit."""
    lat, lon = 33.6891, -78.8867
    # Fixed: Added temperature_unit=fahrenheit parameter directly to the URL string
    url = f"https://open-meteo.com{lat}&longitude={lon}&hourly=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min,weather_code&temperature_unit=fahrenheit&timezone=auto"

    try:
        return requests.get(url).json()
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None


def interpret_wmo_code(code):
    """Maps WMO Weather codes safely to standard descriptive text string labels."""
    c = int(code) if code is not None else -1
    if c == 0: return "Clear"
    if c in [1, 2, 3]: return "Partly Cloudy"
    if c in [45, 48]: return "Foggy"
    if c in [51, 53, 55, 61, 63, 65, 80, 81, 82]: return "Rain"
    if c in [71, 73, 75, 77, 85, 86]: return "Snow"
    if c in [95, 96, 99]: return "Thunderstorm"
    return "Cloudy"


def draw_dashboard(tides, weather):
    """Draws an 800x480 black and white layout using original fallback visual structure."""
    img = Image.new("L", (800, 480), 255)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # Draw grid boundaries
    draw.line([(400, 0), (400, 480)], fill=0, width=2)  # Middle vertical split
    draw.line([(0, 240), (800, 240)], fill=0, width=1)  # Horizontal sub-split

    # Set up date filter strings matching "YYYY-MM-DD"
    today_str = datetime.now().strftime("%Y-%m-%d")
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # --- TOP LEFT: TODAY'S WEATHER ---
    draw.text((20, 15), "TODAY'S WEATHER", fill=0)
    if weather and "daily" in weather and "hourly" in weather:
        # Access day index positions safely
        max_t = weather["daily"]["temperature_2m_max"][0]
        min_t = weather["daily"]["temperature_2m_min"][0]
        draw.text((20, 40), f"High: {max_t}F  |  Low: {min_t}F", fill=0)

        # Parse morning (9 AM), afternoon (3 PM), evening (9 PM) from the 24h cycle
        hourly_temps = weather["hourly"]["temperature_2m"]
        hourly_codes = weather["hourly"]["weather_code"]

        draw.text((20, 80), f"Morning (9am):   {hourly_temps[9]}F - {interpret_wmo_code(hourly_codes[9])}", fill=0)
        draw.text((20, 120), f"Afternoon (3pm): {hourly_temps[15]}F - {interpret_wmo_code(hourly_codes[15])}", fill=0)
        draw.text((20, 160), f"Evening (9pm):   {hourly_temps[21]}F - {interpret_wmo_code(hourly_codes[21])}", fill=0)
    else:
        draw.text((20, 40), "Weather data missing or unavailable.", fill=0)

    # --- BOTTOM LEFT: TOMORROW'S WEATHER ---
    draw.text((20, 255), "TOMORROW'S WEATHER", fill=0)
    if weather and "daily" in weather:
        max_t_tom = weather["daily"]["temperature_2m_max"][1]
        min_t_tom = weather["daily"]["temperature_2m_min"][1]
        cond_tom = interpret_wmo_code(weather["daily"]["weather_code"][1])
        
        draw.text((20, 290), f"Forecast: {cond_tom}", fill=0)
        draw.text((20, 330), f"High: {max_t_tom}F", fill=0)
        draw.text((20, 370), f"Low: {min_t_tom}F", fill=0)

    # --- RIGHT PANEL: TIDES (TODAY & TOMORROW) ---
    draw.text((420, 15), f"TIDES: TODAY ({today_str})", fill=0)
    draw.text((420, 255), f"TIDES: TOMORROW ({tomorrow_str})", fill=0)

    today_y = 50
    tomorrow_y = 290

    if tides:
        for t in tides:
            t_time_str = t["t"]  # Structure from API: "2026-06-27 04:12"
            t_type = "HIGH" if t["type"] == "H" else "LOW"
            t_height = t["v"]

            # Fixed: Safely isolate only the HH:MM time section out of the text string
            time_part = t_time_str.split(" ")[1] if " " in t_time_str else t_time_str
            display_text = f"{time_part} - {t_type} ({t_height} ft)"

            # Fixed: Use date substring checking to match layout panels cleanly
            if t_time_str.startswith(today_str):
                if today_y < 220:
                    draw.text((420, today_y), display_text, fill=0)
                    today_y += 35
            elif t_time_str.startswith(tomorrow_str):
                if tomorrow_y < 460:
                    draw.text((420, tomorrow_y), display_text, fill=0)
                    tomorrow_y += 35
    else:
        draw.text((420, 50), "No tide predictions available.", fill=0)

    # Add a time update indicator stamp at the baseline boundary
    draw.text((10, 460), f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", fill=0)

    # Output clean 1-bit binary image layout
    img_bw = img.convert("1")
    img_bw.save("dashboard.png")
    print("Dashboard snapshot 'dashboard.png' updated successfully.")


if __name__ == "__main__":
    tide_predictions = get_tide_data()
    weather_forecast = get_weather_data()
    draw_dashboard(tide_predictions, weather_forecast)
