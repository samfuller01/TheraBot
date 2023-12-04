import discord
import os
import requests
import logging
import logging.handlers
import datetime
import pytz
import base64
import json
from typing import List
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

# load global and environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DEV_GUILD_ID = os.getenv('DEV_GUILD_ID')
GUILD = discord.Object(id=DEV_GUILD_ID)
DEV_MODE = os.getenv('DEV_MODE')
ESI_CLIENT_ID = os.getenv('ESI_CLIENT_ID')
ESI_SECRET = os.getenv('ESI_SECRET_KEY')
ESI_REFRESH_TOKEN = os.getenv('ESI_REFRESH_TOKEN')
EVE_SCOUT_API_URL = 'https://www.eve-scout.com/api/wormholes'
EVE_TOKEN_URL = 'https://login.eveonline.com/v2/oauth/token'

credentials = f'{ESI_CLIENT_ID}:{ESI_SECRET}'
encoded_credentials = base64.b64encode(credentials.encode(encoding='utf-8')).decode(encoding='utf-8')

# set up logging
logger = logging.getLogger('bot')
if DEV_MODE == 'DEV':
  logger.setLevel(logging.DEBUG)
  logging.getLogger('discord.http').setLevel(logging.DEBUG)
else:
  logger.setLevel(logging.INFO)
  logging.getLogger('discord.http').setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)

class TheraBotClient(discord.Client):
  def __init__(self, *, intents: discord.Intents) -> None:
    super().__init__(intents=intents)
    # count how many times the access token and thera api is accessed
    self.thera_counter = 0
    self.access_counter = 0
    # variables to store response data
    self.wormholes = None
    self.access_token = None
    # discord command things
    self.tree = app_commands.CommandTree(self)

  async def on_ready(self) -> None:
    logger.info(f'logged on as {self.user}')
    # start task loop of fetching info from API and fetching access tokens.
    self.fetch_thera_api.start()
    self.fetch_access_token.start()
  # if bot reconnects start fetching data again
  async def on_resumed(self) -> None:
    await self.fetch_thera_api.start()
    await self.fetch_access_token.start()
  # if bot goes down stop pinging external API's
  async def on_disconnect(self) -> None:
    await self.fetch_thera_api.cancel()
    await self.fetch_access_token.cancel()

  async def setup_hook(self) -> None:
    if DEV_MODE == 'DEV': # if in development mode sync commands to the development server quickly
      self.tree.copy_global_to(guild=GUILD)
      await self.tree.sync(guild=GUILD)
      print('Started in DEV mode')
    else: # otherwise sync globally slowly
      await self.tree.sync()

  @tasks.loop(minutes=20)
  async def fetch_access_token(self) -> None:
    header = {
      'Authorization': f'Basic {encoded_credentials}',
      'Content-Type': 'application/x-www-form-urlencoded',
      'Host': 'login.eveonline.com'
    }
    payload = {
      'grant_type': 'refresh_token',
      'refresh_token': ESI_REFRESH_TOKEN
    }
    res = requests.post(url=EVE_TOKEN_URL, headers=header, data=payload)

    if res.status_code != 200:
      logging.debug(res)
      self.access_token = None
    else:
      results = res.json()
      self.access_token = results['access_token']
      self.access_counter += 1
      logger.info(f'retrieved access token successfully - counter: {self.access_counter}')

  @tasks.loop(minutes=10)
  async def fetch_thera_api(self) -> None:
    res = requests.get(url=EVE_SCOUT_API_URL)
    if res.status_code != 200:
      logging.debug(res)
      self.wormholes = None
    else:
      self.wormholes = res.json()
      self.thera_counter += 1
      logger.info(f'retrieved thera data successfully - counter: {self.thera_counter}')

  @fetch_thera_api.before_loop
  async def before_fetch_thera_api(self) -> None:
    await self.wait_until_ready()

  @fetch_access_token.before_loop
  async def before_fetch_access_token(self) -> None:
    await self.wait_until_ready()

intents = discord.Intents.default()
intents.message_content = True
client = TheraBotClient(intents=intents)

@client.tree.command()
async def ping(interaction: discord.Interaction) -> None:
  """Tests that TheraBot is online"""
  await interaction.response.send_message('pong')

