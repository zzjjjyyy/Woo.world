# -*- coding: utf-8 -*-
import json, subprocess, time, os
from datetime import datetime, timezone, timedelta
BASE=r'D:\DeepSeek Harness\artifacts'
LOG=os.path.join(BASE,'github_watch_old.log')
TOKEN=os.path.join(BASE,'github_token.txt')
client='Iv1.b507a08c87ecfe98'
device='aaaea7a636fd37be2978169986a4926a978f7da8'
exp=datetime.now(timezone.utc)+timedelta(seconds=420)
with open(LOG,'a',encoding='utf-8') as f: f.write(time.strftime('%H:%M:%S ')+'old-code watcher start\n')
interval=5
while datetime.now(timezone.utc)<exp:
    time.sleep(interval)
    try:
        cp=subprocess.run(['curl.exe','--ssl-no-revoke','-sS','-L','--max-time','25','-X','POST','-H','Accept: application/json','-H','User-Agent: dsh-github-upload','-d',f'client_id={client}&device_code={device}&grant_type=urn:ietf:params:oauth:grant-type:device_code','https://github.com/login/oauth/access_token'],capture_output=True,text=True,encoding='utf-8',errors='replace')
        raw=(cp.stdout or '').strip(); d=json.loads(raw) if raw.startswith('{') else {}
    except Exception as e:
        with open(LOG,'a',encoding='utf-8') as f: f.write(time.strftime('%H:%M:%S ')+'err '+repr(e)+'\n')
        continue
    if d.get('access_token'):
        open(TOKEN,'w',encoding='utf-8').write(d['access_token'])
        with open(LOG,'a',encoding='utf-8') as f: f.write(time.strftime('%H:%M:%S ')+'old code authorized\n')
        break
    if d.get('error')=='slow_down': interval=min(20,interval+5)
    if d.get('error') not in ('authorization_pending','slow_down'):
        with open(LOG,'a',encoding='utf-8') as f: f.write(time.strftime('%H:%M:%S ')+'stopped '+str(d.get('error'))+'\n')
        break
with open(LOG,'a',encoding='utf-8') as f: f.write(time.strftime('%H:%M:%S ')+'old watcher exit\n')