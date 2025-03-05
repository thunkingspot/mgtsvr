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

Manual steps to create Aqua app in AWS
- Create an ed25519 pem key pair in the AWS account named aqua-key as ssh key for managed instances. Public key should be placed in aqua/ssh/aqua-key.pem
- Create policy called AquaDeployRole using aqua/awsinfra/AquaDeployPolicy 
  - Consider whether the policy should only be allowed to be applied to the management instance...
- Create role AquaDeployRole - AWS Service role for ec2.
  - Attach AquaDeployPolicy to the role
  - Attach AmazonDynamoDBFullAccess to the role
  - Attach AmazonS3FullAccess to the role
- Attach the AquaDeployRole to the management instance being used for deployment (might be a desktop instance).
- Create a role AquaHostRole - to give necessary permissions to the host instances (S3, Dynamo)
  - Attach AquaInstancePolicy
  - Attach AmazonDynamoDBFullAccess to the role
  - Attach AmazonS3FullAccess to the role
  - Add it as an instance role launch template
- Make sure AWS CLI is installed on the management instance.
- Run the script CreateAquaAppLaunchTemplate to create the launch template in the AWS account.
  sudo bash ./CreateAquaAppLaunchTemplate.sh
- If the template is confirmed good update the default version to be used to the new version.
  sudo bash ./SetDefaultAquaAppLaunchTemplate.sh
- (for now) To create the app instances run the following command from the awsinfra directory:
  aws ec2 run-instances --launch-template LaunchTemplateName=AquaAppLaunchTemplate,Version=$Latest --region us-west-2 --count 2
- To itemize, start and stop intances:
    aws ec2 describe-instances --region us-west-2
    aws ec2 start-instances --instance-ids i-0ffa02efb2ec50524 i-0342f1e90f9c9ba85 --region us-west-2
    aws ec2 stop-instances --instance-ids i-0ffa02efb2ec50524 i-0342f1e90f9c9ba85 --region us-west-2
- Create FastAPI app
  Python is installed. But need to install python3.10-venv for virtual env
    sudo apt install python3.10-venv
    from mgtsvr directory
    create private venv
      python3 -m venv venv
      source venv/bin/activate (deactivate to shutdown virtual env)
    with venv active
      - for app
        pip install fastapi uvicorn boto3
      - for tests
        pip install pytest httpx
      - install app as a package for testing
        - from app directory (to mark it as a package)
          - touch __init__.py
        - from project root (where setup.py is located)
          - pip install -e .
      - from tests directory
        - pytest
- Python Test Runner
  - Install Pytest runner
  - Add settings.json 
- Run the fastapi server - --reload automatically detects changes when in dev cycle
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
- Setup website with Nginx
  sudo apt update
  sudo apt install nginx
- Modify appinfra/nginx_aqua.conf to work with app files.
  setting the proxy for /api/ means that the api will be stripped from the request and if you want the routes to refer to it make sure the proxy_pass line in the conf includes it - e.g. - http://localhost:8000/mgtapi
- Create a symbolic link to enable the configuration by linking it to the sites-enabled directory.
  sudo ln -s /home/ubuntu/src/mgtsvr/appinfra/nginx_mgtapi.conf /etc/nginx/sites-enabled/
- Remove the default Nginx configuration link to avoid conflicts.
  sudo rm /etc/nginx/sites-enabled/default
- Test Nginx configuration to ensure there are no syntax errors.
  sudo nginx -t
- Reload Nginx to apply the new configuration.
  sudo systemctl reload nginx
- Nginx start, stop, restart
  sudo systemctl xxx nginx
- Nginx logs
  sudo tail -f /var/log/nginx/error.log
- Debugging Python
  Create a .vscode directory in your workspace if it doesn't already exist.
  Create a launch.json file inside the .vscode directory with the following configuration:
- Management Instance
  In the extreme it could be containerized as well but it seems like it would be suitable to just configure the instance and create an AMI that can be instantiated if more are needed. There would need to be some late bound conf if more than one is needed and it wouldn't take long before now that start sounding like a cluster of managment instances running behind a load balancer... blah blah. At that point it's worth considering whether it makes sense to keep rolling your own. This can be a lighter weight instance (no ui) that is separate from the desktop instance. But... maybe not. For the moment we need to support a webhook-like tcp server for triggering. So some of the config will move out of aqua and into mgtsvr. Aqua is targeted for automated deployment. mgtsvr not so much.
  1. Note: managing the github range is an exercise. This needs to be revisited. Create a security group to allow webhook access to the management instance (sg-0669c0b51e9894f4d - management-webhook-sg), allow only the managment instance IP and the github ip range. Not using SSL...yet. 
  3. Add the webhook secret to aws secret manager and as a github repository secret. Don't use a webhook defined by github. Use a workflow_dispatch action and emulate the webhook encryption approach. This does not encrypt the payload. It just allows a signature for the payload to validate authenticity, plus some management of a timestamp included in the payload to prevent replay attacks.
- change github to use a key without a passphrase (for automation)
- Setup Load balancer and API Gateway
  - Application Load Balancer
    - internal
    - AZ - private thunkingspot subnets on us-west-2a and 2b
    - make sure when creating instances you select the correct subnet
    - security groups need to allow ssh (port 22)
    - network acls also need to allow port 22
  - API Gateway
    - TBD
  - Configuring hosts (things that needed to be done)
    - make sure aqua-key2.pem is in .ssh directory of client
    - for creating/updating the ami you need to create an instance in the public subnet to have access to the internet and in the advanced network settings you need to enable "auto-assign public ip"
    - Launch template needs to include a role that gives access to S3 (AquaHostRole)
    - ssh -i /home/ubuntu/.ssh/aqua-key2.pem 10.0.x.x
      - when generating the pem file may need to download from a linux client - keys generated on windows client can be problematic.
    - install docker (follow readme.md)
    - create hosts
    - add hosts to respective target groups


