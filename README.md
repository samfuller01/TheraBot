# Thera Discord Bot

![Property of CCP Games](https://images.ctfassets.net/7lhcm73ukv5p/1rS96YuV4c29hjKlMM0YYa/873b64b4d5340d6f5ace1a3294c9d00a/ThumbClean.jpg?w=850&fm=jpg&fl=progressive&q=75)

Welcome to the Thera Discord bot! This bot has been specifically designed to help users navigate the Thera wormhole system in EVE Online by providing them with real-time information on current connections and the proximity of various systems to Thera.

## Features

  - Displays the current Thera connections in a Discord channel
  - Provides the closest Thera connection to a give K-space system

## Installation

To install the Thera Discord bot, follow these steps:

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

## Usage

To use the Thera Discord bot, simply type one of the following commands into a channel where the bot is present:

  - `/ping` - tests that the bot is online
  - `/thera` - displays the current Thera connections
  - `/system_lookup <system name>` - provides the closest Thera connection to the given system

## Todo

Below is a list of things that I would like to implement eventually. No promise that any of these things actually get implemented though.

  - Allow a "watchlist system" where the bot will ping certain people or a certain channel if a certain region/regions connect to Thera
  - Add a routing system that lets you know the closest connections from the starting system and destination system
  - Display the current EVE time

## Credits

This bot was created by Sam Fuller. It uses [EVE-Scout's API](https://www.eve-scout.com/) for gathering Thera data.

## License

This project is licensed under the MIT License. See the LICENSE file for details. TheraBot also uses data and images from EVE-Online, which is covered by a separate license from [CPP](https://www.ccpgames.com/). See the `CCP.md` file for more details.
