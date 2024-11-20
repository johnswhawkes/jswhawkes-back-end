import os
import logging
import azure.functions as func
from azure.cosmos import CosmosClient, exceptions
from datetime import datetime
import uuid

# Retrieve Cosmos DB settings from environment variables
COSMOS_ENDPOINT = os.getenv('COSMOS_ENDPOINT')
COSMOS_KEY = os.getenv('COSMOS_KEY')
DATABASE_NAME = "VisitCounterDB"
CONTAINER_NAME = "VisitCount"

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing request for visit count.')

    # Current date as partition key (this is how we'll group visits)
    visit_date = datetime.utcnow().strftime('%Y-%m-%d')

    try:
        # Initialize Cosmos DB client
        client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
        container = client.get_database_client(DATABASE_NAME).get_container_client(CONTAINER_NAME)

        # Try to get the document for the current date
        existing_item = None
        for item in container.query_items(
            query=f"SELECT * FROM c WHERE c.visitDate = '{visit_date}'",
            enable_cross_partition_query=True
        ):
            existing_item = item
            break

        if existing_item:
            # Document found, increment the visit count
            existing_item['visitCount'] += 1
            container.upsert_item(existing_item)
        else:
            # Document not found, create a new document for today with count 1
            container.upsert_item({
                "id": str(uuid.uuid4()),  # Unique ID for the document
                "visitDate": visit_date,
                "visitCount": 1  # First visit of the day
            })

        return func.HttpResponse(f"Visitor count updated for {visit_date}.", status_code=200)

    except exceptions.CosmosHttpResponseError as e:
        logging.error(f"Error with Cosmos DB: {e.message}")
        return func.HttpResponse(f"Error with Cosmos DB: {e.message}", status_code=500)
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return func.HttpResponse(f"Unexpected error: {str(e)}", status_code=500)
