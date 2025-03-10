# Copyright 2025 THUNKINGSPOT LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import time
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

# Singleton class to manage secret retrieval
class SecretManager:
    _instance = None
    _secret = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SecretManager, cls).__new__(cls)
        return cls._instance

    def get_secret(self):
        if self._secret is None:
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
            
            self._secret = webhook_secret
        return self._secret

secret_manager = SecretManager()

# Verify the signature of the request
def verify_signature(raw_body: bytes, signature: str) -> bool:
    if not signature:
        return False
    try:
        sha_name, signature_value = signature.split("=")
    except ValueError:
        return False

    if sha_name != "sha256":
        return False

    mac = hmac.new(secret_manager.get_secret().encode("utf-8"), raw_body, digestmod=hashlib.sha256)
    #logger.debug(f"Computed signature: {mac.hexdigest()}")
    #logger.debug(f"Payload signature: {signature_value}")
    return hmac.compare_digest(mac.hexdigest(), signature_value)

"""
Handle the pipeline trigger request
The request must contain a JSON payload with the following fields:
- debug_mode: true or false (default is false) - causes app to listen for debugger attach
- repo_url: github repository URL of the target app
- repo_mgt_dir: name of directory in the repo containing the phase scripts
- phase: [build, deploy-inactive, swap]
- phase_script: name of the script in the target app to run for the specified phase
- container_name: target container name for the app
- timestamp: compatible with string produced by: date -u +"%Y-%m-%dT%H:%M:%SZ"
"""
@app.post("/mgtapi")
async def webhook(request: Request):
    # Retrieve the signature header from GitHub
    signature = request.headers.get("X-Hub-Signature-256")
    raw_body = await request.body()
    #logger.debug(f"Raw body (hex): {raw_body.hex()}")
    #logger.debug(f"Signature: {signature}")

    # Store the last 100 signatures in a persistent memory structure
    if not hasattr(app.state, "seen_signatures"):
        app.state.seen_signatures = []

    # Reject a signature that we have already seen
    if signature in app.state.seen_signatures:
        raise HTTPException(status_code=403, detail="Signature has already been used")

    # Add the new signature to the list and maintain only the last 100 signatures
    app.state.seen_signatures.append(signature)
    if len(app.state.seen_signatures) > 100:
        app.state.seen_signatures.pop(0)

    if not verify_signature(raw_body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # TODO - implement handling for build, deploy, swap phases with different valid payloads
    debug_mode = payload.get("debug_mode")
    repo_url = payload.get("repo_url")
    repo_mgt_dir = payload.get("repo_mgt_dir")
    phase = payload.get("phase")
    phase_script = payload.get("phase_script")
    container_name = payload.get("container_name")
    timestamp = payload.get("timestamp")

    # If timestamp is not within 45 seconds of current time, reject the request. Also
    # this makes the signature of every request unique, to prevent replay attacks.
    # timestamp is produced by the shell command: date -u +"%Y-%m-%dT%H:%M:%SZ" 
    current_time = time.time()
    try:
        payload_time = time.mktime(time.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp format")

    if abs(current_time - payload_time) > 45:
        raise HTTPException(status_code=403, detail="Invalid timestamp")

    # Trigger the deployment script asynchronously
    try:
        subprocess.run(
            [
            '/bin/bash',
            '/home/ubuntu/src/mgtsvr/mgt/deployrepo.sh',
            container_name,
            repo_url,
            repo_mgt_dir,
            phase,
            phase_script,
            debug_mode
            ],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running deployment script: {e}")
        raise HTTPException(status_code=500, detail="Error running deployment script")

    return {"message": "Deployment triggered"}
