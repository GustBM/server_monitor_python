import logging
import socket
import time

from monitor.config import ServerEntry

logger = logging.getLogger(__name__)

def check_server(server: ServerEntry, timeout: int = 5) -> bool:
  try:
    with socket.create_connection((server.ip, server.port), timeout):
      return True
  except OSError:
    return False
