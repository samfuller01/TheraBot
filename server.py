import requests
import os
import base64
from dotenv import load_dotenv
from flask import Flask, request

app = Flask(__name__)

load_dotenv()
ESI_CLIENT_ID = os.getenv('ESI_CLIENT_ID')
ESI_SECRET = os.getenv('ESI_SECRET_KEY')
ESI_URL = 'https://login.eveonline.com/v2/oauth/token'

credentials = f'{ESI_CLIENT_ID}:{ESI_SECRET}'
encoded_credentials = base64.b64encode(credentials.encode(encoding='utf-8')).decode(encoding='utf-8')

@app.route('/callback', methods=['GET'])
def callback():
  query_params = request.args.to_dict()
  if not query_params:
    return '<p>No query params provided</p>'
  
  access_code = query_params.get('code')
  headers = {
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Host': 'login.eveonline.com'
  }
  payload = {
    'grant_type': 'authorization_code',
    'code': access_code
  }
  res = requests.post(url=ESI_URL, headers=headers, data=payload)

  if res.status_code != 200:
    return f'<p>Error getting data from EVE SSO</p><br><p>{res}</p>'
  
  json = res.json()
  access_token = json.get('access_token')
  refresh_token = json.get('refresh_token')
  
  return f'<p>Access Token: {access_token} Refresh Token: {refresh_token}</p>', 200 