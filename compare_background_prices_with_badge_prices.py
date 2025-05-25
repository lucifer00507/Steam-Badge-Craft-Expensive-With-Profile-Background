import requests
from bs4 import BeautifulSoup
import re
import json
import csv
import time
import os
import sys

# Define the path for the output CSV files in the current working directory
drive_folder = '.' # Current directory

os.makedirs(drive_folder, exist_ok=True) # Create the folder if it doesn't exist

# Main alert CSV
output_csv_file = os.path.join(drive_folder, "steam_background_alerts.csv")
# Comprehensive log of all processed games
all_processed_games_file = os.path.join(drive_folder, "all_processed_games.csv")

# Global variables to hold file objects and writers, allowing re-opening
alert_csvfile_global = None
all_processed_csvfile_global = None
alert_csv_writer_global = None
all_processed_csv_writer_global = None

def open_csv_files(output_csv_path, all_processed_games_path, alert_file_exists, all_processed_file_exists):
    """Opens or re-opens the CSV files and initializes writers."""
    global alert_csvfile_global, all_processed_csvfile_global, alert_csv_writer_global, all_processed_csv_writer_global

    try:
        # Close existing files if they are open and not already closed
        if alert_csvfile_global and not alert_csvfile_global.closed:
            alert_csvfile_global.close()
        if all_processed_csvfile_global and not all_processed_csvfile_global.closed:
            all_processed_csvfile_global.close()

        alert_csvfile_global = open(output_csv_path, 'a', newline='', encoding='utf-8')
        all_processed_csvfile_global = open(all_processed_games_path, 'a', newline='', encoding='utf-8') # Always open in append mode

        alert_csv_writer_global = csv.writer(alert_csvfile_global)
        all_processed_csv_writer_global = csv.writer(all_processed_csvfile_global)

        # Write header for the main alert CSV ONLY if the file is new or empty
        if not alert_file_exists or os.stat(output_csv_path).st_size == 0:
            alert_csv_writer_global.writerow([
                "game name", 
                "app id", 
                "badge price", 
                "highest background price", 
                "buy order price", 
                "highest background steam market link",
                "steam card exchange link"
            ])
        
        # Write header for the comprehensive processed games log ONLY if the file is new or empty
        # This check is important because we always open in 'a' mode to avoid truncating
        if not all_processed_file_exists or os.stat(all_processed_games_path).st_size == 0:
            all_processed_csv_writer_global.writerow(["AppID"])
        
        print("CSV files successfully opened/re-opened.")
        return True
    except Exception as e:
        print(f"ERROR: Failed to open/re-open CSV files: {e}")
        return False

def get_steam_market_buy_listings(market_url):
    """
    Fetches the Steam Community Market page for a given item to extract the item_nameid,
    then queries the Steam Market API for buy order details with infinite retry logic.
    """
    if not market_url:
        return None, None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    retry_delay_seconds = 10

    item_nameid = None
    attempt = 0
    while True:
        attempt += 1
        try:
            response = requests.get(market_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            item_nameid_match = re.search(r'Market_LoadOrderSpread\( (\d+) \);', response.text)
            if item_nameid_match:
                item_nameid = item_nameid_match.group(1)
                break
            else:
                print(f"Attempt {attempt}: Could not find item_nameid on Steam Market page {market_url}. Retrying in {retry_delay_seconds * attempt} seconds...")
                time.sleep(retry_delay_seconds * attempt)
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt}: Error accessing Steam Market page {market_url}: {e}. Retrying in {retry_delay_seconds * attempt} seconds...")
            time.sleep(retry_delay_seconds * attempt)
        except Exception as e:
            print(f"Attempt {attempt}: Unexpected error during initial market page fetch: {e}. Retrying in {retry_delay_seconds * attempt} seconds...")
            time.sleep(retry_delay_seconds * attempt)

    if not item_nameid:
        print(f"Failed to find item_nameid for {market_url} after multiple attempts.")
        return None, None

    if item_nameid:
        histogram_api_url = f"https://steamcommunity.com/market/itemordershistogram?country=US&language=english&currency=1&item_nameid={item_nameid}"
        
        attempt = 0
        while True:
            attempt += 1
            try:
                api_response = requests.get(histogram_api_url, headers=headers, timeout=10)
                api_response.raise_for_status()
                json_data = api_response.json()

                num_buyers = 0
                buy_amount = 0.0

                if json_data.get('success') == 1:
                    buy_amount_raw = json_data.get('highest_buy_order')
                    if buy_amount_raw:
                        try:
                            buy_amount = float(buy_amount_raw) / 100.0 
                        except ValueError:
                            print(f"Error parsing highest_buy_order amount: {buy_amount_raw}")
                            buy_amount = 0.0

                    buy_order_graph = json_data.get('buy_order_graph')
                    if buy_order_graph and isinstance(buy_order_graph, list):
                        if len(buy_order_graph) > 0:
                            num_buyers = int(buy_order_graph[-1][1]) 
                        else:
                            num_buyers = 0
                    else:
                        print(f"Buy order graph not found or is empty for item_nameid {item_nameid}.")
                        num_buyers = 0

                    return num_buyers, buy_amount
                else:
                    print(f"Attempt {attempt}: Steam Market API response not successful for item_nameid {item_nameid}: {json_data.get('success')}. Retrying in {retry_delay_seconds * attempt} seconds...")
                    time.sleep(retry_delay_seconds * attempt)
            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt}: Error accessing Steam Market API for item_nameid {item_nameid}: {e}. Retrying in {retry_delay_seconds * attempt} seconds...")
                time.sleep(retry_delay_seconds * attempt)
            except json.JSONDecodeError as e:
                print(f"Attempt {attempt}: Error decoding JSON from Steam Market API for item_nameid {item_nameid}: {e}. Retrying in {retry_delay_seconds * attempt} seconds...")
                time.sleep(retry_delay_seconds * attempt)
            except Exception as e:
                print(f"Attempt {attempt}: Unexpected error during API fetch for item_nameid {item_nameid}: {e}. Retrying in {retry_delay_seconds * attempt} seconds...")
                time.sleep(retry_delay_seconds * attempt)
    
    print(f"Failed to retrieve buy listings for {market_url} after multiple attempts.")
    return None, None

