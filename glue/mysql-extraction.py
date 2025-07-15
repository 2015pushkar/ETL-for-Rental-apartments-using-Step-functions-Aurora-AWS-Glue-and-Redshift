import boto3, sys, csv, pymysql, io, json, logging
from datetime import date
from botocore.exceptions import ClientError
from awsglue.utils import getResolvedOptions

# Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger()

args = getResolvedOptions(sys.argv, ["table_name", "load_type", "log_level"])
table_name = args["table_name"]
load_type = args["load_type"]
log_level  = args["log_level"].upper()

# ──────────────── SETUP LOGGING ────────────────
numeric_level = getattr(logging, log_level, logging.INFO)
logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)
logger.info("Job init | table=%s | load_type=%s | log_level=%s",
            table_name, load_type, log_level)

def get_rds_credentials(secret_name, region_name):
    logger.debug("Fetching RDS creds | secret=%s, region=%s",
                 secret_name, region_name)
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        logger.debug("RDS creds fetched successfully.")
    except ClientError as e:
        logger.error(f"Unable to retrieve secret: {e}")
        return None

    if 'SecretString' not in get_secret_value_response:
        logger.error("Secret does not contain a string.")
        return None

    secret = get_secret_value_response['SecretString']
    credentials = json.loads(secret)
    logger
    return credentials

credentials = get_rds_credentials("rental-db", "us-east-1")

# DB Credentials
user_name = credentials['username']
host = credentials['host']
password = credentials['password']
db_name = "rental_apartments"

# S3 bucket Path - all the tables will be stored in the same bucket
s3_bucket = "nl-aws-de-labs-rgn"
s3_key = f'raw_landing_zone/apartment_db/{table_name}/data.csv'

# DynamoDB never stores the tables; It only keeps a bookmark of the last extracted value
# """
#     {
#     "table_name": "your_table_name",
#     "load_column": "your_load_column" -> last_modified_timestamp
#     "last_extracted_value": "your_last_extracted_value" -> '2023-10-01 12:00:00'
#     }
# """

dynamodb = boto3.resource('dynamodb')
config_table = dynamodb.Table('incremental_load_configurations')

def fetch_configurations(table_name):
    logger.debug("Reading incremental config | table=%s", table_name)
    try:
        response = config_table.get_item(Key={'table_name': table_name})
        logger.debug("DynamoDB response: %s", response)
        if 'Item' in response:
            logger.info("Fetched configurations for table: %s", table_name)
            logger.debug("Load column: %s, Last extracted value: %s",
                         response['Item']['load_column'], response['Item'].get('last_extracted_value'))
            return response['Item']['load_column'], response['Item'].get('last_extracted_value')
        else:
            return None, None
    except Exception as e:
        logger.error(f"Failed to fetch configurations: {str(e)}")
        return None, None

incr_column, last_extracted_value = None, None

if load_type == 'incremental':
    incr_column, last_extracted_value = fetch_configurations(table_name)
    if not incr_column:
        logger.error("Incremental column not found, exiting...")
        sys.exit(1)

def update_last_extracted_value(table_name, last_value):
    logger.debug("Updating last extracted value | table=%s, value=%s",
                 table_name, last_value)
    try:
        response = config_table.update_item(
            Key={'table_name': table_name},
            UpdateExpression="SET last_extracted_value = :val",
            ExpressionAttributeValues={
                ':val': last_value
            },
            ReturnValues="UPDATED_NEW"
        )
        logger.info(f"Updated last extracted value to {last_value}")
    except Exception as e:
        logger.error(f"Failed to update last extracted value: {str(e)}")

def main():
    try:
        connection = pymysql.connect(
            host=host,
            user=user_name,
            password=password,
            database=db_name,
            cursorclass=pymysql.cursors.DictCursor
        )

        with connection.cursor() as cursor:
            sql = f"SELECT * FROM {table_name}"
            if load_type == 'incremental' and incr_column and last_extracted_value:
                sql += f" WHERE {incr_column} > '{last_extracted_value}' ORDER BY {incr_column} DESC"
            cursor.execute(sql)
            result = cursor.fetchall()

        csv_data = convert_to_csv(result)

        s3 = boto3.client('s3')
        s3.put_object(Body=csv_data, Bucket=s3_bucket, Key=s3_key)
        logger.info('Data extracted and written to S3 successfully')

        if result and load_type == 'incremental':
            new_last_value = result[0][incr_column]
            update_last_extracted_value(table_name, str(new_last_value))

    except Exception as e:
        logger.error(f'Error: {str(e)}')
        sys.exit(1)

    finally:
        connection.close()

def convert_to_csv(data):
    logger.debug("Converting data to CSV format")
    if not data:
        return ""
    csv_file = io.StringIO()
    fieldnames = data[0].keys()
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    for row in data:
        writer.writerow(row)
    return csv_file.getvalue()

if __name__ == '__main__':
    main()