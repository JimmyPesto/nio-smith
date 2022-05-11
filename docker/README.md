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

Copy `sample.config.yaml` to a file named `config.yaml` inside of the `data/config/` directory. Fill it out as you normally would, with a few minor
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

First, create all external volumes for managing the container state. Make sure to use an absolute path to the directory used for the volumes or run the following commands from the root of this project:

```
sudo docker volume create \
  --opt type=none \
  --opt o=bind \
  --opt device="${PWD}/data/state" nio-state
sudo docker volume create \
  --opt type=none \
  --opt o=bind \
  --opt device="${PWD}/plugins/cashup/cashup.json" plugin-cashup-state
```

Test the bot with the following command to see the console outputs:
```
sudo docker-compose up nio-smith
```
Run the bot as background deamon with:
```
sudo docker-compose up -d nio-smith
```


## Systemd

**TODO**

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
