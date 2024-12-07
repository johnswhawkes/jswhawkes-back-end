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

        # Get the current daily count
        daily_visitor_count = get_visitor_count(container, visit_date)

        # Increment the daily count
        daily_visitor_count += 1

        # Update the daily visitor count
        container.upsert_item({
            "id": visit_date,  # Unique ID for the date
            "visitDate": visit_date,
            "visitorCount": daily_visitor_count
        })

        logging.info(f"Daily count for {visit_date}: {daily_visitor_count}")

        # Get the total visitor count after updating the daily count
        total_visitor_count = get_total_count(container)

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


def get_total_count(container):
    try:
        # Retrieve the total visitor count by aggregating all items with the correct query format
        query = "SELECT VALUE SUM(c.visitorCount) FROM c"
        
        # Perform the query with cross-partition enabled (safe here, even for a single partition)
        result = list(container.query_items(query=query, enable_cross_partition_query=True))

        # Check if any results exist
        if result:
            return result[0]  # Since it's a single aggregate value, we return the first element
        else:
            return 0
    except Exception as e:
        logging.error(f"Error reading total visitor count: {e}")
        return 0

def get_visitor_count(container, visit_date):
    try:
        # Retrieve the existing visitor count for the current date
        item = container.read_item(item=visit_date, partition_key=visit_date)
        return item.get("visitorCount", 0)  # Return current count or 0 if not found
    except exceptions.CosmosResourceNotFoundError:
        logging.warning(f"Could not find existing visitor count for {visit_date}. Initializing count.")
        return 0
    except Exception as e:
        logging.error(f"Error reading visitor count for {visit_date}: {e}")
        return 0