@client.tree.command()
async def thera(interaction: discord.Interaction) -> None:
  """Prints out all current Thera connections (data can be up to 10 minutes out of date)"""
  if client.wormholes == None:
    await interaction.response.send_message('Could not access Thera data :(')
    return
  
  battleship_wormholes = ['V898', 'F135', 'M164']
  freighter_wormholes = ['E587', 'L031']
  
  embed = discord.Embed(title='Thera Connections', description='Current Thera wormholes', color=0xffd700)
  embed.set_thumbnail(url='https://images.ctfassets.net/7lhcm73ukv5p/1rS96YuV4c29hjKlMM0YYa/873b64b4d5340d6f5ace1a3294c9d00a/ThumbClean.jpg?w=850&fm=jpg&fl=progressive&q=75')
  for system in client.wormholes:
    system_type = system['destinationWormholeType']['name'] if system['destinationWormholeType']['name'] != 'K162' else system['sourceWormholeType']['name']
    mass_type = 'Large (Freighter)' if system_type in freighter_wormholes else ('Large (Battleship)' if system_type in battleship_wormholes else 'Medium (Cruiser)')
    date_object = datetime.datetime.fromisoformat(str(system['wormholeEstimatedEol']).replace('Z', '+00:00')).replace(tzinfo=pytz.UTC)
    time_difference = date_object - datetime.datetime.now(datetime.timezone.utc)
    hours_remaining = round(time_difference.total_seconds() / 3600)
    name = f"{system['destinationSolarSystem']['name']} ({round(system['destinationSolarSystem']['security'], 2)}) {system['destinationSolarSystem']['region']['name']}"
    value = f"Size: {mass_type}\nEOL Status: {system['wormholeEol']}\nMass Status: {system['wormholeMass']}\nOut Sig: {system['signatureId']}\nIn Sig: {system['wormholeDestinationSignatureId']}\nEst. Life: ~{hours_remaining} hours remain"
    embed.add_field(name=name, value=value, inline=True)
  
  await interaction.response.send_message(embed=embed)

@client.tree.command()
@app_commands.describe(system_name='The name of the system to lookup')
async def lookup(interaction: discord.Interaction, system_name: str) -> None:
  """Finds the closest system to the system provided and tells you the number of jumps (data can be up to 10 minutes out of date)"""
  res = requests.get(EVE_SCOUT_API_URL + f'?systemSearch={system_name}')
  if res.status_code != 200:
    logger.error(res.text)
    await interaction.response.send_message('Could not access Thera data :( Did you spell the system name correctly?')
    return
  
  wormholes = res.json()
  # filter out wormholes that say zero jumps from target system but are not the target system (API says zero jumps for W-Space systems)
  filtered_wormholes = [item for item in wormholes if not (item['jumps'] == 0 and str(item['destinationSolarSystem']['name']).lower() != system_name.lower())]
  # sort the remaining wormholes by how many jumps the connection is from target system
  sorted_wormholes = sorted(filtered_wormholes, key=lambda x: x['jumps'])
  # closest system is the first one in the system 
  # NOTE: I don't know what happens if two systems are equally far apart from target system, I'm guessing it picks whichever one occurs first in the list
  system = sorted_wormholes[0]

  battleship_wormholes = ['V898', 'F135', 'M164']
  freighter_wormholes = ['E587', 'L031']

  embed = discord.Embed(title=f'Closest {system_name.title()} Connection', color=0xffd700)
  embed.set_thumbnail(url='https://images.ctfassets.net/7lhcm73ukv5p/1rS96YuV4c29hjKlMM0YYa/873b64b4d5340d6f5ace1a3294c9d00a/ThumbClean.jpg?w=850&fm=jpg&fl=progressive&q=75')
  system_type = system['destinationWormholeType']['name'] if system['destinationWormholeType']['name'] != 'K162' else system['sourceWormholeType']['name']
  mass_type = 'Large (Freighter)' if system_type in freighter_wormholes else ('Large (Battleship)' if system_type in battleship_wormholes else 'Medium (Cruiser)')
  date_object = datetime.datetime.fromisoformat(str(system['wormholeEstimatedEol']).replace('Z', '+00:00')).replace(tzinfo=pytz.UTC)
  time_difference = date_object - datetime.datetime.now(datetime.timezone.utc)
  hours_remaining = round(time_difference.total_seconds() / 3600)
  name = f"{system['destinationSolarSystem']['name']} ({round(system['destinationSolarSystem']['security'], 2)}) {system['jumps']} Jumps"
  value = f"Region: {system['destinationSolarSystem']['region']['name']}\nSize: {mass_type}\nEst. Life: ~{hours_remaining} hours remain\nMass Status: {system['wormholeMass']}\nOut Sig: {system['signatureId']}\nIn Sig: {system['wormholeDestinationSignatureId']}"
  embed.add_field(name=name, value=value)

  await interaction.response.send_message(embed=embed)

