import requests
import psycopg2
import re

# Database connection parameters
db_name = 'RFPs'
db_user = 'postgres'
db_password = '0987'
db_host = 'localhost'
db_port = '5432'
table_documents = 'world_bank'

# Connect to PostgreSQL database
conn = psycopg2.connect(
    dbname=db_name,
    user=db_user,
    password=db_password,
    host=db_host,
    port=db_port
)
cursor = conn.cursor()

# Base URL for the WDS API
base_url = "https://search.worldbank.org/api/v2/wds"

# Parameters for the API request
params = {
    "format": "json",
    "rows": 1000,  # Maximum number of rows per request
    "os": 0,       # Offset, starting at 0
    "fl": "id,docdt,docty,display_title,pdfurl,listing_relative_url",  # Fields to retrieve
    "strdate": "2024-01-01"  # Start date for filtering
}

# Total number of records to retrieve
total_records = 10055  # Adjust as needed based on actual total records

# Function to extract the code from display_title
def extract_code(display_title):
    match = re.search(r"P\d+", display_title)
    return match.group(0) if match else None

# Function to insert data into PostgreSQL
def insert_data(doc):
    try:
        # Ensure 'id' and 'display_title' are not None
        if not doc.get('id') or not doc.get('display_title'):
            print(f"Skipping document due to missing 'id' or 'display_title': {doc}")
            return

        # Extract the code from display_title
        code = extract_code(doc.get('display_title', ''))

        # Insert data into the Documents table
        cursor.execute(
            f"""
            INSERT INTO {table_documents} (id, docty, docdt, display_title, pdfurl, listing_relative_url, code)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
            """,
            (
                doc.get('id'),
                doc.get('docty'),
                doc.get('docdt'),
                doc.get('display_title'),
                doc.get('pdfurl'),
                doc.get('listing_relative_url'),
                code  # Insert the extracted code
            )
        )

        # Commit the transaction
        conn.commit()
        print(f"Data for document {doc.get('id')} inserted successfully.")

    except Exception as e:
        print(f"Error inserting data: {e}")
        conn.rollback()

# Fetch and insert documents with pagination
while params["os"] < total_records:
    # Make the API request
    response = requests.get(base_url, params=params)

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        
        # Get the total number of records from the first response
        if params["os"] == 0:
            total_records = int(data.get("total", 0))
            print(f"Total records to fetch: {total_records}")

        documents = data.get('documents', {})

        # Insert each document into the database
        for doc_id, doc_info in documents.items():
            if doc_info.get('id'):
                insert_data(doc_info)
            else:
                print(f"Document missing 'id': {doc_info}")

        # Update the offset for the next request
        params["os"] += params["rows"]
        print(f"Fetching records starting at offset: {params['os']}")
    else:
        print(f"Request failed with status code {response.status_code}")
        break

# Close the database connection
cursor.close()
conn.close()

print(f"All documents have been retrieved and inserted into the '{table_documents}' table.")
