    DEBUG_MODE=true
    if [ "$1" == "false" ]; then
      DEBUG_MODE=false
    fi

    # Start the SSH agent and add the SSH key
    eval "$(ssh-agent -s)"
    ssh-add ~/.ssh/id_ed25519

    # Clone git repo to temporary directory
    CURRENT_DIR=$(pwd)
    TEMP_DIR=$(mktemp -d)
    git clone $2 $TEMP_DIR
    cd $TEMP_DIR

    # Run the deployment script in the repo
    /bin/bash ./$3 $DEBUG_MODE

    # Clean up the temporary directory
    cd $CURRENT_DIR
    rm -rf $TEMP_DIR