def get_highest_background_price(appid):
    """
    Fetches the background prices for a given Steam AppID from Steam Card Exchange
    and returns the highest price found along with its Steam Market URL and the SCE game page URL.
    """
    if not isinstance(appid, int):
        return None, None, None, None

    url = f"https://www.steamcardexchange.net/index.php?gamepage-appid-{appid}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    retry_delay_seconds = 10

    attempt = 0
    while True:
        attempt += 1
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt}: Error accessing page for AppID {appid}: {e}. Retrying in {retry_delay_seconds * attempt} seconds...")
            time.sleep(retry_delay_seconds * attempt)
        except Exception as e:
            print(f"Attempt {attempt}: Unexpected error during game page fetch for AppID {appid}: {e}. Retrying in {retry_delay_seconds * attempt} seconds...")
            time.sleep(retry_delay_seconds * attempt)

    soup = BeautifulSoup(response.text, 'html.parser')
    
    game_title_element = soup.find('div', class_='gameTitle')
    game_title = game_title_element.text.strip() if game_title_element else f"Game (AppID: {appid})"

    highest_price = None
    highest_price_market_url = None
    
    backgrounds_link = soup.find('a', string=re.compile(r'Backgrounds'))
    
    if backgrounds_link:
        parent_div_of_link = backgrounds_link.find_parent('div', class_='bg-gray-dark')
        
        if parent_div_of_link:
            backgrounds_grid = parent_div_of_link.find_next_sibling('div', class_='grid')
            
            if backgrounds_grid:
                price_links = backgrounds_grid.find_all('a', class_='btn-primary', string=re.compile(r'Price: \$\d+\.\d{2}'))
                
                for link in price_links:
                    price_text = link.get_text(strip=True)
                    prices_found = re.findall(r'\$(\d+\.\d{2})', price_text)
                    
                    for price_str in prices_found:
                        try:
                            price = float(price_str)
                            if highest_price is None or price > highest_price:
                                highest_price = price
                                highest_price_market_url = link.get('href')
                        except ValueError:
                            continue
            else:
                pass
        else:
            pass
    else:
        pass

    if highest_price is not None:
        return highest_price, game_title, highest_price_market_url, url
    else:
        return None, game_title, None, url