@client.tree.command()
@app_commands.describe(
  source_system='The starting system',
  destination_system='The destination system',
  ship_size='The size of the ship you wish to bring through Thera'
)
async def route(interaction: discord.Interaction, source_system: str, destination_system: str, ship_size: str='') -> None:
  """Finds the shortest route between two systems and tells you the number of jumps and other relevant info"""
  source_res = requests.get(EVE_SCOUT_API_URL + f'?systemSearch={source_system}')
  if source_res.status_code != 200:
    logger.error(source_res.text)
    await interaction.response.send_message('Could not access Thera data :( Did you spell the system name correctly?')
    return
  destination_res = requests.get(EVE_SCOUT_API_URL + f'?systemSearch={destination_system}')
  if destination_res.status_code != 200:
    logger.error(destination_res.text)
    await interaction.response.send_message('Could not access Thera data :( Did you spell the system name correctly?')
    return
  
  gate_jumps = 0
  # Find if it is faster to not go through Thera unless there is no access_token
  if client.access_token != None:
    with open('eve_systems.json') as f:
      system_data = json.load(f)
    src_sys_id = system_data[source_system]['system_id']
    dest_sys_id = system_data[destination_system]['system_id']
    url = f'https://esi.evetech.net/route/{src_sys_id}/{dest_sys_id}'
    header = {
      'Authorization': f'Bearer {client.access_token}'
    }
    res = requests.get(url=url, headers=header)
    
    if res.status_code != 200:
      logger.error(f'error getting route {res}')
      await interaction.response.send_message('Error fetching routes from ESI :(')
      return
    
    result = res.json()
    gate_jumps = len(result)
  
  # wormholes battleships can take
  battleship_wormholes = ['V898', 'F135', 'M164', 'E587', 'L031']
  # wormholes freighters can take 
  freighter_wormholes = ['E587', 'L031']

  source_wormholes = source_res.json()
  destination_wormholes = destination_res.json()

  # Filter out wormhole connects to Thera (The EVE-Scout API says wormhole connections have zero jumps)
  filter_s_wormholes = [item for item in source_wormholes if not (item['jumps'] == 0 and str(item['destinationSolarSystem']['name']).lower() != source_system.lower())]
  filter_d_wormholes = [item for item in destination_wormholes if not (item['jumps'] == 0 and str(item['destinationSolarSystem']['name']).lower() != destination_system.lower())]

  # Lambda function to determine the wormhole type of each Thera connection
  system_type = lambda x: x['destinationWormholeType']['name'] if x['destinationWormholeType']['name'] != 'K162' else x['sourceWormholeType']['name']

  # Filter out wormholes based on ship size
  if ship_size.lower() == 'freighter':
    filter_s_wormholes = [item for item in filter_s_wormholes if system_type(item) in freighter_wormholes]
    filter_d_wormholes = [item for item in filter_d_wormholes if system_type(item) in freighter_wormholes]
  elif ship_size.lower() == 'battleship':
    filter_s_wormholes = [item for item in filter_s_wormholes if system_type(item) in battleship_wormholes]
    filter_d_wormholes = [item for item in filter_d_wormholes if system_type(item) in battleship_wormholes]
  elif ship_size.lower() == 'capital':
    await interaction.response.send_message('You cannot take a true capital ship (dreadnoughts, carriers, fax\'s, supercarriers, or titans) through Thera')
    return
  
  sorted_s_wormholes = sorted(filter_s_wormholes, key=lambda x: x['jumps'])
  sorted_d_wormholes = sorted(filter_d_wormholes, key=lambda x: x['jumps'])

  # Check if the lists are empty
  if not sorted_s_wormholes or not sorted_d_wormholes:
    await interaction.response.send_message('Could not find a route through Thera for the given ship size :(')
    return
  
  closest_to_source = sorted_s_wormholes[0]
  closest_to_dest = sorted_d_wormholes[0]

  battleship_wormholes = ['V898', 'F135', 'M164']
  freighter_wormholes = ['E587', 'L031']

  # Add one because of the jump through Thera itself
  thera_jumps = closest_to_source['jumps'] + closest_to_dest['jumps'] + 1

  # TODO: Add feature to allow routing through K-Space/to Thera via ESI
  # NOTE: A SECURE database and a publicly available callback would need to be added for that to work though
  # Another positive of that feature is that it would allow for avoided systems to be used when finding routes
  if thera_jumps > gate_jumps:
    await interaction.response.send_message('The fastest route is by just gating through K-Space.')
  elif thera_jumps == gate_jumps:
    await interaction.response.send_message('The fastest route through K-Space is equal distance to the route through Thera.')
  else:
    src_sys = source_system.upper() if '-' in source_system else source_system.title()
    dest_sys = destination_system.upper() if '-' in destination_system else destination_system.title()
    embed = discord.Embed(title=f"From {src_sys} To {dest_sys} Is {thera_jumps} Jumps", color=0xffd700)
    embed.set_thumbnail(url='https://images.ctfassets.net/7lhcm73ukv5p/1rS96YuV4c29hjKlMM0YYa/873b64b4d5340d6f5ace1a3294c9d00a/ThumbClean.jpg?w=850&fm=jpg&fl=progressive&q=75')

    mass_type = 'Large (Freighter)' if system_type(closest_to_source) in freighter_wormholes else ('Large (Battleship)' if system_type(closest_to_source) in battleship_wormholes else 'Medium (Cruiser)')
    date_object = datetime.datetime.fromisoformat(str(closest_to_source['wormholeEstimatedEol']).replace('Z', '+00:00')).replace(tzinfo=pytz.UTC)
    time_difference = date_object - datetime.datetime.now(datetime.timezone.utc)
    hours_remaining = round(time_difference.total_seconds() / 3600)

    name = f"{str(closest_to_source['destinationSolarSystem']['name']).title()} ({round(closest_to_source['destinationSolarSystem']['security'], 2)}) - {closest_to_source['jumps']}J Away"
    value = f"Region: {closest_to_source['destinationSolarSystem']['region']['name']}\nSize: {mass_type}\nEst. Life: ~{hours_remaining} hours remain\nMass Status: {closest_to_source['wormholeMass']}\nOut Sig: {closest_to_source['signatureId']}\nIn Sig: {closest_to_source['wormholeDestinationSignatureId']}"
    embed.add_field(name=name, value=value, inline=True)

    mass_type = 'Large (Freighter)' if system_type(closest_to_dest) in freighter_wormholes else ('Large (Battleship)' if system_type(closest_to_dest) in battleship_wormholes else 'Medium (Cruiser)')
    date_object = datetime.datetime.fromisoformat(str(closest_to_dest['wormholeEstimatedEol']).replace('Z', '+00:00')).replace(tzinfo=pytz.UTC)
    time_difference = date_object - datetime.datetime.now(datetime.timezone.utc)
    hours_remaining = round(time_difference.total_seconds() / 3600)

    name = f"{str(closest_to_dest['destinationSolarSystem']['name']).title()} ({round(closest_to_dest['destinationSolarSystem']['security'], 2)}) - {closest_to_dest['jumps']}J Away"
    value = f"Region: {closest_to_dest['destinationSolarSystem']['region']['name']}\nSize: {mass_type}\nEst. Life: ~{hours_remaining} hours remain\nMass Status: {closest_to_dest['wormholeMass']}\nOut Sig: {closest_to_dest['signatureId']}\nIn Sig: {closest_to_dest['wormholeDestinationSignatureId']}"
    embed.add_field(name=name, value=value, inline=True)

    await interaction.response.send_message(embed=embed)
    return

@route.autocomplete('ship_size')
async def route_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
  options = ['frigate', 'destroyer', 'cruiser', 'battlecruiser', 'battleship', 'freighter', 'industrial', 'capital industrial (Orca)', 'capital']
  data = []
  for option in options:
    if current.lower() in option.lower():
      data.append(app_commands.Choice(name=option, value=option))
  return data

@client.tree.command()
async def pochven_map(interaction: discord.Interaction) -> None:
  """Displays the map of Pochven"""
  await interaction.response.send_message('https://pochven.electusmatari.com/images/image22.png')

@client.tree.command()
async def eve_time(interaction: discord.Interaction) -> None:
  """Displays the current EVE time"""
  utc_time = datetime.datetime.utcnow()
  time_24h = utc_time.strftime('%H:%M:%S')
  await interaction.response.send_message(f'The current EVE time is {time_24h}')

def run_bot() -> None:
  client.run(token=TOKEN, log_handler=handler)

if __name__ == '__main__':
  run_bot()