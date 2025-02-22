import os
import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def init_db(app):
    # Configure the database using environment variables
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Please ensure the database is properly configured."
        )

    # Handle Heroku-style PostgreSQL URLs
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # Log database connection attempt
    logger.info(f"Attempting to connect to database at {db_url.split('@')[-1]}")

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    try:
        # Initialize the app with the extension
        db.init_app(app)

        # Test the database connection
        with app.app_context():
            db.engine.connect()
            logger.info("Successfully connected to the database")

    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        logger.error("Please check your database configuration and ensure PostgreSQL is running")
        raise