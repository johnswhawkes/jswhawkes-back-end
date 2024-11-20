import os
import logging
import azure.functions as func
from azure.cosmos import CosmosClient, exceptions
from datetime import datetime
import uuid

# Retrieve Cosmos DB settings from environment variables
COSMOS_ENDPOINT = os.getenv('COSMOS_ENDPOINT')
COSMOS_KEY = os.getenv('COSMOS_KEY')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'VisitCounterDB')  # Default fallback if env var is missing
CONTAINER_NAME = os.getenv('CONTAINER_NAME', 'VisitorCount')

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing request for visitor tracking.')

    try:
        # Extract headers
        user_agent = req.headers.get('User-Agent', 'Unknown')
        ip_address = req.headers.get('X-Forwarded-For', req.headers.get('REMOTE_ADDR', 'Unknown'))

        # Log visitor info
        logging.info(f"Visitor info - User Agent: {user_agent}, IP Address: {ip_address}")

        # Parse visitor info (You may want to use a library for user-agent parsing)
        visitor_info = {
            "ipAddress": ip_address,
            "os": parse_os(user_agent),
            "browser": parse_browser(user_agent),
            "device": parse_device(user_agent)
        }
        
        # Current date as partition key
        visit_date = datetime.utcnow().strftime('%Y-%m-%d')

        # Initialize Cosmos DB client
        logging.info("Initializing Cosmos DB client.")
        client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
        database = client.get_database_client(DATABASE_NAME)
        container = database.get_container_client(CONTAINER_NAME)

        # Log the connection details
        logging.info(f"Connected to Cosmos DB - Database: {DATABASE_NAME}, Container: {CONTAINER_NAME}")

        # Store visitor data in Cosmos DB
        item = {
            "id": str(uuid.uuid4()),  # Unique ID for the visit
            "visitDate": visit_date,
            "pageID": "home",  # This can be dynamic based on the page being visited
            "visitTime": datetime.utcnow().isoformat(),
            "visitorInfo": visitor_info
        }

        logging.info(f"Upserting item: {item}")
        container.upsert_item(item)
        logging.info("Visitor data stored successfully.")

        return func.HttpResponse("Visitor data stored.", status_code=200)

    except exceptions.CosmosResourceNotFoundError as e:
        logging.error(f"Cosmos DB error: {str(e)}")
        return func.HttpResponse(f"Cosmos DB error: {str(e)}", status_code=500)
    
    except exceptions.CosmosHttpResponseError as e:
        logging.error(f"Cosmos HTTP response error: {str(e)}")
        return func.HttpResponse(f"Error with Cosmos DB HTTP response: {str(e)}", status_code=500)
    
    except Exception as e:
        logging.error(f"General error: {str(e)}")
        return func.HttpResponse(f"Internal server error: {str(e)}", status_code=500)


def parse_os(user_agent):
    try:
        if "Windows" in user_agent:
            return "Windows"
        elif "Mac" in user_agent:
            return "Mac"
        elif "Linux" in user_agent:
            return "Linux"
        else:
            return "Unknown"
    except Exception as e:
        logging.error(f"Error parsing OS: {str(e)}")
        return "Unknown"

def parse_browser(user_agent):
    try:
        if "Chrome" in user_agent:
            return "Chrome"
        elif "Firefox" in user_agent:
            return "Firefox"
        elif "Safari" in user_agent:
            return "Safari"
        else:
            return "Unknown"
    except Exception as e:
        logging.error(f"Error parsing Browser: {str(e)}")
        return "Unknown"

def parse_device(user_agent):
    try:
        if "Mobile" in user_agent:
            return "Mobile"
        elif "Tablet" in user_agent:
            return "Tablet"
        else:
            return "Desktop"
    except Exception as e:
        logging.error(f"Error parsing Device: {str(e)}")
        return "Unknown"
