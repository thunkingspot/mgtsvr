set -e

DEBUG_MODE=true
if [ "$1" == "false" ]; then
  DEBUG_MODE=false
fi

# Clean up old containers and images. Don't fail if there are no containers or images to clean up.
# Do this first because it will leave the current version alone
if [ "$(sudo docker ps -q)" ]; then
  sudo docker stop $(sudo docker ps -q)
  sudo docker container prune -f
fi
sudo docker image prune -f || true

# Clone git repo to temporary directory
CURRENT_DIR=$(pwd)
TEMP_DIR=$(mktemp -d)

# Ensure cleanup happens even if git clone or /bin/bash fail
trap 'echo "Cleaning up temporary directory $TEMP_DIR"; cd $CURRENT_DIR; rm -rf $TEMP_DIR' EXIT

git clone $2 $TEMP_DIR
cd $TEMP_DIR

# Run the build and deploy script in the repo
/bin/bash ./$3 $DEBUG_MODE

echo "Cleaning up temporary directory $TEMP_DIR"
cd $CURRENT_DIR
rm -rf $TEMP_DIR