const clientId = 'Iv1.b507a08c87ecfe98';
const body = new URLSearchParams({ client_id: clientId, scope: 'public_repo' });
fetch('https://github.com/login/device/code', {
  method: 'POST',
  headers: {
    'Accept': 'application/json',
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'dsh-github-upload',
  },
  body: body.toString(),
}).then(async (r) => {
  const t = await r.text();
  console.log('STATUS', r.status, 'LEN', t.length);
  if (r.ok) {
    const data = JSON.parse(t);
    console.log(JSON.stringify({
      user_code: data.user_code,
      verification_uri: data.verification_uri,
      expires_in: data.expires_in,
      interval: data.interval,
      device_code_len: data.device_code ? data.device_code.length : 0,
    }));
    if (data.device_code) {
      require('fs').writeFileSync('D:\\DeepSeek Harness\\artifacts\\node_device_code.txt', data.device_code);
    }
  } else {
    console.log(t.slice(0, 500));
  }
}).catch((e) => console.log('ERR', e.name, e.message));
