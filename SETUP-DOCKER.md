# Setup

nio-smith is a sample repository of a working Matrix bot that can be taken
and transformed into one's own bot, service or whatever else may be necessary.
Below is a quick setup guide to running the existing bot.

## Install the dependencies

There are two paths to installing the dependencies for development.

### Using `docker-compose`

It is **recommended** to use Docker Compose to run the bot while
developing, as all necessary dependencies are handled for you. After
installation and ensuring the `docker-compose` command works, you need to:

1. Create a data directory and config file by following the
   [docker setup instructions](docker#setup).

2. Create a docker volume pointing to that directory:

   ```
   docker volume create \
     --opt type=none \
     --opt o=bind \
     --opt device="/path/to/data/dir" data_volume
   ```

Run `docker/start-dev.sh` to start the bot.

**Note:** If you are trying to connect to a Synapse instance running on the
host, you need to allow the IP address of the docker container to connect. This
is controlled by `bind_addresses` in the `listeners` section of Synapse's
config. If present, either add the docker internal IP address to the list, or
remove the option altogether to allow all addresses.

### Running natively

If you would rather not or are unable to run docker, the following will
instruct you on how to install the dependencies natively:

#### Install libolm

You can install [libolm](https://gitlab.matrix.org/matrix-org/olm) from source,
or alternatively, check your system's package manager. Version `3.0.0` or
greater is required.

#### Install Python dependencies

Create and activate a Python 3 virtual environment:

```
virtualenv -p python3 env
source env/bin/activate
```

Install python dependencies:

```
pip install -r requirements.txt
```

To install all plugin requirements (specified in each plugin's `requirements.txt`), you may optionally run:
```
find . -iname requirements.txt -exec pip install -r {} \;
```

## Configuration

Copy the sample configuration file to a new `config.yaml` file.

```
cp sample.config.yaml data/config.yaml
```

Edit the config file. The `matrix` section must be modified at least.

## Running

### Docker

Refer to the docker [run instructions](docker/README.md#running).

### Native installation

Make sure to source your python environment if you haven't already:

```
source env/bin/activate
```

Then simply run the bot with:

```
nio-smith
```

You'll notice that "nio-smith" is scattered throughout the codebase. When
it comes time to modifying the code for your own purposes, you are expected to
replace every instance of "nio-smith" and its variances with your own
project's name.

By default, the bot will run with the config file at `./config.yaml`. However, an
alternative relative or absolute filepath can be specified after the command:

```
nio-smith other-config.yaml
```

## Testing the bot works

Invite the bot to a room and it should accept the invite and join.

By default nio-smith comes with an `echo` command. Let's test this now.
After the bot has successfully joined the room, try sending the following
in a message:

```
!c echo I am a bot!
```

The message should be repeated back to you by the bot.

## Going forwards

Congratulations! Your bot is up and running. Now you can modify the code,
re-run the bot and see how it behaves. Have fun!