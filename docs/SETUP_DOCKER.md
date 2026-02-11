Docker Compose Setup
===
The docker image will run AssistantNio with a SQLite database and
automatically uses end-to-end encryption dependencies.

## Clone the repository
* Clone the repository to a path of your choice, e.g. `AssistantNio`:
* If you're looking for a more stable experience, it's recommended to run from the main branch:
  ```bash
  git clone --branch main <insert URL> AssistantNio
  ```

* If you really want the latest development commits, e.g. to submit PRs, check out the develop branch:
  ```bash
  git clone --branch develop <insert URL> AssistantNio
  ```

## Dependencies
* [Docker](https://docs.docker.com/engine/install/ubuntu/#installation-methods) version 23.0.4 or higher
* [docker-compose-plugin](https://docs.docker.com/compose/install/linux/)

## Configuration
* run the following commands from the root directory of this project
* Copy the sample configuration file to a new `data/config/config.yaml` file.
    ```bash
    cp sample.config.yaml data/config/config.yaml
    ```
    Edit the config file. The `matrix` section must be modified at least.


* For each plugin config file you want to edit, create a copy in the `data/config/` directory
    * either manually per plugin like this:
    ```bash
    plugin_name="aichat"
    cp plugins/${plugin_name}/${plugin_name}.sample.yaml data/config/${plugin_name}.yaml
    ```
    * or for all plugins like this (parameters: `from-dir`, `to-dir`):
    ```bash
    ./helpers/copy_plugin_config_files.sh  ./plugins/ ./data/config/
    ```

## State Volume
* Create an external volume where the container state shall be persisted.
Make sure to use an absolute path to the directory used for the volumes or run the following command
**from the root of this project**:
    ```
    sudo docker volume create \
      --opt type=none \
      --opt o=bind \
      --opt device="${PWD}/data/state" AssistantNio-state
    ```
    This state will be persisted between different builds.

## Running
* Open a terminal in the `docker/` directory.

* Test the bot with the following command to see the live console outputs:
    ```
    sudo docker compose up assistantnio
    ```
* Run the bot detached from your terminal with:
    ```
    sudo docker compose up -d assistantnio
    ```
* If you get an error message like
  "=> ERROR [assistantnio builder 4/8] RUN ./scripts/build_and_install_libolm.sh 3.2.15 /python-libs 0.2s"
  just mark the libolm build script as executable `chmod +x build_and_install_libolm.sh `

## Upgrading
* To use the latest state from main, run this from the project root directory:
    ```bash
    git switch main
    git pull
    cd docker
    docker compose down
    docker compose up -d --build
    ```
    make docker compose repeat the build process and start in detached mode.

Enjoy. ;) 