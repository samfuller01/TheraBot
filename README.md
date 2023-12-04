# Thera Discord Bot

![Property of CCP Games](https://images.ctfassets.net/7lhcm73ukv5p/1rS96YuV4c29hjKlMM0YYa/873b64b4d5340d6f5ace1a3294c9d00a/ThumbClean.jpg?w=850&fm=jpg&fl=progressive&q=75)

Welcome to Thera Discord Bot! This bot has been purpose-built to assist EVE Online players in navigating the Thera wormhole system, providing real-time information on current connections and proximity of various systems to Thera, and routing players through space easily using Thera.

## Features

  - Displays the current Thera connections in a Discord channel
  - Provides the closest Thera connection to a give K-space system
  - Provides the shortest route from one system to another through Thera
  - Displays a map of Pochven
  - Shows the current EVE time

## Installation

To install the Thera Discord bot locally or host it on your own, follow these steps:

1. Clone this repository to your local machine
2. Install the required dependencies by running `pip install -r requirements.txt`
3. Create a new Discord bot and add it to your server
4. Create a .env file (an example one is provided at `.env.example`) with the following variables:

```Dotenv
TOKEN=<your Discord bot token>
GUILD_ID=<your guild id> # This is only needed for quickly syncing the commands with the dev guild
DEV_MODE=<DEV or PROD mode>
```

5. Run the bot by running `python thera.py`

Alternatively, you can invite TheraBot to your discord server [here](https://discord.com/oauth2/authorize?client_id=1080613977500946453&permissions=277025459200&scope=bot%20applications.commands).

## Usage

To use the Thera Discord bot, simply type one of the following commands into a channel where the bot is present:

  - `/ping` - Tests if the bot is online
  - `/thera` - Displays the current Thera connections
  - `/lookup <system name>` - Provides the closest Thera connection to the given system
  - `/route <source system> <destination system>` - Provides the shortest route through Thera from source to destination
  - `/pochven_map` - Provides the map of Pochven
  - `/eve_time` - Provides the current EVE time

## Todo

Below is a list of things that I would like to implement eventually. No promise that any of these things actually get implemented though.

  - Allow a "watchlist system" where the bot will ping certain people or a certain channel if a certain region/regions connect to Thera
  - ~~Add a routing system that lets you know the closest connections from the starting system and destination system~~ Update: Done
  - ~~Display the current EVE time~~ Update: Done

## Credits

This bot was created by Sam Fuller. It uses [EVE-Scout's API](https://www.eve-scout.com/) for gathering Thera data.

## License

This project is licensed under the MIT License. See the LICENSE file for details. TheraBot also uses data and images from EVE-Online, which is covered by a separate license from [CPP](https://www.ccpgames.com/). See the `CCP.md` file for more details.
