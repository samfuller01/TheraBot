import discord
import os
import requests
import logging
import datetime
import pytz
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

# load global and environment variables and set up logging
load_dotenv()
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
TOKEN = os.getenv('TOKEN')
GUILD_ID = os.getenv('GUILD_ID')
GUILD = discord.Object(id=GUILD_ID)
DEV_MODE = os.getenv('DEV_MODE')
API_URL = 'https://www.eve-scout.com/api/wormholes'

class TheraBotClient(discord.Client):
  def __init__(self, *, intents: discord.Intents) -> None:
    super().__init__(intents=intents)
    self.counter = 0
    self.wormholes = None
    self.tree = app_commands.CommandTree(self)
    self.synced = False

  async def on_ready(self) -> None:
    print(f'Logged on as {self.user}')
    print(''.center(10, '-'))
    await self.fetch_thera_api()

  async def setup_hook(self) -> None:
    if DEV_MODE == 'DEV': # if in development mode sync commands to the development server quickly
      self.tree.copy_global_to(guild=GUILD)
      await self.tree.sync(guild=GUILD)
      print('Started in DEV mode')
    else: # otherwise sync globally slowly
      await self.tree.sync()
      print('Started in PROD mode')

  @tasks.loop(minutes=10)
  async def fetch_thera_api(self) -> None:
    res = requests.get(url=API_URL)
    if res.status_code != 200:
      self.wormholes = None
    else:
      self.wormholes = res.json()
    self.counter += 1

    print(f'Retrieved Thera Data. Counter #{self.counter}')

  @fetch_thera_api.before_loop
  async def before_fetch_thera_api(self) -> None:
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
  
  # cruiser_wormholes = ['T458', 'Q063', 'F353']
  battleship_wormholes = ['V898', 'F135', 'M164']
  freighter_wormholes = ['E587', 'L031']
  
  embed = discord.Embed(title='Thera Connections', description='Current Thera wormholes', color=0xffd700)
  embed.set_thumbnail(url='https://images.ctfassets.net/7lhcm73ukv5p/1rS96YuV4c29hjKlMM0YYa/873b64b4d5340d6f5ace1a3294c9d00a/ThumbClean.jpg?w=850&fm=jpg&fl=progressive&q=75')
  for system in client.wormholes:
    system_type = system['destinationWormholeType'] if system['destinationWormholeType'] != 'K162' else system['sourceWormholeType']
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
  res = requests.get(API_URL + f'?systemSearch={system_name}')
  if res.status_code != 200:
    await interaction.response.send_message('Could not access Thera data :( Did you spell the system name correctly?')
    return
  
  wormholes = res.json()
  # filter out wormholes that say zero jumps from target system but are not the target system (API says zero jumps for W-Space systems)
  filtered_wormholes = [item for item in wormholes if not (item['jumps'] == 0 and str(item['destinationSolarSystem']['name']).lower() != system_name.lower())]
  # sort the remaining wormholes by how many jumps the connection is from target system
  sorted_wormholes = sorted(filtered_wormholes, key=lambda x: x['jumps'])
  # closest system is the first one in the system 
  # NOTE: I don't know what happens if two systems are equally far apart from target system, I'm guessing it semi-randomly picks one of the two(?)
  system = sorted_wormholes[0]

  battleship_wormholes = ['V898', 'F135', 'M164']
  freighter_wormholes = ['E587', 'L031']

  formatted_sys_name = str(system_name).title()
  embed = discord.Embed(title=f'Closest {formatted_sys_name} Connection', color=0xffd700)
  embed.set_thumbnail(url='https://images.ctfassets.net/7lhcm73ukv5p/1rS96YuV4c29hjKlMM0YYa/873b64b4d5340d6f5ace1a3294c9d00a/ThumbClean.jpg?w=850&fm=jpg&fl=progressive&q=75')
  system_type = system['destinationWormholeType'] if system['destinationWormholeType'] != 'K162' else system['sourceWormholeType']
  mass_type = 'Large (Freighter)' if system_type in freighter_wormholes else ('Large (Battleship)' if system_type in battleship_wormholes else 'Medium (Cruiser)')
  date_object = datetime.datetime.fromisoformat(str(system['wormholeEstimatedEol']).replace('Z', '+00:00')).replace(tzinfo=pytz.UTC)
  time_difference = date_object - datetime.datetime.now(datetime.timezone.utc)
  hours_remaining = round(time_difference.total_seconds() / 3600)
  name = f"{system['destinationSolarSystem']['name']} ({round(system['destinationSolarSystem']['security'], 2)}) {system['jumps']} Jumps"
  value = f"Region: {system['destinationSolarSystem']['region']['name']}\nSize: {mass_type}\nEst. Life: ~{hours_remaining} hours remain\nMass Status: {system['wormholeMass']}\nOut Sig: {system['signatureId']}\nIn Sig: {system['wormholeDestinationSignatureId']}"
  embed.add_field(name=name, value=value)

  await interaction.response.send_message(embed=embed)

