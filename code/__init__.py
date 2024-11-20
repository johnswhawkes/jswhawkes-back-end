import os
import logging
import azure.functions as func
from azure.cosmos import CosmosClient
from datetime import datetime

# Retrieve Cosmos DB settings from environment variables
COSMOS_ENDPOINT = os.getenv('COSMOS_ENDPOINT')
COSMOS_KEY = os.getenv('COSMOS_KEY')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'VisitCounterDB')  # Default fallback if env var is missing
CONTAINER_NAME = os.getenv('CONTAINER_NAME', 'VisitorCount')

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        logging.info('Processing request for visitor count.')

        # Initialize Cosmos DB client
        client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
        container = client.get_database_client(DATABASE_NAME).get_container_client(CONTAINER_NAME)

        # Use today's date as the partition key
        visit_date = datetime.utcnow().strftime('%Y-%m-%d')

        # Get the current count or initialize to 0 if not found
        visitor_count = get_visitor_count(container, visit_date)

        # Increment visitor count
        visitor_count += 1

        # Update the visitor count in Cosmos DB
        container.upsert_item({
            "id": visit_date,  # Use visit_date as the unique ID
            "visitDate": visit_date,
            "visitorCount": visitor_count
        })

        logging.info(f"Visitor count for {visit_date}: {visitor_count}")

        return func.HttpResponse(f"Visitor count updated: {visitor_count}", status_code=200)
    
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)

def get_visitor_count(container, visit_date):
    # Try to retrieve the existing visitor count for the current date
    try:
        item = container.read_item(visit_date, partition_key=visit_date)
        return item.get("visitorCount", 0)  # Return current count or 0 if not found
    except Exception as e:
        logging.warning(f"Could not find existing visitor count for {visit_date}. Initializing count.")
        return 0  # Initialize count to 0 if the item does not exist
