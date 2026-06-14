# Server Monitor

Monitors TCP connectivity of servers and sends email alerts when a server goes offline or recovers.

## How it works

The monitor probes each server in the list via TCP socket at a configurable interval. When a state transition is detected (online → offline or offline → online), an email is sent to all configured recipients.

```
UNKNOWN → ONLINE   — first successful probe, no alert
ONLINE  → OFFLINE  — sends offline alert
OFFLINE → OFFLINE  — repeats alert every notification_interval seconds
OFFLINE → ONLINE   — sends recovery notice
```

## Project structure

```
.
├── app.py                        # Entry point
├── config/
│   ├── monitor_config.json       # SMTP host, intervals, timeouts
│   ├── monitor_list.txt          # Hostnames to monitor (one per line)
│   ├── servers_pool.json         # Available servers (hostname, ip, port)
│   └── users_info.json           # Alert recipients
├── monitor/
│   ├── checker.py                # TCP connectivity check
│   ├── config.py                 # Config loading and validation
│   ├── loop.py                   # Monitor loop and state transitions
│   ├── notifier.py               # Email alerts (offline + recovery)
│   └── state.py                  # Server state tracking
├── logger/
│   └── setup.py                  # Logging configuration
└── logs/
    └── server_monitor.log
```

## Setup

**1. Install dependencies**
```bash
pip install python-dotenv
```

**2. Configure credentials**
```bash
cp .env.example .env
# Edit .env with your SMTP credentials
```

**3. Configure servers**

Add servers to `config/servers_pool.json`:
```json
[
  {"hostname": "my-server", "ip": "192.168.1.10", "port": 80}
]
```

Add hostnames to monitor in `config/monitor_list.txt`:
```
my-server
```

Add recipients to `config/users_info.json`:
```json
[
  {"username": "Admin", "email": "admin@example.com"}
]
```

**4. Run**
```bash
python app.py
# or with a custom monitor list:
python app.py /path/to/monitor_list.txt
```

## Configuration

`config/monitor_config.json`:

| Field | Description | Default |
|-------|-------------|---------|
| `smtp.host` | SMTP server host | — |
| `smtp.port` | SMTP port | — |
| `smtp.use_tls` | Use SSL/TLS | — |
| `smtp.use_starttls` | Use STARTTLS | — |
| `smtp.timeout` | SMTP connection timeout (s) | `10` |
| `check_interval` | Seconds between probes | `60` |
| `notification_interval` | Minimum seconds between repeated offline alerts | `300` |
| `socket_timeout` | TCP connection timeout (s) | `5` |
| `log_dir` | Log file directory | `../logs` |

## Environment variables

Credentials are read from `.env` (never committed to git):

| Variable | Description |
|----------|-------------|
| `SMTP_USERNAME` | SMTP login username |
| `SMTP_PASSWORD` | SMTP password or app password |
| `SMTP_SENDER` | From address for alert emails |

## Testing offline/recovery behavior

Start a local TCP server and point the monitor at it:

1. Add to `config/servers_pool.json`:
   ```json
   {"hostname": "local-test", "ip": "127.0.0.1", "port": 9999}
   ```
2. Add `local-test` to `config/monitor_list.txt`
3. Start the local server: `python -m http.server 9999`
4. Start the monitor: `python app.py`
5. Stop the local server → observe `WENT OFFLINE` in the log
6. Restart the local server → observe `RECOVERY` in the log

## Stopping

Send `SIGINT` (Ctrl+C) or `SIGTERM` — the monitor shuts down cleanly.
