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

# Variables
LAUNCH_TEMPLATE_NAME="AquaAppLaunchTemplate"
#AMI_ID="ami-0606dd43116f5ed57" # Replace with your desired Ubuntu AMI ID
AMI_ID="ami-00e95891e6974bdb8"
INSTANCE_TYPE="t2.micro"
KEY_NAME="aqua-key2" # Replace with your key pair name
SECURITY_GROUP_ID="sg-0325c8c81e5fa39f1" # Replace with your security group ID
SUBNET_ID="subnet-0d88855b1a0af17eb" # Replace with your subnet ID

# Create/Update Launch Template (use the first command to create a new launch
# template and the second command to update an existing launch template)
#aws ec2 create-launch-template \
aws ec2 create-launch-template-version \
  --launch-template-name $LAUNCH_TEMPLATE_NAME \
  --version-description "Updated version" \
  --launch-template-data '{
    "ImageId": "'$AMI_ID'",
    "InstanceType": "'$INSTANCE_TYPE'",
    "KeyName": "'$KEY_NAME'",
    "TagSpecifications": [
      {
        "ResourceType": "instance",
        "Tags": [
          {
            "Key": "THUNKINGSPOTLLC",
            "Value": "AQUA-APP"
          }
        ]
      }
    ],
    "NetworkInterfaces": [
      {
        "AssociatePublicIpAddress": false,
        "DeviceIndex": 0,
        "SubnetId": "'$SUBNET_ID'",
        "Groups": ["'$SECURITY_GROUP_ID'"]
      }
    ],
    "IamInstanceProfile": {
      "Name": "AquaHostRole"
    }
  }'
