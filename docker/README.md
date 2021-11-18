# Docker

The docker image will run nio-smith with a SQLite database and
end-to-end encryption dependencies included. For larger deployments, a
connection to a Postgres database backend is recommended.

## Setup

### The `/data` volume

The docker container expects the `config.yaml` file to exist at
`/data/config.yaml`. 

We'll later mount this directory into the container so that its contents
persist across container restarts.

### Creating a config file

Copy `sample.config.yaml` to a file named `config.yaml` inside of the `data` directory. Fill it out as you normally would, with a few minor
differences:

* The path to the database should reside inside of the data directory.
* The bot store directory should reside inside of the data directory so that it
  is not wiped on container restart. Change it from the default to
  `/data/store`. There is no need to create this directory yourself, it will be
  created on startup if it does not exist.
* The file to store execution times of timers for plugins should reside inside of the data directory.

Change any other config values as necessary. For instance, you may also want to
store log files in the `/data` directory.

## Running

First, create a volume for the data directory created in the above section. Make sure to use an absolute path to the directory used for the state volume:

```
docker volume create \
  --opt type=none \
  --opt o=bind \
  --opt device="/path/to/data/dir" state_volume
sudo docker volume create \
  --opt type=none \
  --opt o=bind \
  --opt device="~/bot/nio-smith/data/state" nio-state
```

TODO delete or implement docker hub stuff!
#Start the bot with:
#
#```
#docker-compose up nio-smith
#```
#
#This will run the bot and log the output to the terminal. You can instead run
#the container detached with the `-d` flag:
#
#```
#docker-compose up -d nio-smith
#```
#
#(Logs can later be accessed with the `docker logs` command).
#
#This will use the `latest` tag from
#[Docker Hub](https://hub.docker.com/somebody/nio-smith).

To run from the checked out code, you can use:

```
docker-compose up local-checkout
```

This will build an optimized, production-ready container. If you are developing
instead and would like a development container for testing local changes, use
the `docker/start-dev.sh` script.

**Note:** If you are trying to connect to a Synapse instance running on the
host, you need to allow the IP address of the docker container to connect. This
is controlled by `bind_addresses` in the `listeners` section of Synapse's
config. If present, either add the docker internal IP address to the list, or
remove the option altogether to allow all addresses.

TODO delete or implement docker hub stuff!
##Updating
#
#To update the container, navigate to the bot's `docker` directory and run:
#
#```
#docker-compose pull nio-smith
#```
#
#Then restart the bot.

## Systemd

A systemd service file is provided for your convenience at
[nio-smith.service](nio-smith.service). The service uses
`docker-compose` to start and stop the bot.

Copy the file to `/etc/systemd/system/nio-smith.service` and edit to
match your setup. You can then start the bot with:

```
systemctl start nio-smith
```

and stop it with:

```
systemctl stop nio-smith
```

To run the bot on system startup:

```
systemctl enable nio-smith
```

## Building the image

To manually build a production image from source, use the following `docker build` command
from the repo's root:

```
docker build -t $USER/nio-smith:latest -f docker/Dockerfile .
```
