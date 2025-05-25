# generated with google gemini 2.5 flash ❤️

# Steam-Badge-Craft-Expensive-With-Profile-Background

A Python script designed to identify potential arbitrage opportunities on Steam by comparing Steam game badge crafting prices with the highest available prices for their profile backgrounds on the Steam Community Market. It fetches data from Steam Card Exchange and the Steam Market, alerts you to profitable differences, and manages processed game data persistently.

## ✨ Features

* **Badge Price Fetching:** Retrieves the current crafting prices for Steam game badges from Steam Card Exchange.

* **Highest Background Price Discovery:** For each game, it navigates to its dedicated page on Steam Card Exchange to find the highest priced profile background available.

* **Price Comparison & Alerting:** Compares the badge crafting price to the highest background price. If the background price is significantly higher, it triggers an alert.

* **Steam Market Buy Order Integration:** For alerted games, it fetches real-time buy order data (highest buy price and quantity) from the Steam Community Market API.

* **Console Output:** Provides immediate alerts and details directly in your terminal/Colab output for games meeting the alert criteria.

* **Dual CSV Export for Data Management:**

    * `steam_background_alerts.csv`: Stores detailed information (Game Name, AppID, Badge Price, Highest Background Price, Buy Order Price, Steam Market Link, **Steam Card Exchange Link**) for games that meet the alert criteria.

    * `all_processed_games.csv`: A comprehensive log of all AppIDs the script has *attempted* to process. This file is used internally for efficient skipping.

* **Robust Retry Mechanism:** Implements infinite retry loops with an increasing delay (starting at 10 seconds) for all network requests to handle rate-limiting or temporary network issues from external websites/APIs.

* **Efficient Persistent Data Saving:**

    * The script automatically loads previously processed game AppIDs from `all_processed_games.csv` on subsequent runs.

    * **Crucially, it skips web requests for games that have already been processed** (i.e., present in `all_processed_games.csv`), significantly speeding up execution on repeated runs.

    * CSV files are opened in append mode, ensuring new results are added without overwriting previous data.

    * **Local Version (`.py`):** Saves files in the script's directory.

    * **Google Colab Version (`.ipynb`):** Integrates with Google Drive to save files persistently within your Drive.

## 🚀 How It Works

1.  The script first loads a list of `AppID`s from `all_processed_games.csv` (if it exists) in the script's directory (for local runs) or from your mounted Google Drive (for Colab runs) to identify games that have already been checked.

2.  It then fetches a comprehensive list of games and their current badge crafting prices from the Steam Card Exchange API.

3.  For each game in the list:

    * It first checks if the game's `AppID` is in the `processed_app_ids` set. If it is, the game is skipped immediately without making any web requests.

    * If the game is new, its `AppID` is logged to `all_processed_games.csv`.

    * It then visits the game's specific page on Steam Card Exchange to scrape the highest listed price for any of its profile backgrounds.

    * It compares this highest background price with the game's badge crafting price.

    * If the highest background price is strictly greater than the badge price, it considers this a potential opportunity.

4.  For games identified as potential opportunities, it attempts to fetch live "buy order" data from the Steam Community Market API for that specific background.

5.  All relevant data for alerted games (including name, AppID, prices, Steam Market link, and Steam Card Exchange link) is printed to the console and appended to `steam_background_alerts.csv`.

## 📋 Prerequisites

Before running the script, ensure you have:

* **Python 3.x** installed.

* **pip** (Python package installer).

## 🛠️ Installation

1.  **Clone the repository (or copy the code):**

    ```bash
    git clone [https://github.com/YourUsername/SteamBackgroundPriceAlert.git](https://github.com/YourUsername/SteamBackgroundPriceAlert.git)
    cd SteamBackgroundPriceAlert
    ```
    (Replace `YourUsername` with your actual GitHub username if you fork it)

2.  **Install the required Python libraries:**

    ```bash
    pip install requests beautifulsoup4
    ```

## 🏃 Usage

This project provides two versions of the script: a `.py` file for local execution and a `.ipynb` (Jupyter/Colab notebook) file for use in Google Colab.

### ⚙️ Running Locally (`steam_price_alert_local.py`)