# TODO: Add ability to select what size ship you are in and find fastest route that ship can take
@client.tree.command()
@app_commands.describe(
  source_system='The starting system',
  destination_system='The destination system'
)
async def route(interaction: discord.Interaction, source_system: str, destination_system: str) -> None:
  """Finds the shortest route between two systems and tells you the number of jumps and other relevant info"""
  source_res = requests.get(API_URL + f'?systemSearch={source_system}')
  if source_res.status_code != 200:
    await interaction.response.send_message('Could not access Thera data :( Did you spell the system name correctly?')
    return
  destination_res = requests.get(API_URL + f'?systemSearch={destination_system}')
  if destination_res.status_code != 200:
    await interaction.response.send_message('Could not access Thera data :( Did you spell the system name correctly?')
    return
  
  battleship_wormholes = ['V898', 'F135', 'M164']
  freighter_wormholes = ['E587', 'L031']

  source_wormholes = source_res.json()
  destination_wormholes = destination_res.json()
  filter_s_wormholes = [item for item in source_wormholes if not (item['jumps'] == 0 and str(item['destinationSolarSystem']['name']).lower() != source_system.lower())]
  filter_d_wormholes = [item for item in destination_wormholes if not (item['jumps'] == 0 and str(item['destinationSolarSystem']['name']).lower() != destination_system.lower())]
  sorted_s_wormholes = sorted(filter_s_wormholes, key=lambda x: x['jumps'])
  sorted_d_wormholes = sorted(filter_d_wormholes, key=lambda x: x['jumps'])
  wormholes = [sorted_s_wormholes[0], sorted_d_wormholes[0]]

  embed = discord.Embed(title=f"From {source_system.title()} To {destination_system.title()}", color=0xffd700)
  embed.set_thumbnail(url='https://images.ctfassets.net/7lhcm73ukv5p/1rS96YuV4c29hjKlMM0YYa/873b64b4d5340d6f5ace1a3294c9d00a/ThumbClean.jpg?w=850&fm=jpg&fl=progressive&q=75')

  system_type = wormholes[0]['destinationWormholeType'] if wormholes[0]['destinationWormholeType'] != 'K162' else wormholes[0]['sourceWormholeType']
  mass_type = 'Large (Freighter)' if system_type in freighter_wormholes else ('Large (Battleship)' if system_type in battleship_wormholes else 'Medium (Cruiser)')
  date_object = datetime.datetime.fromisoformat(str(wormholes[0]['wormholeEstimatedEol']).replace('Z', '+00:00')).replace(tzinfo=pytz.UTC)
  time_difference = date_object - datetime.datetime.now(datetime.timezone.utc)
  hours_remaining = round(time_difference.total_seconds() / 3600)
  name = f"{str(wormholes[0]['destinationSolarSystem']['name']).title()} ({round(wormholes[0]['destinationSolarSystem']['security'], 2)}) - {wormholes[0]['jumps']} Away"
  value = f"Region: {wormholes[0]['destinationSolarSystem']['region']['name']}\nSize: {mass_type}\nEst. Life: ~{hours_remaining} hours remain\nMass Status: {wormholes[0]['wormholeMass']}\nOut Sig: {wormholes[0]['signatureId']}\nIn Sig: {wormholes[0]['wormholeDestinationSignatureId']}"
  embed.add_field(name=name, value=value, inline=True)

  name = f"{str(wormholes[1]['destinationSolarSystem']['name']).title()} ({round(wormholes[1]['destinationSolarSystem']['security'], 2)}) - {wormholes[1]['jumps']} Away"
  value = f"Region: {wormholes[1]['destinationSolarSystem']['region']['name']}\nSize: {mass_type}\nEst. Life: ~{hours_remaining} hours remain\nMass Status: {wormholes[1]['wormholeMass']}\nOut Sig: {wormholes[1]['signatureId']}\nIn Sig: {wormholes[1]['wormholeDestinationSignatureId']}"
  embed.add_field(name=name, value=value, inline=True)

  embed.set_footer(text='This route may not be shorter than just gating through K-Space. It is your responsibility to check that!')

  await interaction.response.send_message(embed=embed)

def main() -> None:
  client.run(TOKEN, log_handler=handler)

if __name__ == '__main__':
  main()