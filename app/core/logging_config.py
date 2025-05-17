import logging
import sys

# Define the log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"

# Create a formatter
formatter = logging.Formatter(LOG_FORMAT)

# Create a handler for console output
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# Configure the root logger
def setup_logging(log_level=logging.INFO):
    """Set up basic logging configuration."""
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplicate logs if this function is called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    # Add the console handler to the root logger
    logger.addHandler(console_handler)

    # You can also add file handlers here if needed, for example:
    # file_handler = logging.FileHandler("app.log")
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)

    logging.info("Logging configured.")

# Example of how to get a logger for a specific module
# logger = logging.getLogger(__name__)
# logger.info("This is an info message from logging_config.py")

