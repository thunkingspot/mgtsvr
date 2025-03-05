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
import hmac
import hashlib
import time
import subprocess
from unittest.mock import Mock, patch
from contextlib import contextmanager
from fastapi.testclient import TestClient
from app.main import app, secret_manager

# prevent boto3 from making actual API calls
@contextmanager
def mock_boto3_client(mock_client):
    import boto3
    original_session_client = boto3.session.Session.client
    boto3.session.Session.client = lambda *args, **kwargs: mock_client
    try:
        yield
    finally:
        boto3.session.Session.client = original_session_client

# Reset app state before each test
def reset_app_state():
    if hasattr(app.state, "seen_signatures"):
        app.state.seen_signatures = []

# Test secret manager singleton with mock boto3 client
def test_secret_manager():
    reset_app_state()
    mock_client = Mock()
    mock_client.get_secret_value.return_value = {
        'SecretString': json.dumps({"WEBHOOK_SECRET": "mock_secret"})
    }
    with mock_boto3_client(mock_client):
        secret = secret_manager.get_secret()
        assert secret == "mock_secret"

# Assert that HTTP 500 status exception is raised when get_secret_value fails
def test_secret_manager_get_secret_exception():
    reset_app_state()
    mock_client = Mock()
    mock_client.get_secret_value.side_effect = Exception("Error")
    with mock_boto3_client(mock_client):
        try:
            secret_manager.get_secret()
        except Exception as e:
            assert e.status_code == 500


# Test for missing SecretString
def test_secret_manager_missing_secret_string():
    reset_app_state()
    mock_client = Mock()
    mock_client.get_secret_value.return_value = {'SecretString': None}
    with mock_boto3_client(mock_client):
        try:
            secret_manager.get_secret()
        except ValueError as e:
            assert "SecretString" in str(e)

# Test for missing WEBHOOK_SECRET
def test_secret_manager_missing_webhook_secret():
    reset_app_state()
    mock_client = Mock()
    mock_client.get_secret_value.return_value = {
        'SecretString': json.dumps({})
    }
    with mock_boto3_client(mock_client):
        try:
            secret_manager.get_secret()
        except ValueError as e:
            assert "WEBHOOK_SECRET" in str(e)

client = TestClient(app)

