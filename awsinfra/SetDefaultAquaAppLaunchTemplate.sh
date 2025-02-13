#!/bin/bash

# Variables
LAUNCH_TEMPLATE_NAME="AquaAppLaunchTemplate"

# Get the latest version number of the launch template
latest_version=$(aws ec2 describe-launch-template-versions \
  --launch-template-name $LAUNCH_TEMPLATE_NAME \
  --query 'LaunchTemplateVersions | sort_by(@, &VersionNumber) | [-1].VersionNumber' \
  --output text)

if [ -z "$latest_version" ]; then
  echo "No versions found for launch template $LAUNCH_TEMPLATE_NAME."
  exit 1
fi

# Set the latest version as the default version
aws ec2 modify-launch-template \
  --launch-template-name $LAUNCH_TEMPLATE_NAME \
  --default-version $latest_version

echo "Default version of launch template $LAUNCH_TEMPLATE_NAME set to version $latest_version."