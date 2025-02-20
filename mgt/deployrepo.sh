    DEBUG_MODE=true
    if [ "$1" == "false" ]; then
      DEBUG_MODE=false
    fi

    # Clean up old containers and images
    # Do this first because it will leave the current version alone
    sudo docker image prune -f
    sudo docker stop $(sudo docker ps -a -q --filter ancestor=$4)
    containers=$(sudo docker ps -a -q --filter ancestor=$4)
    if [ $(echo "$containers" | wc -l) -gt 1 ]; then
      sudo docker rm $(echo "$containers" | tail -n +2)
    fi

    # Clone git repo to temporary directory
    CURRENT_DIR=$(pwd)
    TEMP_DIR=$(mktemp -d)
    git clone $2 $TEMP_DIR
    cd $TEMP_DIR

    # Run the build and deploy script in the repo
    /bin/bash ./$3 $DEBUG_MODE

    # Clean up the temporary directory
    cd $CURRENT_DIR
    rm -rf $TEMP_DIR