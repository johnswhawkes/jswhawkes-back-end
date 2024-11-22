import os
import logging
import requests
from datetime import datetime
import hashlib
import base64
import hmac
from azure.functions import HttpRequest, HttpResponse

# Retrieve Cosmos DB settings from environment variables
COSMOS_ENDPOINT = os.getenv('COSMOS_ENDPOINT')
COSMOS_KEY = os.getenv('COSMOS_KEY')  # Your Cosmos DB key
DATABASE_NAME = os.getenv('DATABASE_NAME', 'VisitCounterDB')  # Default fallback if env var is missing
CONTAINER_NAME = os.getenv('CONTAINER_NAME', 'VisitorCount')

# Generate authorization header
def get_cosmos_auth_headers(verb, resource_type, resource_link, body):
    date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    body_string = body if body else ''
    canonicalized_resource = f"/dbs/{DATABASE_NAME}/colls/{CONTAINER_NAME}/docs/{resource_link}"
    
    string_to_sign = f"{verb}\n{body_string}\n{date}\n{canonicalized_resource}"
    
    # HMAC SHA256 signature
    signature = base64.b64encode(hmac.new(base64.b64decode(COSMOS_KEY), string_to_sign.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
    
    headers = {
        'Authorization': f'cosmosdbaccount={signature}',
        'x-ms-date': date,
        'x-ms-version': '2018-12-31',
        'Content-Type': 'application/json',
    }
    
    return headers

# Function to get visitor count
def get_visitor_count(visit_date):
    url = f"{COSMOS_ENDPOINT}/dbs/{DATABASE_NAME}/colls/{CONTAINER_NAME}/docs/{visit_date}"
    headers = get_cosmos_auth_headers('GET', 'docs', visit_date, '')
    
    # Make the GET request to retrieve the current visitor count
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        item = response.json()
        return item.get("visitorCount", 0)
    else:
        logging.warning(f"Could not find existing visitor count for {visit_date}. Initializing count.")
        return 0  # Initialize count to 0 if not found

# Main function to handle the HTTP request
def main(req: HttpRequest) -> HttpResponse:
    try:
        logging.info('Processing request for visitor count.')

        # Use today's date as the partition key
        visit_date = datetime.utcnow().strftime('%Y-%m-%d')

        # Get the current count or initialize to 0 if not found
        visitor_count = get_visitor_count(visit_date)

        # Increment visitor count
        visitor_count += 1

        # Update the visitor count in Cosmos DB
        item = {
            "id": visit_date,  # Use visit_date as the unique ID
            "visitDate": visit_date,
            "visitorCount": visitor_count
        }

        url = f"{COSMOS_ENDPOINT}/dbs/{DATABASE_NAME}/colls/{CONTAINER_NAME}/docs/{visit_date}"
        headers = get_cosmos_auth_headers('POST', 'docs', visit_date, json.dumps(item))
        
        # Make the POST request to update the visitor count
        response = requests.post(url, headers=headers, json=item)
        
        if response.status_code == 201:
            logging.info(f"Visitor count for {visit_date}: {visitor_count}")
            return HttpResponse(f"Visitor count updated: {visitor_count}", status_code=200)
        else:
            raise Exception(f"Failed to update document: {response.status_code} - {response.text}")

    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return HttpResponse(f"Error: {str(e)}", status_code=500)
