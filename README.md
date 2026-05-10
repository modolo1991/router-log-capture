# Router Log Capture

Captures logs from your home or office router, stores them in a database, and lets you browse and search them in a web UI. Useful for diagnosing intermittent WAN outages.

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Python 3.10+ (only needed for the one-time setup wizard)

## Quick start

**1. Run the setup wizard**

```
python setup.py
```

Answer the prompts — it will ask what type of router you have, your login credentials, and your timezone. It saves everything to a `.env` file.

**2. Start the app**

```
docker compose up -d
```

**3. Open the web UI**

Go to `http://localhost:8080` in your browser (or whichever port you chose during setup).

That's it. The app runs in the background and polls your router for new logs on the interval you configured.

---

## Supported routers

| Router type | How it works |
|---|---|
| **Sagemcom** (e.g. Optus FAST5366LTE-A) | Logs in via the router's JSON-RPC API and downloads the log file |
| **Syslog** (e.g. D-Link, most routers) | Listens for logs that the router pushes over the network — you need to point the router's syslog setting at this machine's IP |
| **HTTP scraper** | Logs in to the router's web admin page and scrapes the log table |

---

## Stopping and starting

```bash
docker compose stop      # pause without deleting data
docker compose start     # resume
docker compose down      # stop and remove containers (data is kept in a volume)
```

## Changing settings

Run `python setup.py` again to regenerate `.env`, then restart:

```bash
docker compose up -d --force-recreate
```

## Viewing logs (troubleshooting the app itself)

```bash
docker compose logs -f
```

---

## Syslog router setup

If you chose the **Syslog** collector, you need to tell your router where to send logs:

1. Log in to your router's admin page
2. Find the **Syslog** or **Remote Logging** setting (usually under System / Maintenance / Logs)
3. Set the server address to the IP of the machine running this app
4. Set the port to `514` (or whatever you entered during setup)
5. Save and apply

Logs will start appearing in the UI within seconds of the router sending them.

---

## Deploying on a second machine (e.g. at work)

You can run this on any machine that has Docker installed — a work PC, a laptop, or a home server.

**Steps:**

1. Copy or clone this repository to the new machine
2. Run `python setup.py` and answer the prompts for that location's router
3. Run `docker compose up -d`

If you're using Git, clone the repo and only create a fresh `.env` (it is not committed — `.gitignore` excludes it to keep your credentials private).

For a **syslog router at work** (e.g. D-Link), make sure:
- The machine running Docker is on the same network as the router
- The D-Link router's syslog setting points to that machine's IP and port 514
- Nothing is blocking UDP port 514 on the machine. On Windows, add a firewall rule:
  ```powershell
  New-NetFirewallRule -DisplayName "Syslog UDP 514" -Direction Inbound -Protocol UDP -LocalPort 514 -Action Allow
  ```

---

## AI assistant integration (MCP)

The app includes an MCP (Model Context Protocol) server that lets AI coding assistants — Claude Code, Codex, Cursor, Continue.dev — query your router logs directly. When you run `python setup.py`, it detects which AI tools you have installed and configures them automatically.

Once set up, you can ask your AI assistant things like:
- "Is my router reachable right now?"
- "Were there any errors in the last hour?"
- "Why did my internet drop this morning?"

The MCP server runs on port 8081 alongside the main app and is only accessible from your local machine (not exposed to other devices on your network).

> **Note:** The MCP server only works while Docker is running. Start it with `docker compose up -d`.

If you install a new AI tool after initial setup, just run `python setup.py` again — it will configure the new client without affecting your existing `.env`.

---

## Notes on timestamps

Router logs record timestamps in the router's local time. The app needs to know your timezone to display them correctly. The setup wizard sets this automatically, and it is stored as `TZ=` in your `.env` file. If your timestamps look wrong (e.g. 10 hours off), check that `TZ` in `.env` matches your local timezone.
