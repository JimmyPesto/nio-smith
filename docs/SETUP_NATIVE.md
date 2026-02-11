Native Setup
===

Running this application natively on your Unix host system is possible but not recommend.  
If you simply want to start talking to Assistant Nio, try the [super awesome docker setup](./SETUP_DOCKER.md) instead.

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

```commandline
sudo apt install libjpeg-dev zlib1g-dev
```

### Install libolm
* You should be able to install [libolm](https://gitlab.matrix.org/matrix-org/olm)
    * from your distribution's package manager e.g. `apt install libolm3 libolm-dev` on Debian/Ubuntu
    * manually build it as in [build_and_install_libolm.sh](../docker/build_and_install_libolm.sh)

### Install Python dependencies

* Change in to the root folder of this repository:
  ```bash
  cd AssistantNio
  ```

* Create and activate a Python 3.10 virtual environment:
  ```bash
  virtualenv -p python3.10 env
  source env/bin/activate
  ```

* Install main python dependencies:
  ```bash
  pip install -r requirements.txt
  ```

* To install all plugin requirements (specified in each plugin's `requirements.txt`), you may run:
  ```bash
  find / -iname requirements.txt -exec pip install --prefix="/python-libs" --no-warn-script-location -r {} \;
  ```
  or just install the requirements on the plugin that interest you.

## Configuration

* Copy the sample configuration file to a new `config.yaml` file.
  ```bash
  cp sample.config.yaml data/config/config.yaml
  ```
* Edit the config file. The `matrix` section must be modified at least.

* Now copy all the plugin config files you want to edit into the `data/config/` directory:
  ```bash
  plugin_name="aichat"
  cp plugins/${plugin_name}/${plugin_name}.sample.yaml data/config/${plugin_name}.yaml.test
  ```
  and edit them accordingly

## Running

* Starting from the projects root directory, make sure to source your python environment if you haven't already:
  ```bash
  source ~/env/bin/activate
  ```

* Then simply run the bot with:
  ```bash
  python main.py
  ```

* By default, the bot will run with the config file at `"./data/config/config.yaml"` and load all plugins from the `plugins`-directory.
You may optionally specify a different config-file and plugins-directory by running:
  ```bash
  python main.py [configfile [plugins_directory]]
  ```
  e.g.
  ```bash
  python main.py myconfig.yaml myplugins
  ```

## Upgrading
* Just use the latest state from main:
  ```bash
  git switch main
  git pull
  ```

* In case of changed requirements, repeat "Install Python dependencies".

Enjoy. ;) 