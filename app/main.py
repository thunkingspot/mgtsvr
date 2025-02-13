import boto3
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import subprocess
import logging

# Configure logging to output to console
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

    secret = get_secret_value_response['SecretString']
    return secret

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

    mac = hmac.new(WEBHOOK_SECRET.encode(), raw_body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature_value)

# nginx will strip the prefix /mgtapi from the URL before forwarding the request to the FastAPI app
@app.post("/")
async def webhook(request: Request):
    # Retrieve the signature header from GitHub
    signature = request.headers.get("X-Hub-Signature-256")
    raw_body = await request.body()

    if not verify_signature(raw_body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Trigger the deployment script asynchronously
    #subprocess.Popen(['/bin/bash', '/home/ubuntu/deploy.sh'])

    return {"message": "Deployment triggered"}
