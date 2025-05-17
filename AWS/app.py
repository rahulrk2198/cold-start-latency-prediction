import boto3
import joblib
import numpy as np
import json
import time
import datetime
import os
import psutil
import csv
import logging

# Set up logging configuration - Modified for Lambda compatibility
# logging.basicConfig(level=logging.INFO) # Removed this line
logger = logging.getLogger()
logger.setLevel(logging.INFO) # Set level directly on the root logger

# S3 settings
MODEL_BUCKET = "mlp-invscaling-bucket"
MODEL_FILE_NAME = "mlp_model.pkl"
MODEL_PATH = f"/tmp/{MODEL_FILE_NAME}"

LOG_BUCKET = "cold-start-logs"
LOG_FILE_PATH = "/tmp/log.csv"
S3_LOG_FILE = "log.csv"

model = None

def load_model():
    test_s3_permissions() # Note: This function may still log an error if GetObject fails
    global model
    if model is None:
        logger.info("Downloading Model from S3")
        s3 = boto3.client("s3")
        try:
            s3.download_file(MODEL_BUCKET, MODEL_FILE_NAME, MODEL_PATH)
            logger.info("Model downloaded successfully.")
        except Exception as e:
            logger.error(f"Error downloading model: {e}") # Use logger.error for exceptions
            # Depending on requirements, you might want to raise the exception
            # raise e
            return None # Return None or handle error appropriately if download fails
        model = joblib.load(MODEL_PATH)
    return model

def log_metrics(latency_ms, context):
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        memory = psutil.virtual_memory().used / (1024 * 1024)  # in MB
        cpu = psutil.cpu_percent()
        remaining_time = context.get_remaining_time_in_millis()

        row = [
            now.isoformat(),
            now.weekday(),
            now.hour,
            round(latency_ms, 2),
            round(memory, 2),
            cpu,
            context.aws_request_id,
            context.function_name,
            context.function_version,
            remaining_time
        ]

        # Write new row to temp log file
        file_exists = os.path.isfile(LOG_FILE_PATH)
        with open(LOG_FILE_PATH, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow([
                    'Timestamp', 'DayOfWeek', 'Hour', 'Latency(ms)', 'MemoryUsed(MB)',
                    'CPUUsage(%)', 'RequestID', 'FunctionName', 'FunctionVersion', 'RemainingTime(ms)'
                ])
            writer.writerow(row)

        # Try to append to existing log in S3
        s3 = boto3.client('s3')
        logger.info("Checking for existing log.csv in S3...")
        try:
            s3.download_file(LOG_BUCKET, S3_LOG_FILE, "/tmp/existing_log.csv")
            with open("/tmp/existing_log.csv", "a", newline='') as existing, open(LOG_FILE_PATH, "r") as new:
                next(new)  # Skip header
                existing.writelines(new.readlines())
            final_log_path = "/tmp/final_log.csv"
            os.rename("/tmp/existing_log.csv", final_log_path)
        except s3.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.info("No existing log.csv found in S3. Starting fresh.")
                final_log_path = LOG_FILE_PATH
            else:
                logger.error(f"Error checking for existing log.csv: {e}")
                return

        # Upload final merged log back to S3
        s3.upload_file(final_log_path, LOG_BUCKET, S3_LOG_FILE)
        logger.info("Appended log.csv uploaded successfully to S3.")

    except Exception as e:
        logger.error(f"Error in log_metrics: {e}")

def test_s3_permissions():
    s3 = boto3.client('s3')
    try:
        # Attempt to list the objects - Commented out due to missing s3:ListBucket permission in the provided policy
        # response = s3.list_objects_v2(Bucket=MODEL_BUCKET)
        # logger.info(f"S3 ListBucket check successful for {MODEL_BUCKET}.") # Removed response from log as it's not available

        # Attempt to download the model file to check GetObject permission
        logger.info(f"Attempting test download of {MODEL_FILE_NAME} from {MODEL_BUCKET}...")
        s3.download_file(MODEL_BUCKET, MODEL_FILE_NAME, '/tmp/test_model.pkl')
        logger.info("Test model file downloaded successfully (checking GetObject permission).")
        os.remove('/tmp/test_model.pkl') # Clean up test file
    except Exception as e:
        # Log specific S3 access errors
        logger.error(f"Error testing S3 permissions for bucket {MODEL_BUCKET}: {e}")
        # Depending on requirements, you might want to raise the exception here
        # raise e

def handler(event, context):
    logger.info("Lambda function handler started.")
    try:
        start_time = time.perf_counter()

        # Load the model (includes S3 permission test)
        loaded_model = load_model() # Renamed variable to avoid conflict with global 'model'
        if loaded_model is None:
             logger.error("Failed to load model. Exiting.")
             return {
                "statusCode": 500, # Internal Server Error
                "body": json.dumps({"error": "Model could not be loaded."})
             }
        logger.info("Model loaded successfully.")

        # Process input data
        try:
            input_data = json.loads(event["body"])["features"]
            input_array = np.array(input_data).reshape(1, -1)
            logger.info("Input data parsed successfully.")
        except Exception as e:
             logger.error(f"Error parsing input JSON or features: {e}")
             return {
                "statusCode": 400, # Bad Request
                "body": json.dumps({"error": f"Invalid input format: {e}"})
             }

        # Make prediction
        prediction = loaded_model.predict(input_array)[0]
        logger.info(f"Prediction made successfully: {int(prediction)}")

        # Calculate latency and log metrics
        latency = (time.perf_counter() - start_time) * 1000  # in ms
        logger.info(f"Request processed. Latency: {latency:.2f} ms.")
        log_metrics(latency, context) # Log metrics including S3 upload

        # Return success response
        return {
            "statusCode": 200,
            "body": json.dumps({"prediction": int(prediction)})
        }

    except Exception as e:
        # Catch-all for any other unexpected errors during execution
        logger.error(f"Unhandled exception in handler: {e}", exc_info=True) # Log traceback
        return {
            "statusCode": 500, # Internal Server Error
            "body": json.dumps({"error": f"An unexpected error occurred: {e}"})
        }