# Setup — enabling live data

The app runs out of the box against the offline `fixture` source. To pull
**live** data you need two things: network access to the data hosts, and an API
key. In a Claude Code **web session** both are configured on the *environment*,
not in code.

## 1. Network allowlist

Web sessions run behind an egress allowlist that blocks data hosts by default
(you'll see `403 policy denial` for these). In the environment's network policy,
allow the hosts you intend to use:

| Source | Host to allow | Needed for |
|--------|---------------|------------|
| EIA-930 (live demand) | `api.eia.gov` | the `eia930` source — **minimum** |
| PJM | `dataminer2.pjm.com` | future nodal source |
| CAISO | `oasis.caiso.com` | future nodal source |
| MISO | `api.misoenergy.org` | future nodal source |
| SPP | `marketplace.spp.org` | future nodal source |
| ERCOT | `www.ercot.com` | future nodal source |
| NYISO | `mis.nyiso.com` | future zonal source |
| ISO-NE | `webservices.iso-ne.com` | future nodal source |

For just the current EIA path, allowing **`api.eia.gov`** is enough.

> A running session does **not** pick up policy changes — start a **fresh
> session** on this repo/branch after editing the policy.

## 2. API key

Get a free EIA key: https://www.eia.gov/opendata/register.php

Provide it in **one** of these ways (the app reads either name):

- **Environment variable on the web environment** (recommended — survives
  session restarts, never in the transcript):
  `EIA_API_KEY=...`
- **Local `.env` file** (gitignored, single container only):
  ```
  EIA_API_KEY=your_key_here
  ```
  See `.env.example`.

## 3. Verify it's live

```bash
# 1. network open? (should NOT be 403/000)
curl -s -o /dev/null -w "%{http_code}\n" https://api.eia.gov/v2/

# 2. install + run
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
energy-tracker --source eia930 --regions PJM,ERCO,CISO

# 3. or via the API
uvicorn energy_tracker.api:app --port 8000 &
curl "localhost:8000/demand?source=eia930&regions=PJM&latest=true"
```

## Security note

Never commit the key. `.env` is gitignored. If a key is ever pasted into a chat
or a commit, rotate it (re-register at the EIA link above).
