import os
import logging
import azure.functions as func
from azure.cosmos import CosmosClient, exceptions
from datetime import datetime
import json  # Importing json module to format the response

# Retrieve Cosmos DB settings from environment variables
COSMOS_ENDPOINT = os.getenv('COSMOS_ENDPOINT')
COSMOS_KEY = os.getenv('COSMOS_KEY')  # Add your Cosmos DB primary key in environment variables
DATABASE_NAME = os.getenv('DATABASE_NAME', 'VisitCounterDB')  # Default fallback if env var is missing
CONTAINER_NAME = os.getenv('CONTAINER_NAME', 'VisitorCount')

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        logging.info('Processing request for visitor count.')

        # Initialize Cosmos DB client using connection string
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

        # Return the response in JSON format
        return func.HttpResponse(
            json.dumps({"count": visitor_count}),  # Return a JSON response
            status_code=200,
            mimetype="application/json"  # Explicitly set the MIME type to JSON
        )
    
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        # Return error response in JSON format
        return func.HttpResponse(
            json.dumps({"error": str(e)}),  # Return an error message in JSON format
            status_code=500,
            mimetype="application/json"
        )


def get_visitor_count(container, visit_date):
    # Try to retrieve the existing visitor count for the current date
    try:
        item = container.read_item(item=visit_date, partition_key=visit_date)
        return item.get("visitorCount", 0)  # Return current count or 0 if not found
    except exceptions.CosmosResourceNotFoundError:
        logging.warning(f"Could not find existing visitor count for {visit_date}. Initializing count.")
        return 0  # Initialize count to 0 if the item does not exist
    except Exception as e:
        logging.error(f"Error reading visitor count for {visit_date}: {e}")
        return 0  # Default to 0 in case of other exceptions
