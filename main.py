import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import requests
import json

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()
sheet_url = os.getenv("GOOGLE_SHEET_URL")
credentials_path = os.getenv("GOOGLE_CREDENTIALS")
api_key = os.getenv("OPENROUTER_API_KEY")

# -----------------------------
# Google Sheets authorization
# -----------------------------
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_url(sheet_url)

# -----------------------------
# Read Sheet 1: Centres
# -----------------------------
sheet1 = spreadsheet.get_worksheet(0)
sheet1_values = sheet1.get_all_values()
df_centres = pd.DataFrame(sheet1_values[1:], columns=sheet1_values[0])
df_centres['HS Code'] = pd.to_numeric(df_centres['HS Code'])
df_centres['Centers'] = pd.to_numeric(df_centres['Centers'])

# -----------------------------
# Read Sheet 2: Commods
# -----------------------------
sheet2 = spreadsheet.get_worksheet(1)
sheet2_values = sheet2.get_all_values()
df_commods = pd.DataFrame(sheet2_values[1:], columns=sheet2_values[0])
df_commods['HS Code'] = pd.to_numeric(df_commods['HS Code'])

# -----------------------------
# Function to call LLM via OpenRouter GPT-4o-mini
# -----------------------------
def get_total_production_from_llm(commod_name):
    prompt = f"""
    Provide the most recent estimated total production of {commod_name} in India
    for the 2023–2024 crop year, based on government or FAO statistics.
    Return only a numeric value in million tons (e.g., rice ~140–150).
    Do not return unrealistically large numbers. Only provide the numeric value.
    """
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o-mini",
        "messages":[{"role":"user","content":prompt}],
        "temperature":0.0
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print("API Status Code:", response.status_code)
    print("API Response Text:", response.text)
    
    try:
        response_json = response.json()
    except json.JSONDecodeError:
        raise ValueError("Error decoding JSON from API response")
    
    if 'error' in response_json:
        raise ValueError(f"OpenRouter API returned error: {response_json['error']}")
    
    if 'choices' not in response_json:
        raise ValueError("'choices' not found in API response")
    
    llm_output = response_json['choices'][0]['message']['content']
    print("Raw LLM output:", llm_output)
    
    # Extract numeric value
    numeric_str = ''.join(filter(lambda x: x.isdigit() or x == '.', llm_output))
    if not numeric_str:
        raise ValueError("LLM did not return a numeric value.")
    
    total_value = float(numeric_str)
    
    # Safety check: realistic max production in million tons
    if total_value > 500:
        print("Warning: LLM output seems too high. Using 145 million tons as fallback.")
        total_value = 145  # fallback realistic value
    
    return total_value

# -----------------------------
# Main execution
# -----------------------------
def main():
    commod_name = input("Enter commod name (e.g., rice, wheat): ").strip().lower()
    
    # Map commod name to HS Code
    hs_row = df_commods[df_commods['Name'].str.lower() == commod_name]
    if hs_row.empty:
        print(f"Commod '{commod_name}' not found in Sheet 2")
        return
    hs_code = hs_row['HS Code'].values[0]
    
    # Filter centres producing this HS Code
    df_filtered = df_centres[df_centres['HS Code'] == hs_code]
    num_centres = df_filtered.shape[0]
    centres_list = df_filtered['Centers'].tolist()
    
    if num_centres == 0:
        print(f"No centres found producing {commod_name}")
        return
    
    # Get total production (million tons)
    total_production_million = get_total_production_from_llm(commod_name)
    
    # Convert to tons
    total_production_tons = total_production_million * 1_000_000
    per_centre_production = total_production_tons / num_centres
    
    # Output
    print("\n------ Production Summary ------")
    print(f"Commod Name: {commod_name}")
    print(f"HS Code: {hs_code}")
    print(f"Number of centres: {num_centres}")
    print(f"Total production (LLM, in million tons): {total_production_million}")
    print(f"Total production (in tons): {total_production_tons:,.0f}")
    print(f"Per-centre production (tons): {per_centre_production:,.2f}")
    print("--------------------------------")

if __name__ == "__main__":
    main()


# meenakshi.s@mintelligence.io  