This version saves `steam_background_alerts.csv` and `all_processed_games.csv` directly in the same directory as the script.

1.  **Save the script:** Save the Python code as `steam_price_alert_local.py` in your desired directory.

2.  **Navigate to the directory:** Open your terminal or command prompt and navigate to the directory where you saved the script.

3.  **Run the script:**

    ```bash
    python steam_price_alert_local.py
    ```

### ☁️ Running on Google Colab (`steam_price_alert_colab.ipynb`)

This version integrates with Google Drive for persistent storage of `steam_background_alerts.csv` and `all_processed_games.csv`.

1.  **Open Google Colab:** Go to [colab.research.google.com](https://colab.research.google.com/).

2.  **Create a New Notebook:** Click `File > New notebook`.

3.  **Copy the Code:** Copy the entire Python script (the one with Google Drive integration) into the Colab notebook cell.

4.  **Save as .ipynb:** Save the notebook (e.g., as `steam_price_alert_colab.ipynb`).

5.  **Run the Cell:** Click the "Run" button (play icon) next to the cell, or press `Shift + Enter`.

6.  **Authorize Google Drive:**

    * The first time you run it, you will be prompted to authorize Google Drive access. Click the link provided in the output.

    * Select your Google account, grant the necessary permissions.

    * Copy the authorization code provided by Google back into the input box in Colab and press Enter.

7.  **Monitor Output:** The script will start fetching data and printing alerts to the console. The CSV files will be created/updated in a folder named `SteamAlerts` within your Google Drive's `My Drive` (e.g., `/content/drive/My Drive/SteamAlerts/`).

## 📊 Output

### Console Alerts

When a potential opportunity is found, output similar to this will appear in your console:

Checking 'Arcane Raise' (AppID: 603750, List Price: $1.07)...
  Highest background price found on game page: $11.46
  >>> ALERT: Highest background price ($11.46) for 'Game (AppID: 603750)' is HIGHER than its List Price ($1.07) from the table!
    Fetching Steam Market buy listings for: https://steamcommunity.com/market/listings/753/603750-A%20Deep%20Black
    Steam Market Buy Orders: 380 requests to buy at $8.60 or lower.
----------------------------------------------------------------------

You will also see "Skipping..." messages for games that have been processed in previous runs, indicating that no new web requests are being made for them.

### CSV Files

#### `steam_background_alerts.csv`

This file will contain detailed information for games where the highest background price is greater than the badge price.

| Column Name | Description |
| :---------- | :---------- |
| `game name` | The name of the game. |
| `app id` | The Steam Application ID. |
| `badge price` | The crafting price of the game's badge (your initial investment). |
| `highest background price` | The highest price found for any of the game's profile backgrounds on Steam Card Exchange. |
| `buy order price` | The highest active buy order price on the Steam Market for the identified background. |
| `highest background steam market link` | A direct link to the Steam Community Market listing for the specific background. |
| `steam card exchange link` | A direct link to the game's page on Steam Card Exchange. |

#### `all_processed_games.csv`

This file is a simple log used internally by the script to track which AppIDs have already been processed. It contains a single column:

| Column Name | Description |
| :---------- | :---------- |
| `AppID` | The Steam Application ID of a processed game. |

## ⚠️ Important Notes & Disclaimer

* **External Dependencies:** This script relies on data provided by `steamcardexchange.net` and `steamcommunity.com` (Steam Market API). Changes to their website structure or API endpoints may break the script.

* **Rate Limiting:** While robust infinite retry logic with exponential backoff is implemented, excessive requests may still lead to temporary IP bans or CAPTCHAs from Steam or Steam Card Exchange. Use responsibly.

* **Market Volatility:** Prices on the Steam Market are highly volatile. The prices fetched are snapshots and can change rapidly.

* **Profitability:** The "buy order price" indicates what people are *currently* willing to pay. Actual sale prices after market fees might be lower. This script identifies *potential* opportunities, not guaranteed profits.

* **Manual Verification:** Always manually verify prices and market conditions on Steam before making any purchasing decisions.

* **Google Drive Permissions:** (Relevant for Colab users) Ensure you grant the necessary permissions when prompted by Google Colab to allow the script to create and write to files in your Google Drive.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to open an issue or submit a pull request.

## 📄 License
