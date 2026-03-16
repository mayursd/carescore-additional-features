# Lambda function for secure Daily.co room creation
# Place this in infrastructure/lambda_create_room.py and deploy to AWS Lambda
# Set DAILY_API_KEY as an environment variable in your Lambda configuration

import os
import json
import requests

def get_cors_headers(origin):
    """Return CORS headers based on origin"""
    allowed_origins = [
        # Add your S3 website URL here
        "https://your-carescore-recorder-bucket.s3-website-us-east-1.amazonaws.com",
        "https://your-carescore-recorder-bucket.s3.amazonaws.com",
        # For development
        "http://localhost:3000",
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ]
    
    if origin in allowed_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-API-Key"
        }
    
    # Fallback - you can remove this for stricter security
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS", 
        "Access-Control-Allow-Headers": "Content-Type"
    }

def lambda_handler(event, context):
    # Get the origin from the request
    origin = event.get('headers', {}).get('origin', '')
    cors_headers = get_cors_headers(origin)
    
    method = event.get("requestContext", {}).get("http", {}).get("method", "POST")
    if method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": ""
        }
    if method == "GET":
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": "Lambda is up!"
        }

    DAILY_API_KEY = os.environ["DAILY_API_KEY"]
    try:
        body = json.loads(event["body"])
    except Exception:
        return {
            "statusCode": 400,
            "headers": cors_headers,
            "body": json.dumps({"error": "Invalid request body"})
        }

    resp = requests.post(
        "https://api.daily.co/v1/rooms",
        headers={
            "Authorization": f"Bearer {DAILY_API_KEY}",
            "Content-Type": "application/json"
        },
        json=body
    )
    return {
        "statusCode": resp.status_code,
        "headers": cors_headers,
        "body": resp.text
    }