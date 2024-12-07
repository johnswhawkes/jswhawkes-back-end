import os
import logging
import azure.functions as func
from azure.cosmos import CosmosClient, exceptions
from datetime import datetime
import json

# Retrieve Cosmos DB settings from environment variables
COSMOS_ENDPOINT = os.getenv('COSMOS_ENDPOINT')
COSMOS_KEY = os.getenv('COSMOS_KEY')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'VisitCounterDB')
CONTAINER_NAME = os.getenv('CONTAINER_NAME', 'VisitorCount')

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        logging.info('Processing request for visitor count.')

        # Initialize Cosmos DB client using connection string
        client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
        container = client.get_database_client(DATABASE_NAME).get_container_client(CONTAINER_NAME)

        # Use today's date as the partition key
        visit_date = datetime.utcnow().strftime('%Y-%m-%d')

        # Get the current daily count and update it
        daily_visitor_count = get_visitor_count(container, visit_date)
        daily_visitor_count += 1

        # Update the daily visitor count
        container.upsert_item({
            "id": visit_date,  # Unique ID for the date
            "visitDate": visit_date,
            "visitorCount": daily_visitor_count
        })

        # Calculate the total visitor count by summing all visitor counts
        total_visitor_count = calculate_total_count(container)

        logging.info(f"Daily count for {visit_date}: {daily_visitor_count}")
        logging.info(f"Total visitor count: {total_visitor_count}")

        # Return both counts in the response
        return func.HttpResponse(
            json.dumps({
                "dailyCount": daily_visitor_count,
                "totalCount": total_visitor_count
            }),
            status_code=200,
            mimetype="application/json"
        )
    
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

def calculate_total_count(container):
    try:
        # Query all items to sum the "visitorCount" field
        total_count = 0
        query = "SELECT c.visitorCount FROM c WHERE c.visitorCount IS NOT NULL"
        
        # Execute the query
        items = container.query_items(query=query, enable_cross_partition_query=True)
        
        # Sum the visitor counts from all items
        for item in items:
            total_count += item.get("visitorCount", 0)

        logging.info(f"Calculated total visitor count: {total_count}")
        return total_count
    
    except Exception as e:
        logging.error(f"Error reading total visitor count: {e}")
        return 0

def get_visitor_count(container, visit_date):
    try:
        # Retrieve the existing visitor count for the current date
        item = container.read_item(item=visit_date, partition_key=visit_date)
        return item.get("visitorCount", 0)
    except exceptions.CosmosResourceNotFoundError:
        logging.warning(f"Could not find existing visitor count for {visit_date}. Initializing count.")
        return 0
    except Exception as e:
        logging.error(f"Error reading visitor count for {visit_date}: {e}")
        return 0
