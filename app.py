import argparse
import signal
import socket
import sys
from pathlib import Path

def main():
  parser = argparse.ArgumentParser(
      description="Server Availability Monitor — monitors TCP connectivity and sends email alerts"
  )
  parser.add_argument(
      "monitor_list",
      type=Path,
      nargs="?",
      default=Path("config") / "monitor_list.txt",
      help="Path to monitor_list.txt containing hostnames to monitor",
  )
  args = parser.parse_args()

  from monitor.config import ConfigError, ServerEntry, load_config
  from logger.setup import configure_logger

  try:
      config = load_config(args.monitor_list)
  except ConfigError as exc:
      print(f"Configuration error: {exc}", file=sys.stderr)
      sys.exit(1)

  configure_logger(config.log_dir)

  from monitor.loop import MonitorLoop

  loop = MonitorLoop(config)

  signal.signal(signal.SIGINT, lambda _s, _f: loop.stop())
  signal.signal(signal.SIGTERM, lambda _s, _f: loop.stop())

  loop.run()

  # for hostname in config.monitored_hostnames:
  #   server = config.servers[hostname]
  #   status = check_server(server)
    # if status:
    #   print(f"Servidor {server.hostname} ONLINE")
    # else:
    #   print(f"Servidor {server.hostname} OFFLINE")

if __name__ == "__main__":
  main()