def get_games_from_badgeprices_table(url="https://www.steamcardexchange.net/index.php?badgeprices"):
    """
    Retrieves game data (AppID, title, and badge price) directly from the
    Steam Card Exchange API endpoint that feeds the badge pricelist table with retry logic.
    """
    api_url = "https://www.steamcardexchange.net/api/request.php?GetBadgePrices_Guest"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }
    games_data = []

    retry_delay_seconds = 10

    attempt = 0
    while True:
        attempt += 1
        try:
            response = requests.get(api_url, headers=headers, timeout=15)
            response.raise_for_status()
            json_data = response.json()

            if 'data' in json_data and isinstance(json_data['data'], list):
                for row in json_data['data']:
                    if len(row) >= 3 and isinstance(row[0], list) and len(row[0]) >= 2:
                        game_appid = int(row[0][0])
                        game_title = row[0][1]
                        badge_price_str = row[2] 

                        try:
                            badge_price = float(badge_price_str.replace('$', ''))
                            games_data.append({
                                'game_title': game_title,
                                'appid': game_appid,
                                'badge_price': badge_price
                            })
                        except ValueError:
                            continue
                    else:
                        pass
                break
            else:
                print(f"Attempt {attempt}: API response 'data' key not found or is not a list. Retrying in {retry_delay_seconds * attempt} seconds...")
                time.sleep(retry_delay_seconds * attempt)
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt}: Error accessing the badge prices API: {e}. Retrying in {retry_delay_seconds * attempt} seconds...")
            time.sleep(retry_delay_seconds * attempt)
        except json.JSONDecodeError as e:
            print(f"Attempt {attempt}: Error decoding JSON from API response: {e}. Retrying in {retry_delay_seconds * attempt} seconds...")
            time.sleep(retry_delay_seconds * attempt)
        except Exception as e:
            print(f"Attempt {attempt}: Unexpected error during badge prices API fetch: {e}. Retrying in {retry_delay_seconds * attempt} seconds...")
            time.sleep(retry_delay_seconds * attempt)
    
    return games_data

