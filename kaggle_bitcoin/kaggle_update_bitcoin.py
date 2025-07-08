import os
from kaggle.api.kaggle_api_extended import KaggleApi

# === CONFIG ===
dataset_slug = "martintorres54/btc-price"
upload_dir = "upload"

# === Ensure upload folder exists ===
if not os.path.exists(upload_dir):
    raise FileNotFoundError("❌ 'upload/' folder not found in the repo.")

# === Find the existing CSV file ===
csv_files = []
for root, dirs, files in os.walk(upload_dir):
    for f in files:
        if f.endswith(".csv"):
            csv_files.append(os.path.join(root, f))

if not csv_files:
    raise FileNotFoundError("❌ No CSV file found in 'upload/' — cannot upload.")

existing_data_filename = csv_files[0]
print(f"✅ Found dataset file: {existing_data_filename}")

# === Upload to Kaggle ===
print("📤 Uploading to Kaggle...")

api = KaggleApi()
api.authenticate()

api.dataset_create_version(
    dataset_slug=dataset_slug,
    version_notes="Initial upload from GitHub Actions",
    delete_old_versions=True
)

print("✅ Upload complete.")
