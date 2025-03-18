import re
import requests
from bs4 import BeautifulSoup

# The URL to the official NOAA/NWS page for Chicago (LOT region).
URL = "https://forecast.weather.gov/product.php?issuedby=lot&product=omr&site=lot"

def fetch_chicago_shore_temp():
    """
    Fetches the Chicago Shore temperature in Fahrenheit from the NOAA OMR report.
    Returns an integer temperature or None if not found.
    """
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    text_content = soup.get_text()

    # Look for a line referencing "CHICAGO SHORE" and capturing a Fahrenheit temperature.
    pattern = re.compile(r"CHICAGO SHORE.*?(\d+)\s*F", re.IGNORECASE | re.DOTALL)
    match = pattern.search(text_content)
    if match:
        try:
            temp_f = int(match.group(1))
            return temp_f
        except ValueError:
            pass
    return None

def main():
    temp = fetch_chicago_shore_temp()
    if temp is None:
        print("Could not parse Chicago shore temperature.")
        return

    print(f"Current Chicago Shore Temperature: {temp}°F")

    # If above 50, we print "ALERT" for the Actions log
    if temp > 50:
        print("ALERT: Temperature is above 50°F!")
    else:
        print("Temperature is at or below 50°F.")

if __name__ == "__main__":
    main()
