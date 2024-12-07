def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        logging.info('Processing request for visitor count.')

        # Initialize Cosmos DB client using connection string
        client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
        container = client.get_database_client(DATABASE_NAME).get_container_client(CONTAINER_NAME)

        # Use today's date as the partition key
        visit_date = datetime.utcnow().strftime('%Y-%m-%d')

        # Get the current counts (daily and total)
        daily_visitor_count = get_visitor_count(container, visit_date)
        total_visitor_count = get_total_count(container)

        # Increment both counters
        daily_visitor_count += 1
        total_visitor_count += 1

        # Update the daily visitor count
        container.upsert_item({
            "id": visit_date,  # Unique ID for the date
            "visitDate": visit_date,
            "visitorCount": daily_visitor_count
        })

        # Update the total visitor count (stored under a static ID)
        container.upsert_item({
            "id": "totalCount",  # Static ID for total count
            "visitDate": "all-time",
            "totalVisitorCount": total_visitor_count
        })

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

def get_total_count(container):
    try:
        # Retrieve the total visitor count
        item = container.read_item(item="totalCount", partition_key="totalCount")
        return item.get("totalVisitorCount", 0)
    except exceptions.CosmosResourceNotFoundError:
        logging.warning("Total visitor count not found. Initializing to 0.")
        return 0
    except Exception as e:
        logging.error(f"Error reading total visitor count: {e}")
        return 0
