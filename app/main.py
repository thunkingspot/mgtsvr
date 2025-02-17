import json
import boto3
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import subprocess
import logging

# Configure logging to output to console
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
# Set boto3 and botocore logging level to WARNING to prevent logging sensitive information
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)

app = FastAPI()

def get_secret():
    secret_name = "MGTSVR_WEBHOOK_SECRET"
    region_name = "us-west-2"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except Exception as e:
        logger.error(f"Error retrieving secret: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving secret")

    secret_string = get_secret_value_response['SecretString']
    if not secret_string:
        raise ValueError("SecretString is empty or missing in the secret response")
    
    # Parse the JSON string to a dictionary
    secret_dict = json.loads(secret_string)
    
    # Return the value of 'WEBHOOK_SECRET'
    webhook_secret = secret_dict.get("WEBHOOK_SECRET")
    if not webhook_secret:
        raise ValueError("WEBHOOK_SECRET not found in the secret payload")
    
    return webhook_secret

WEBHOOK_SECRET = get_secret()

def verify_signature(raw_body: bytes, signature: str) -> bool:
    if not signature:
        return False
    try:
        sha_name, signature_value = signature.split("=")
    except ValueError:
        return False

    if sha_name != "sha256":
        return False

    mac = hmac.new(WEBHOOK_SECRET.encode("utf-8"), raw_body, digestmod=hashlib.sha256)
    # logger.debug(f"Computed signature: {mac.hexdigest()}")
    return hmac.compare_digest(mac.hexdigest(), signature_value)

# nginx will strip the prefix /mgtapi from the URL before forwarding the request to the FastAPI app
@app.post("/mgtapi")
async def webhook(request: Request):
    # Retrieve the signature header from GitHub
    signature = request.headers.get("X-Hub-Signature-256")
    raw_body = await request.body()
    # logger.debug(f"Raw body (hex): {raw_body.hex()}")
    # logger.debug(f"Signature: {signature}")

    if not verify_signature(raw_body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Trigger the deployment script asynchronously
    try:
        subprocess.run(
            [
            '/bin/bash',
            '/home/ubuntu/src/mgtsvr/mgt/deployrepo.sh',
            'true',
            'git@github.com:thunkingspot/aqua.git',
            '/mgt/deploy.sh'
            ],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running deployment script: {e}")
        raise HTTPException(status_code=500, detail="Error running deployment script")

    return {"message": "Deployment triggered"}