# Test for valid webhook request
@patch('app.main.secret_manager.get_secret', return_value='mock_secret')
@patch('subprocess.run')
def test_webhook_valid_signature(mock_subprocess_run, mock_get_secret):
  reset_app_state()
  mock_subprocess_run.return_value.returncode = 0
  payload = {
    "debug_mode": "false",
    "repo_url": "git@github.com:thunkingspot/aqua.git",
    "repo_mgt_dir": "mgt",
    "phase": "deploy",
    "phase_script": "deploy.sh",
    "container_name": "aqua-app",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
  }
  raw_body = json.dumps(payload).encode('utf-8')
  signature = 'sha256=' + hmac.new('mock_secret'.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

  response = client.post(
    "/mgtapi",
    headers={"X-Hub-Signature-256": signature},
    data=raw_body
  )

  assert response.status_code == 200
  assert response.json() == {"message": "Deployment triggered"}
  mock_subprocess_run.assert_called_once()
  args, kwargs = mock_subprocess_run.call_args
  assert args[0][2] == payload["container_name"]
  assert args[0][3] == payload["repo_url"]
  assert args[0][4] == payload["repo_mgt_dir"]
  assert args[0][5] == payload["phase"]
  assert args[0][6] == payload["phase_script"]

# Test for invalid signature
@patch('app.main.secret_manager.get_secret', return_value='mock_secret')
@patch('subprocess.run')
def test_webhook_invalid_signature(mock_subprocess_run, mock_get_secret):
    reset_app_state()
    payload = {
        "debug_mode": "false",
        "repo_url": "git@github.com:thunkingspot/aqua.git",
        "repo_mgt_dir": "mgt",
        "phase": "deploy",
        "phase_script": "deploy.sh",
        "container_name": "aqua-app",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    raw_body = json.dumps(payload).encode('utf-8')
    signature = 'sha256=' + hmac.new('invalid_secret'.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    response = client.post(
        "/mgtapi",
        headers={"X-Hub-Signature-256": signature},
        data=raw_body
    )

    assert response.status_code == 403

# Test for missing X-Hub-Signature-256 header
def test_webhook_missing_signature():
    reset_app_state()
    raw_body = json.dumps({"na": "na"}).encode('utf-8')

    response = client.post(
        "/mgtapi",
        data=raw_body
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid signature"}

# Test for reused signature
@patch('app.main.secret_manager.get_secret', return_value='mock_secret')
@patch('subprocess.run')
def test_webhook_reused_signature(mock_subprocess_run, mock_get_secret):
    reset_app_state()
    payload = {
        "debug_mode": "false",
        "repo_url": "git@github.com:thunkingspot/aqua.git",
        "repo_mgt_dir": "mgt",
        "phase": "deploy",
        "phase_script": "deploy.sh",
        "container_name": "aqua-app",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    raw_body = json.dumps(payload).encode('utf-8')
    signature = 'sha256=' + hmac.new('mock_secret'.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    # First request
    response = client.post(
        "/mgtapi",
        headers={"X-Hub-Signature-256": signature},
        data=raw_body
    )
    assert response.status_code == 200

    # Second request with the same signature
    response = client.post(
        "/mgtapi",
        headers={"X-Hub-Signature-256": signature},
        data=raw_body
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Signature has already been used"}

# Test for invalid JSON payload
@patch('app.main.secret_manager.get_secret', return_value='mock_secret')
def test_webhook_invalid_json(mock_get_secret):
    reset_app_state()
    raw_body = b"invalid json"
    signature = 'sha256=' + hmac.new('mock_secret'.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    response = client.post(
        "/mgtapi",
        headers={"X-Hub-Signature-256": signature},
        data=raw_body
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid JSON payload"}

# Test for invalid timestamp format
@patch('app.main.secret_manager.get_secret', return_value='mock_secret')
def test_webhook_invalid_timestamp_format(mock_get_secret):
    reset_app_state()
    payload = {
        "debug_mode": "false",
        "repo_url": "git@github.com:thunkingspot/aqua.git",
        "repo_mgt_dir": "mgt",
        "phase": "deploy",
        "phase_script": "deploy.sh",
        "container_name": "aqua-app",
        "timestamp": "invalid-timestamp"
    }
    raw_body = json.dumps(payload).encode('utf-8')
    signature = 'sha256=' + hmac.new('mock_secret'.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    response = client.post(
        "/mgtapi",
        headers={"X-Hub-Signature-256": signature},
        data=raw_body
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid timestamp format"}

# Test for timestamp outside allowed range
@patch('app.main.secret_manager.get_secret', return_value='mock_secret')
def test_webhook_timestamp_outside_allowed_range(mock_get_secret):
    reset_app_state()
    payload = {
        "debug_mode": "false",
        "repo_url": "git@github.com:thunkingspot/aqua.git",
        "repo_mgt_dir": "mgt",
        "phase": "deploy",
        "phase_script": "deploy.sh",
        "container_name": "aqua-app",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 100))
    }
    raw_body = json.dumps(payload).encode('utf-8')
    signature = 'sha256=' + hmac.new('mock_secret'.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    response = client.post(
        "/mgtapi",
        headers={"X-Hub-Signature-256": signature},
        data=raw_body
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid timestamp"}

# Test for deployment script failure
@patch('app.main.secret_manager.get_secret', return_value='mock_secret')
@patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'cmd'))
def test_webhook_deployment_script_failure(mock_subprocess_run, mock_get_secret):
    reset_app_state()
    payload = {
        "debug_mode": "false",
        "repo_url": "git@github.com:thunkingspot/aqua.git",
        "repo_mgt_dir": "mgt",
        "phase": "deploy",
        "phase_script": "deploy.sh",
        "container_name": "aqua-app",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    raw_body = json.dumps(payload).encode('utf-8')
    signature = 'sha256=' + hmac.new('mock_secret'.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    response = client.post(
        "/mgtapi",
        headers={"X-Hub-Signature-256": signature},
        data=raw_body
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Error running deployment script"}