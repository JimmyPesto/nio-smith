# Docker
The docker image will run AssistantNio with a SQLite database and
end-to-end encryption dependencies included.

## Setup

### Creating a config file

Copy `sample.config.yaml` to a file named `config.yaml` inside of the `data/config/` directory.

Change any config values as necessary. For instance, you may also want to add all files that need write access during
the runtime into the "./data/state/" directory which will be mounted with read and write access rights.


## state volume
First, create an external volumes for managing the container state. Make sure to use an absolute path to the directory used for the volumes or run the following command **from the root of this project**:
```
sudo docker volume create \
  --opt type=none \
  --opt o=bind \
  --opt device="${PWD}/data/state" AssistantNio-state
```
This state will be persisted between different builds.

Test the bot with the following command to see the console outputs:
```
sudo docker-compose up assistantnio
```
Run the bot as background demon with:
```
sudo docker-compose up -d assistantnio
```
