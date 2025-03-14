import sqlite3
import os
from datetime import datetime
import logging
from app import logger


class BotDatabase:
    def __init__(self, db_path="bot_stats.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Create database tables if they don't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Users table
                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    first_seen TIMESTAMP,
                    last_active TIMESTAMP
                )
                """
                )

                # Place searches table
                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    place_name TEXT,
                    place_type TEXT,
                    latitude REAL,
                    longitude REAL,
                    city TEXT,  -- Added city field
                    search_time TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                """
                )

                # Authorized admins table
                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS authorized_admins (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    granted_at TIMESTAMP
                )
                """
                )

                # Check if city column exists in searches table
                cursor.execute("PRAGMA table_info(searches)")
                columns = cursor.fetchall()
                column_names = [column[1] for column in columns]

                # Add city column if it doesn't exist
                if "city" not in column_names:
                    cursor.execute("ALTER TABLE searches ADD COLUMN city TEXT")
                    logger.info("Added 'city' column to searches table")

                conn.commit()
                logger.info("Database initialized successfully")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")

    def add_or_update_user(
        self, user_id, username=None, first_name=None, last_name=None
    ):
        """Add a new user or update an existing user's information"""
        now = datetime.now().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Check if user exists
                cursor.execute(
                    "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
                )
                if cursor.fetchone():
                    # Update last active
                    cursor.execute(
                        "UPDATE users SET last_active = ?, username = ?, first_name = ?, last_name = ? WHERE user_id = ?",
                        (now, username, first_name, last_name, user_id),
                    )
                    logger.debug(f"Updated user: {user_id}")
                else:
                    # Add new user
                    cursor.execute(
                        "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                        (user_id, username, first_name, last_name, now, now),
                    )
                    logger.info(f"Added new user: {user_id}")
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error adding/updating user {user_id}: {e}")
            return False

    def log_search(
        self, user_id, place_name, place_type, latitude, longitude, city=None
    ):
        """Log a place search by a user"""
        now = datetime.now().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO searches (user_id, place_name, place_type, latitude, longitude, city, search_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, place_name, place_type, latitude, longitude, city, now),
                )
                conn.commit()
                logger.debug(
                    f"Logged search for {place_name} in {city} by user {user_id}"
                )
                return True
        except sqlite3.Error as e:
            logger.error(f"Error logging search: {e}")
            return False

    def get_user_count(self):
        """Get the total number of users"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Error getting user count: {e}")
            return 0

    def get_search_count(self):
        """Get the total number of searches"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM searches")
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Error getting search count: {e}")
            return 0

    def get_active_users_today(self):
        """Get the count of users active today"""
        today = datetime.now().date().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(DISTINCT user_id) FROM users WHERE last_active LIKE ?",
                    (f"{today}%",),
                )
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Error getting active users: {e}")
            return 0

    def get_popular_places(self, limit=10):
        """Get the most popular places based on search count"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT place_name, place_type, COUNT(*) as search_count 
                    FROM searches 
                    GROUP BY place_name 
                    ORDER BY search_count DESC
                    LIMIT ?
                """,
                    (limit,),
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting popular places: {e}")
            return []

    def get_cities(self, limit=20):
        """Get cities where searches have been performed, with counts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT city, COUNT(*) as search_count 
                    FROM searches 
                    WHERE city IS NOT NULL AND city != ''
                    GROUP BY city 
                    ORDER BY search_count DESC
                    LIMIT ?
                """,
                    (limit,),
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting cities: {e}")
            return []

    def add_authorized_admin(self, user_id, username=None):
        """Add a user to the authorized admins list"""
        now = datetime.now().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO authorized_admins VALUES (?, ?, ?)",
                    (user_id, username, now),
                )
                conn.commit()
                logger.info(f"Added authorized admin: {user_id}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error adding authorized admin: {e}")
            return False

    def is_authorized_admin(self, user_id):
        """Check if a user is an authorized admin"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id FROM authorized_admins WHERE user_id = ?",
                    (user_id,),
                )
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Error checking admin authorization: {e}")
            return False

    def get_searches_by_date(self, days=7):
        """Get search counts grouped by date for the last X days"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT date(search_time) as date, COUNT(*) as count
                    FROM searches
                    WHERE search_time >= date('now', ?)
                    GROUP BY date(search_time)
                    ORDER BY date
                """,
                    (f"-{days} days",),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting searches by date: {e}")
            return []

    def get_recent_users(self, limit=10):
        """Get the most recent active users"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT user_id, username, first_name, last_name, 
                           datetime(last_active) as last_active
                    FROM users
                    ORDER BY last_active DESC
                    LIMIT ?
                """,
                    (limit,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting recent users: {e}")
            return []

    def get_place_types(self):
        """Get distribution of place types"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT place_type, COUNT(*) as count
                    FROM searches
                    GROUP BY place_type
                    ORDER BY count DESC
                """
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting place types: {e}")
            return []

    def backup_database(self, backup_path=None):
        """Create a backup of the database"""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.backup_{timestamp}"

        try:
            with sqlite3.connect(self.db_path) as src, sqlite3.connect(
                backup_path
            ) as dst:
                src.backup(dst)
            logger.info(f"Database backup created at {backup_path}")
            return backup_path
        except sqlite3.Error as e:
            logger.error(f"Database backup error: {e}")
            return None
