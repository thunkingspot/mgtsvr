Manual steps to create Aqua app in AWS
- Create an ed25519 pem key pair in the AWS account named aqua-key as ssh key for managed instances. Public key should be stored in aqua/ssh/aqua-key.pem (also in password vault with AWS info, but not in GitHub)
- Create policy called AquaDeployRole using aqua/awsinfra/AquaDeployPolicy 
  - Consider whether the policy should only be allowed to be applied to the management instance...
- Create role AquaDeployRole - AWS Service role for ec2.
  - Attach AquaDeployPolicy to the role
  - Attach AmazonDynamoDBFullAccess to the role
  - Attach AmazonS3FullAccess to the role
  - May need to attach SecretsManagerReadWrite... not sure yet
- Create role EC2DynamoDbAccessRole - AWS Service role for ec2. This role will be passed to the Aqua app instances and is what they need.
  - Attach AmazonDynamoDBFullAccess to the role
  - Attach AmazonS3FullAccess to the role
  - Attach SecretsManagerReadWrite... not sure yet if this is being used
- Attach the AquaDeployRole to the management instance being used for deployment (might be a desktop instance).
- Launch template also assumes the management instance also belongs to a security group that the app instances will also belong to. This might be more relevant if the management instance is also a development instance (e.g. a desktop instance)
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
    mkdir /home/ubuntu/src/mgtsvr/app
    then create private env
      python3 -m venv venv
      source venv/bin/activate (deactivate to shutdown virtual env)
    with venv active
      pip install fastapi uvicorn boto3
- Run the fastapi server - --reload automatically detects changes when in dev cycle
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
- Setup website with Nginx
  sudo apt update
  sudo apt install nginx
- Create web root directory for static files.
  sudo mkdir -p /var/www/aqua_app
  sudo cp -r /home/ubuntu/src/examples/aqua/app/website/* /var/www/aqua_app/
  Set permissions for the web root directory.
    sudo chown -R www-data:www-data /var/www/aqua_app
    sudo chmod -R 755 /var/www/aqua_app
- Modify appinfra/nginx_aqua.conf to work with app files.
  setting the proxy for /api/ means that the api will be stripped from the request and should not be included in the routes on the app side
- Create a symbolic link to enable the configuration by linking it to the sites-enabled directory.
  sudo ln -s /home/ubuntu/src/examples/mgtsvr/appinfra/nginx_mgtapi.conf /etc/nginx/sites-enabled/
- Remove the default Nginx configuration link to avoid conflicts.
  sudo rm /etc/nginx/sites-enabled/default
- Test Nginx configuration to ensure there are no syntax errors.
  sudo nginx -t
- Reload Nginx to apply the new configuration.
  sudo systemctl reload nginx
- Nginx start, stop, restart
  sudo systemctl xxx nginx
- Debugging Python
  Create a .vscode directory in your workspace if it doesn't already exist.
  Create a launch.json file inside the .vscode directory with the following configuration:
- Install Docker Engine (https://docs.docker.com/engine/install/ubuntu/)
  1. for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done
  2. add the docker respository to apt sources
    # Add Docker's official GPG key:
    sudo apt-get update
    sudo apt-get install ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc

    # Add the repository to Apt sources:
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
  3. Install Docker
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  4. Test
    sudo docker run hello-world
- Install the Docker VSCode extension
  Future - the rootless operation material and set that up https://docs.docker.com/engine/security/rootless/
- Create Dockerfile in project root
- Create requirements.txt in service directory
- Create a docker specific nginx config file appinfra/nginx_aqua_docker.conf
- Determine if rootless docker would eliminate need to run docker commands as sudo
- Build the docker image
    cd /home/ubuntu/src/examples/aqua
    sudo docker build -t aqua-app .
- Run the docker image
    sudo docker run -d -p 80:80 aqua-app
- Things that needed to be done to get app to run in container
  1. Create entrypoint.sh in root directory
      chmod +x entrypoint.sh

      The container might be exiting immediately because the CMD command is not keeping the container running. This can happen if either Nginx or Uvicorn fails to start, or if they start in the background and the main process exits.

      This was not the case - but it provides a way to get some diagnostic steps in the process. Added an nginx validation to the entrypoint shell
  2. nginx_aqua_docker.conf was not valid as a global nginx.conf file... which is how it was being setup in the dockerfile (thank you copilot). What needed to happen was that a global nginx.conf file needed to be created that includes the nginx_aqua_docker.conf from a conf.d directory. This is location typically used in containers for nginx app conf similar to the sites-enabled directory. But these configs are global rather than site specific. It's more straight forward and if it works for the container it's the way to go.
  3. libglibgl1-mesa-glx and libglib2.0-0 are dependencies for opencv (cv2 - used by the app). It was not included as part of the python virtual env because it was already installed for the OS. This should be installed as part of the dockerfile. (Could it be installed in the venv?)
- Management Instance
  Need to back up step and think about how the management instance will be configured. In the extreme it could be containerized as well but it seems like it would be suitable to just configure the instance and create an AMI that can be instantiated if more are needed. There would need to be some late bound conf if more than one is needed and it wouldn't take long before now that start sounding like a cluster of managment instances running behind a load balancer... blah blah. Let's just not go there. We may want this to be a lighter weight instance (no ui) that is separate from the desktop instance. But... maybe not. For the moment we need to support a webhook tcp server for triggering. So some of the config will move out of aqua and into mgtsvr. Aqua is targeted for automated deployment. mgtsvr not so much.
  1. Create a security group to allow webhook access to the management instance (sg-0669c0b51e9894f4d - management-webhook-sg), allow only the managment instance IP and the github ip range. Not using SSL, but payload is encrypted.
  2. remove the symbolic link to nginx_aqua.conf in the aqua project and replace it with the nginx_mgtapi.conf
  3. add the webhook secret to aws secret manager and as a github repository secret. Don't use a webhook defined by github. Use a workflow_dispatch action and emulate the webhook encryption approach.