import sqlite3
import requests
import time
import logging
import json

# Logging configuration (crucial to see what happens in the dark of night)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_NAME = "earthquakes.db"
USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
POLL_INTERVAL_SECONDS = 60

def init_db():
    """Initializes the database and creates the table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # We use the USGS ID as Primary Key to guarantee idempotency
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS earthquakes (
            id TEXT PRIMARY KEY,
            magnitude REAL,
            place TEXT,
            time INTEGER,
            url TEXT,
            longitude REAL,
            latitude REAL,
            depth REAL
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

def poll_data():
    """Executes a polling cycle: fetches data, parses it, and stores it."""
    logger.info("Starting polling cycle...")
    
    try:
        # Timeout is VITAL. If the network hangs, we can't wait forever.
        # 10 seconds for connection wait, 15 for read timeout.
        response = requests.get(USGS_URL, timeout=(10, 15))
        
        # If the API returns a 500, 503, 404, etc., we raise a controlled error
        response.raise_for_status()
        
        # Attempt to parse JSON. If the API returned garbage HTML or truncated text, this fails.
        data = response.json()
        
    except requests.exceptions.Timeout:
        logger.error("Network error: Request timed out.")
        return # Exit current cycle, the main loop will handle the retry
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error: Server responded with a non-200 status code. {e}")
        return
    except requests.exceptions.RequestException as e:
        logger.error(f"Unexpected network error (DNS down, no connection, etc.): {e}")
        return
    except json.JSONDecodeError:
        logger.error("Data error: Response is not valid JSON or is corrupted.")
        return

    # If we reach here, we have a valid JSON. Process the data.
    features = data.get("features", [])
    if not features:
        logger.warning("JSON parsed successfully, but contains no features.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    inserted_count = 0
    for feature in features:
        try:
            quake_id = feature.get("id")
            if not quake_id:
                continue # If for some reason a record has no ID, skip it for safety

            props = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [None, None, None])

            # INSERT OR IGNORE: If the ID already exists in the table, SQLite silently ignores it.
            # This avoids duplicates without having to do a prior SELECT.
            cursor.execute('''
                INSERT OR IGNORE INTO earthquakes 
                (id, magnitude, place, time, url, longitude, latitude, depth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                quake_id,
                props.get("mag"),
                props.get("place"),
                props.get("time"),
                props.get("url"),
                coords[0] if len(coords) > 0 else None,
                coords[1] if len(coords) > 1 else None,
                coords[2] if len(coords) > 2 else None
            ))
            
            if cursor.rowcount == 1:
                inserted_count += 1
                
        except sqlite3.Error as e:
            # If an insertion fails due to schema, we don't want to lose the whole batch
            logger.error(f"Error inserting earthquake ID {quake_id}: {e}")
            continue

    conn.commit()
    conn.close()
    logger.info(f"Cycle completed. {inserted_count} new earthquakes saved. Total processed: {len(features)}")

if __name__ == "__main__":
    init_db()
    logger.info("Starting Resilient Data Poller service...")
    
    # The infinite loop. The heart of resilience.
    while True:
        try:
            poll_data()
        except Exception as e:
            # Final safety net: if there is an unforeseen error in poll_data(), 
            # the loop must not die.
            logger.critical(f"Unhandled error in main loop: {e}", exc_info=True)
        
        # Wait before the next cycle
        logger.info(f"Waiting {POLL_INTERVAL_SECONDS} seconds for the next cycle...")
        time.sleep(POLL_INTERVAL_SECONDS)