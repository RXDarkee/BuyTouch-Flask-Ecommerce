import os
from dotenv import load_dotenv

load_dotenv()

# Base directory of project (absolute path of current script)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Ensure 'instance' folder exists in the project root
INSTANCE_FOLDER_PATH = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_FOLDER_PATH, exist_ok=True)

# Full absolute path for the SQLite database file
DB_PATH = os.path.join(INSTANCE_FOLDER_PATH, "site.db")

# Flask secret key (USE A STRONG, RANDOM ONE!)
SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_dev_key_change_me_idiot")

# Google OAuth Credentials
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
# GOOGLE_DISCOVERY_URL is automatically handled by Authlib's server_metadata_url parameter

# Admin credentials
# For security: ADMIN_PASSWORD in your .env MUST be a HASHED password!
# As requested, this remains static for this code. AVOID THIS IN REAL-WORLD APPS!
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin_master")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin_p@ssw0rd") 

# SQLite database (using absolute path for robustness on Windows)
DATABASE_URL = f"sqlite:///{DB_PATH}"

# For upload folder
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Ensure uploads folder also exists

# Sanity check
print("✅ Config loaded. Absolute Database path ->", DB_PATH)
print("✅ Uploads folder path ->", UPLOAD_FOLDER)
print("✅ Using Admin Username:", ADMIN_USERNAME)
print("⚠️ ADMIN_PASSWORD is NOT HASHED as per direct request. EXTREMELY INSECURE FOR PRODUCTION.")