# --- Main execution block ---
if __name__ == "__main__":
    print("--- Starting to scrape game list from badge prices table ---")
    
    # The drive_folder is already set to '.' or a specific path above based on IS_COLAB.
    # os.makedirs(drive_folder, exist_ok=True) is already called above.

    # Load already processed app IDs from the comprehensive log file
    processed_app_ids = set()
    all_processed_file_exists = os.path.exists(all_processed_games_file)
    if all_processed_file_exists:
        print(f"Loading previously processed game IDs from '{all_processed_games_file}'...")
        try:
            with open(all_processed_games_file, 'r', newline='', encoding='utf-8') as csvfile:
                csv_reader = csv.reader(csvfile)
                header = next(csv_reader, None)
                if header and "AppID" in header:
                    app_id_col_index = header.index("AppID")
                    for row in csv_reader:
                        if len(row) > app_id_col_index:
                            try:
                                processed_app_ids.add(int(row[app_id_col_index]))
                            except ValueError:
                                continue
                else:
                    print(f"Warning: '{all_processed_games_file}' is missing 'AppID' header or is empty. Cannot skip previously processed games efficiently.")
            print(f"Loaded {len(processed_app_ids)} previously processed game IDs.")
        except Exception as e:
            print(f"Error loading existing comprehensive processed games CSV: {e}. Starting with an empty list of processed games.")
            processed_app_ids = set()
    else:
        print("No comprehensive log file found. Starting fresh for all games.")
    
    games_from_list = get_games_from_badgeprices_table()
    
    if not games_from_list:
        print("No games found in the badge prices table via API. Please check the API URL or response structure. Exiting.")
    else:
        print(f"Successfully retrieved {len(games_from_list)} games from the badge prices API.")
        print("\n--- Comparing Highest Background Prices with Badge Prices ---")
        print("Note: Comparing highest background price from game page against 'Price' from the API data.")
        print("      The 'Price' from the API is used as a reference as background prices are not in the initial list.")
        print("-" * 70)

        # Initialize global file objects and writers
        alert_file_exists = os.path.exists(output_csv_file)
        if not open_csv_files(output_csv_file, all_processed_games_file, alert_file_exists, all_processed_file_exists):
            print("Fatal: Could not open CSV files. Exiting script.")
            sys.exit(1)

        games_to_process = games_from_list
        print(f"Processing all {len(games_to_process)} games and writing alerts to '{output_csv_file}' and log to '{all_processed_games_file}'...")

        for game_info in games_to_process:
            game_title_list = game_info['game_title']
            appid_list = game_info['appid']
            badge_price_list = game_info['badge_price']

            if appid_list in processed_app_ids:
                print(f"Skipping '{game_title_list}' (AppID: {appid_list}) - already processed in a previous run.")
                continue

            # Log to all_processed_games.csv with retry
            log_attempt = 0
            while True:
                log_attempt += 1
                try:
                    all_processed_csv_writer_global.writerow([appid_list])
                    all_processed_csvfile_global.flush()
                    break
                except (IOError, ValueError, Exception) as e:
                    print(f"Attempt {log_attempt}: Warning: Could not write AppID {appid_list} to all_processed_games.csv log file: {e}. Attempting to re-open files and retry in {retry_delay_seconds} seconds...")
                    time.sleep(retry_delay_seconds)
                    current_alert_file_exists = os.path.exists(output_csv_file)
                    current_all_processed_file_exists = os.path.exists(all_processed_games_file)
                    if not open_csv_files(output_csv_file, all_processed_games_file, current_alert_file_exists, current_all_processed_file_exists):
                        print("Fatal: Could not re-open CSV files for logging. Exiting script.")
                        sys.exit(1)
                    if log_attempt >= 3:
                        print(f"Failed to log AppID {appid_list} to all_processed_games.csv after multiple attempts. Continuing without logging this game.")
                        break

            processed_app_ids.add(appid_list)

            highest_bg_price, game_title_page, highest_bg_market_url, sce_game_page_url = get_highest_background_price(appid_list)

            if highest_bg_price is not None and highest_bg_price > badge_price_list:
                buy_order_price = None
                
                if highest_bg_market_url:
                    num_buyers, buy_amount = get_steam_market_buy_listings(highest_bg_market_url)
                    if num_buyers is not None and buy_amount is not None:
                        buy_order_price = buy_amount
                        print(f"\nChecking '{game_title_list}' (AppID: {appid_list}, List Price: ${badge_price_list:.2f})...")
                        print(f"  Highest background price found on game page: ${highest_bg_price:.2f}")
                        print(f"  >>> ALERT: Highest background price (${highest_bg_price:.2f}) for '{game_title_page}' is HIGHER than its List Price (${badge_price_list:.2f}) from the table!")
                        print(f"    Fetching Steam Market buy listings for: {highest_bg_market_url}")
                        print(f"    Steam Market Buy Orders: {num_buyers} requests to buy at ${buy_amount:.2f} or lower.")
                        print("-" * 70)
                    else:
                        print(f"\nChecking '{game_title_list}' (AppID: {appid_list}, List Price: ${badge_price_list:.2f})...")
                        print(f"  Highest background price found on game page: ${highest_bg_price:.2f}")
                        print(f"  >>> ALERT: Highest background price (${highest_bg_price:.2f}) for '{game_title_page}' is HIGHER than its List Price (${badge_price_list:.2f}) from the table!")
                        print(f"    Fetching Steam Market buy listings for: {highest_bg_market_url}")
                        print("    Could not retrieve Steam Market buy order details.")
                        print("-" * 70)
                else:
                    print(f"\nChecking '{game_title_list}' (AppID: {appid_list}, List Price: ${badge_price_list:.2f})...")
                    print(f"  Highest background price found on game page: ${highest_bg_price:.2f}")
                    print(f"  >>> ALERT: Highest background price (${highest_bg_price:.2f}) for '{game_title_page}' is HIGHER than its List Price (${badge_price_list:.2f}) from the table!")
                    print("    No Steam Market URL found for this background.")
                    print("-" * 70)
                
                write_attempt = 0
                while True:
                    write_attempt += 1
                    try:
                        alert_csv_writer_global.writerow([
                            game_title_list,
                            appid_list,
                            f"${badge_price_list:.2f}",
                            f"${highest_bg_price:.2f}",
                            f"${buy_order_price:.2f}" if buy_order_price is not None else "N/A",
                            highest_bg_market_url if highest_bg_market_url else "N/A",
                            sce_game_page_url
                        ])
                        alert_csvfile_global.flush()
                        break
                    except (IOError, ValueError, Exception) as e:
                        print(f"Attempt {write_attempt}: CRITICAL ERROR: Failed to write alert row for AppID {appid_list}. File might be closed. Error: {e}. Attempting to re-open files and retry in {retry_delay_seconds} seconds...")
                        time.sleep(retry_delay_seconds)
                        current_alert_file_exists = os.path.exists(output_csv_file)
                        current_all_processed_file_exists = os.path.exists(all_processed_games_file)
                        if not open_csv_files(output_csv_file, all_processed_games_file, current_alert_file_exists, current_all_processed_file_exists):
                            print("Fatal: Could not re-open CSV files for alerts. Exiting script.")
                            sys.exit(1)
                        if write_attempt >= 3:
                            print(f"Failed to write alert for AppID {appid_list} after multiple attempts. Skipping this alert.")
                            break

        if alert_csvfile_global and not alert_csvfile_global.closed:
            alert_csvfile_global.close()
        if all_processed_csvfile_global and not all_processed_csvfile_global.closed:
            all_processed_csvfile_global.close()
        
        print(f"\n--- Alert data written to '{output_csv_file}' ---")
        print(f"--- All processed AppIDs logged to '{all_processed_games_file}' ---")

    print("\n--- Script execution finished ---")
