#!/bin/bash

# Variables
LAUNCH_TEMPLATE_NAME="AquaAppLaunchTemplate"
AMI_ID="ami-0606dd43116f5ed57" # Replace with your desired Ubuntu AMI ID
INSTANCE_TYPE="t2.micro"
KEY_NAME="aqua-key" # Replace with your key pair name
SECURITY_GROUP_ID="sg-00196a0fb1d7d35fd" # Replace with your security group ID
SUBNET_ID="subnet-097c7289038dc51df" # Replace with your subnet ID

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
    ]
  }'
