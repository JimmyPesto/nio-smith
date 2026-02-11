[![Status: Archived](https://img.shields.io/badge/status-archived-red.svg)](https://github.com/original-author/original-repo)

This fork is no longer maintained. See the original project for updates.

# AssistantNio

Hello there, I am AssistentNio! I am a unique chatbot designed to assist you with all your Matrix needs. Equipped with the state-of-the-art OpenAI chatbot functionality and a plethora of helpful tools, I help make your everyday tasks easier. Whether it's setting reminders, share expenses in a group, or looking up information, I am here to help you streamline your daily life. So let's get started!

This plugin-based bot for [@matrix-org](https://github.com/matrix-org) is written in python using
[matrix-nio](https://matrix-nio.readthedocs.io/en/latest/nio.html), supporting end-to-end-encryption out of the box.  
It's based on the lovely [nio-smith](https://github.com/alturiak/nio-smith/blob/master/README.md) by [@alturiak](https://github.com/alturiak) and [nio-template](https://github.com/anoadragon453/nio-template) by [@anoadragon453](https://github.com/anoadragon453).

Pull Requests and feedback welcome. :-)

## Included Plugins
- `aichat`: **interact with OpenAI's chat-based models, including GPT.** ([README.md](./plugins/aichat/README.md), Contributed by [JimmyPesto](https://github.com/JimmyPesto))
- `cashup`: settle expenses among a group ([README.md](./plugins/cashup/README.md), Contributed by [JimmyPesto](https://github.com/JimmyPesto))
- `dates`: stores dates and birthdays, posts reminders ([README.md](./plugins/dates/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `echo`: echoes back text following the command. ([README.md](./plugins/echo/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `federation_status`: Checks federation-status of all connected homeservers ([README.md](./plugins/federation_status/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `help`: lists all available plugins. If called with a plugin as parameter, lists all available commands ([README.md](./plugins/help/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `manage_bot`: Various commands to manage the bot interactively. ([README.md](./plugins/manage_bot/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `meter`: Plugin to provide a simple, randomized meter ([README.md](./plugins/meter/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `oracle`: predicts the inevitable future (german, sorry) ([README.md](./plugins/oracle/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `pick`: Pick a random item from a given list of items. ([README.md](./plugins/pick/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `quote`: Store conversations as quotes to be displayed later. ([README.md](./plugins/quote/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `roll`: Roll one or more dice. The trigger is 'roll'. ([README.mde](./plugins/roll/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `sample`: Collection of several sample commands to illustrate usage and maybe serve as a plugin template. ([README.md](./plugins/sample/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `spruch`: Posts a random quote by more or less famous persons. (german, sorry) ([README.md](./plugins/spruch/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `translate`: Provide translations of all room-messages via Google Translate ([README.md](./plugins/translate/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `wiki`: Lookup keywords in various online encyclopedias. ([README.md](./plugins/wiki/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `wissen`: Post a random or specific entry of the database of useless knowledge. (german, sorry) ([README.md](./plugins/wissen/README.md), Contributed by [@alturiak](https://github.com/alturiak))
- `xkcd_comic`: Post a xkcd-comic as image or url. ([README.md](./plugins/xkcd_comic/README.md), Contributed by [@alturiak](https://github.com/alturiak))

Note:
* Automatic loading of plugins can be configured by allow and deny list in the [bot's configuration](./plugins/sample.config.yaml).  
* List of plugins might be extended by plugins from [nio-smith](https://github.com/alturiak/nio-smith/blob/master/README.md) by [@alturiak](https://github.com/alturiak).

See [docs/PLUGINS.md](docs/PLUGINS.md) for further details on plugin capabilities.

## Features
- ✔ configurable command-prefix
- ✔ fuzzy command matching (for the autocorrect-victims among us)
- ✔ silently ignores unknown commands to avoid clashes with other bots using the same command prefix
- ✔ dynamic population of `help`-command with plugins valid for the respective room
- ✔ auto join channels on invite (can be restricted to specified accounts)
- ✔ resilience against temporary homeserver-outages (e.g. during restarts)
- ✔ resilience against exceptions caused by plugins
- ✔ simple rate-limiting to avoid losing events to homeserver-side ratelimiting
- ❌ cross-signing support
- ❌ user-management

## Setup
It is recommended to run AssistantNio using docker compose. [docs/SETUP_DOCKER.md](./docs/SETUP_DOCKER.md) contains a short guide on getting you started.

If you really want to run AssistantNio on your host system, follow [docs/SETUP_NATIVE.md](./docs/SETUP_NATIVE.md).

Don't mix docker and native execution based on the same config file and the same device_id/device_name.

If you really need to execute the code locally (eg. for development) create an additional `data` directory and `config.yaml` file.

## Project Structure
Please see [docs/STRUCTURE.md](docs/STRUCTURE.md) for a description of the project structure and included files.
