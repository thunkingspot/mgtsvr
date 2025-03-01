set -e

CONTAINER_NAME=$1
REPO_URL=$2
REPO_MGT_DIR=$3
PHASE=$4
PHASE_SCRIPT=$5
DEBUG_MODE=false
if [ "$6" == "true" ]; then
  DEBUG_MODE=true
fi

# Define AWS details
AWS_REGION="us-west-2"
ELB_ARN="arn:aws:elasticloadbalancing:us-west-2:164348132997:loadbalancer/app/THUNKINGSPOTLLC-SVCS/b3d24b7dd2df1dcf"
AWS_INSTANCE_USER="ubuntu"
AWS_KEY_PATH="/home/ubuntu/.ssh/aqua-key2.pem"

# Define staging directory for build artifacts
STAGE_DIR=/home/ubuntu/stage

if [ "$PHASE" == "build" ]; then
  echo "Building Docker image..."
  # /bin/bash mgt/deployrepo.sh aqua-app git@github.com:thunkingspot/aqua.git mgt build buildrepo.sh false

  # Create temporary directory for cloning the repo. Rememeber current directory.
  CURRENT_DIR=$(pwd)
  TEMP_DIR=$(mktemp -d)

  # Ensure cleanup happens even if git clone or /bin/bash fail
  #trap 'echo "Cleaning up temporary directory $TEMP_DIR"; cd $CURRENT_DIR; rm -rf $TEMP_DIR' EXIT

  # Clone the repo to a temp directory
  git clone $REPO_URL $TEMP_DIR

  # Run the build script in the repo
  /bin/bash $TEMP_DIR/$REPO_MGT_DIR/$PHASE_SCRIPT $CONTAINER_NAME $REPO_MGT_DIR $TEMP_DIR $STAGE_DIR
elif [ "$PHASE" == "deploy-inactive" ]; then
  echo "Deploying to target group..."
  # /bin/bash mgt/deployrepo.sh aqua-app git@github.com:thunkingspot/aqua.git mgt deploy-inactive deploy.sh false

  # Determine the inactive listener ARN (operating on HTTP port 81)
  INACTIVE_LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn $ELB_ARN --region $AWS_REGION --query 'Listeners[?Port==`81`].ListenerArn' --output text)

  # Determine the target group associated with the inactive listener
  INACTIVE_TARGET_GROUP=$(aws elbv2 describe-rules --listener-arn $INACTIVE_LISTENER_ARN --region $AWS_REGION --query 'Rules[*].Actions[*].TargetGroupArn' --output text)

  # Query the inactive target group to get instance IDs
  INSTANCE_IDS=$(aws elbv2 describe-target-health --target-group-arn $INACTIVE_TARGET_GROUP --region $AWS_REGION --query 'TargetHealthDescriptions[*].Target.Id' --output text)

  # Get the IP addresses of the instances
  INSTANCE_IPS=$(aws ec2 describe-instances --instance-ids $INSTANCE_IDS --region $AWS_REGION --query 'Reservations[*].Instances[*].PrivateIpAddress' --output text)

  # Deploy the Docker image to each instance
  for IP in $INSTANCE_IPS; do
    # Run the deploy script in the rstage directory
    /bin/bash $STAGE_DIR/$REPO_MGT_DIR/$PHASE_SCRIPT $CONTAINER_NAME $STAGE_DIR $REPO_MGT_DIR $AWS_KEY_PATH $AWS_INSTANCE_USER $IP $DEBUG_MODE 
  done
elif [ "$PHASE" == "swap" ]; then
  # SWAP THE TARGET GROUPS
  echo "Swapping target groups..."
  # /bin/bash mgt/deployrepo.sh aqua-app git@github.com:thunkingspot/aqua.git mgt swap na false

  # Determine the active listener ARN (operating on HTTP port 80)
  # aws elbv2 describe-listeners --load-balancer-arn "arn:aws:elasticloadbalancing:us-west-2:164348132997:loadbalancer/app/THUNKINGSPOTLLC-SVCS/b3d24b7dd2df1dcf" --region "us-west-2" --query 'Listeners[?Port==`80`].ListenerArn' --output text
  ACTIVE_LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn $ELB_ARN --region $AWS_REGION --query 'Listeners[?Port==`80`].ListenerArn' --output text)
  # Determine the inactive listener ARN (operating on HTTP port 81)
  # aws elbv2 describe-listeners --load-balancer-arn "arn:aws:elasticloadbalancing:us-west-2:164348132997:loadbalancer/app/THUNKINGSPOTLLC-SVCS/b3d24b7dd2df1dcf" --region "us-west-2" --query 'Listeners[?Port==`81`].ListenerArn' --output text
  INACTIVE_LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn $ELB_ARN --region $AWS_REGION --query 'Listeners[?Port==`81`].ListenerArn' --output text)

  # Determine the target group associated with the inactive listener
  # aws elbv2 describe-rules --listener-arn "arn:aws:elasticloadbalancing:us-west-2:164348132997:listener/app/THUNKINGSPOTLLC-SVCS/b3d24b7dd2df1dcf/dbb8d3ee6711842b" --region "us-west-2" --query 'Rules[*].Actions[*].TargetGroupArn' --output text
  INACTIVE_TARGET_GROUP=$(aws elbv2 describe-rules --listener-arn $INACTIVE_LISTENER_ARN --region $AWS_REGION --query 'Rules[*].Actions[*].TargetGroupArn' --output text)
  # Determine the target group associated with the active listener
  # aws elbv2 describe-rules --listener-arn "arn:aws:elasticloadbalancing:us-west-2:164348132997:listener/app/THUNKINGSPOTLLC-SVCS/b3d24b7dd2df1dcf/f2c5e056e61768e3" --region "us-west-2" --query 'Rules[*].Actions[*].TargetGroupArn' --output text
  ACTIVE_TARGET_GROUP=$(aws elbv2 describe-rules --listener-arn $ACTIVE_LISTENER_ARN --region $AWS_REGION --query 'Rules[*].Actions[*].TargetGroupArn' --output text)

  # Modify the rules to swap the target groups
  # aws elbv2 modify-listener --listener-arn "arn:aws:elasticloadbalancing:us-west-2:164348132997:listener/app/THUNKINGSPOTLLC-SVCS/b3d24b7dd2df1dcf/f2c5e056e61768e3" --default-actions Type=forward,TargetGroupArn="arn:aws:elasticloadbalancing:us-west-2:164348132997:targetgroup/aqua-green/24e80198d3d6b4d5" --region "us-west-2"
  aws elbv2 modify-listener --listener-arn $ACTIVE_LISTENER_ARN --default-actions Type=forward,TargetGroupArn=$INACTIVE_TARGET_GROUP --region $AWS_REGION
  # aws elbv2 modify-listener --listener-arn "arn:aws:elasticloadbalancing:us-west-2:164348132997:listener/app/THUNKINGSPOTLLC-SVCS/b3d24b7dd2df1dcf/dbb8d3ee6711842b" --default-actions Type=forward,TargetGroupArn="arn:aws:elasticloadbalancing:us-west-2:164348132997:targetgroup/aqua-blue/dc8fe40b380c5fac" --region "us-west-2"
  aws elbv2 modify-listener --listener-arn $INACTIVE_LISTENER_ARN --default-actions Type=forward,TargetGroupArn=$ACTIVE_TARGET_GROUP --region $AWS_REGION
else
  echo "Invalid phase specified. Exiting..."
  exit 1
fi