import os
import time
from datetime import datetime, timedelta, timezone

import kaggle
import pandas as pd
import requests


# Function to fetch data from Bitstamp API
def fetch_bitstamp_data(currency_pair, start_timestamp, end_timestamp, step=86400, limit=1000):
    url = f"https://www.bitstamp.net/api/v2/ohlc/{currency_pair}/"
    params = {
        "step": step,
        "start": int(start_timestamp),
        "end": int(end_timestamp),
        "limit": limit,
    }
    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        return response.json().get("data", {}).get("ohlc", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return []


# Download the latest dataset from Kaggle
def download_latest_dataset(dataset_slug):
    kaggle.api.dataset_download_files(dataset_slug, path="upload", unzip=True)


# Check for missing data

def check_missing_data(existing_data_filename):
    df = pd.read_csv(existing_data_filename)

    if "Timestamp" not in df.columns or df.empty:
        print("⚠️ CSV is empty or missing 'Timestamp'. Starting fresh from Jan 1, 2012.")
        last_timestamp = int(datetime(2012, 1, 1, tzinfo=timezone.utc).timestamp())
    else:
        df["Timestamp"] = pd.to_numeric(df["Timestamp"], errors="coerce")
        if df["Timestamp"].dropna().empty:
            print("⚠️ All Timestamps are NaN. Starting fresh from Jan 1, 2012.")
            last_timestamp = int(datetime(2012, 1, 1, tzinfo=timezone.utc).timestamp())
        else:
            last_timestamp = df["Timestamp"].max()

    current_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    current_timestamp = int(current_time.timestamp())

    last_datetime = datetime.fromtimestamp(last_timestamp, tz=timezone.utc)
    print(f"Last data point: {last_datetime} (Unix: {last_timestamp})")
    print(f"Current time: {current_time} (Unix: {current_timestamp})")

    if current_timestamp > last_timestamp:
        print(f"Gap of {current_timestamp - last_timestamp} seconds detected.")
        return last_timestamp, current_timestamp
    else:
        print("Dataset is up to date.")
        return None, None

# Fetch and append missing data
def fetch_and_append_missing_data(currency_pair, last_timestamp, current_timestamp, existing_data_filename, output_filename):
    df_existing = pd.read_csv(existing_data_filename)
    df_existing["Timestamp"] = pd.to_numeric(df_existing["Timestamp"], errors="coerce")

    time_chunks = []
    current_start = last_timestamp
    chunk_size = 1000 * 60  # 1000 minutes in seconds

    while current_start < current_timestamp:
        current_end = min(current_start + chunk_size, current_timestamp)
        time_chunks.append((current_start, current_end))
        current_start = current_end

    all_new_data = []
    for i, (chunk_start, chunk_end) in enumerate(time_chunks):
        print(f"Fetching chunk {i+1}/{len(time_chunks)}: {datetime.fromtimestamp(chunk_start, tz=timezone.utc)} → {datetime.fromtimestamp(chunk_end, tz=timezone.utc)}")
        chunk_data = fetch_bitstamp_data(currency_pair, chunk_start, chunk_end, step=86400)
        if chunk_data:
            df_chunk = pd.DataFrame(chunk_data)
            df_chunk["timestamp"] = pd.to_numeric(df_chunk["timestamp"], errors="coerce")
            df_chunk.columns = ["Timestamp", "Open", "High", "Low", "Close", "Volume"]
            all_new_data.append(df_chunk)
        else:
            print("  - No data in this chunk")
        time.sleep(1)

    if all_new_data:
        df_new = pd.concat(all_new_data, ignore_index=True)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined = df_combined.drop_duplicates(subset="Timestamp", keep="first")
        df_combined = df_combined.sort_values(by="Timestamp", ascending=True)
        df_combined.to_csv(output_filename, index=False)
        print(f"✅ Updated dataset saved to {output_filename}")
    else:
        print("No new data found. Writing original file again.")
        df_existing.to_csv(output_filename, index=False)


# Main execution
if __name__ == "__main__":
    dataset_slug = "martintorres54/btc-price"
    currency_pair = "btcusd"
    upload_dir = "upload"

    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    print("📥 Downloading dataset from Kaggle...")
    download_latest_dataset(dataset_slug)

    # Find any CSV file in the upload/ folder
    csv_files = []
    for root, dirs, files in os.walk(upload_dir):
        for f in files:
            if f.endswith(".csv"):
                csv_files.append(os.path.join(root, f))

    if not csv_files:
        raise FileNotFoundError("❌ No CSV file found in 'upload/' after downloading from Kaggle.")

    existing_data_filename = csv_files[0]
    output_filename = existing_data_filename
    print(f"✅ Using dataset file: {existing_data_filename}")
    print(f"⏰ Current time: {datetime.now(timezone.utc)}")

    # Check and update
    print("🔎 Checking for missing data...")
    last_ts, current_ts = check_missing_data(existing_data_filename)

    if last_ts is not None and current_ts is not None:
        print("🚀 Fetching new data...")
        fetch_and_append_missing_data(currency_pair, last_ts, current_ts, existing_data_filename, output_filename)
    else:
        print("✅ No new data needed.")


