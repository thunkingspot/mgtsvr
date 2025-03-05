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