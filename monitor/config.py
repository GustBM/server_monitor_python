import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


class ConfigError(ValueError):
    pass


@dataclass
class SmtpConfig:
    host: str
    port: int
    use_tls: bool
    use_starttls: bool
    username: str
    password: str
    sender_email: str
    timeout: int = 10


@dataclass
class ServerEntry:
    hostname: str
    ip: str
    port: int


@dataclass
class UserEntry:
    username: str
    email: str


@dataclass
class AppConfig:
    smtp: SmtpConfig
    recipients: List[UserEntry]
    servers: Dict[str, ServerEntry]
    monitored_hostnames: List[str]
    check_interval: int
    notification_interval: int
    socket_timeout: int
    log_dir: Path


def _load_json(path: Path) -> object:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc


def _parse_smtp(data: dict) -> SmtpConfig:
    required = ("host", "port", "use_tls", "use_starttls", "username", "password", "sender_email")
    missing = [k for k in required if k not in data]
    if missing:
        raise ConfigError(f"smtp config missing keys: {missing}")
    return SmtpConfig(
        host=data["host"],
        port=int(data["port"]),
        use_tls=bool(data["use_tls"]),
        use_starttls=bool(data["use_starttls"]),
        username=data["username"],
        password=data["password"],
        sender_email=data["sender_email"],
        timeout=int(data.get("timeout", 10)),
    )


def _parse_users(data: list) -> List[UserEntry]:
    users = []
    for i, entry in enumerate(data):
        if "username" not in entry or "email" not in entry:
            raise ConfigError(f"users_info.json entry {i} missing 'username' or 'email'")
        users.append(UserEntry(username=entry["username"], email=entry["email"]))
    if not users:
        raise ConfigError("users_info.json must contain at least one recipient")
    return users


def _parse_servers(data: list) -> Dict[str, ServerEntry]:
    servers: Dict[str, ServerEntry] = {}
    for i, entry in enumerate(data):
        if "hostname" not in entry or "ip" not in entry or "port" not in entry:
            raise ConfigError(f"servers_pool.json entry {i} missing 'hostname', 'ip', or 'port'")
        hostname = entry["hostname"]
        if hostname in servers:
            raise ConfigError(f"servers_pool.json has duplicate hostname: {hostname}")
        servers[hostname] = ServerEntry(
            hostname=hostname,
            ip=entry["ip"],
            port=int(entry["port"]),
        )
    return servers


def _parse_monitor_list(path: Path) -> List[str]:
    if not path.exists():
        raise ConfigError(f"monitor_list file not found: {path}")
    hostnames = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                hostnames.append(stripped)
    if not hostnames:
        raise ConfigError(f"No hostnames found in {path}")
    return hostnames


def load_config(monitor_list_path: Path) -> AppConfig:
    monitor_list_path = monitor_list_path.resolve()
    config_dir = monitor_list_path.parent

    raw = _load_json(config_dir / "monitor_config.json")
    smtp = _parse_smtp(raw.get("smtp", {}))

    check_interval = int(raw.get("check_interval", 60))
    notification_interval = int(raw.get("notification_interval", 300))
    socket_timeout = int(raw.get("socket_timeout", 5))

    log_dir_raw = raw.get("log_dir", "../logs")
    log_dir = (config_dir / log_dir_raw).resolve()

    recipients = _parse_users(_load_json(config_dir / "users_info.json"))
    servers = _parse_servers(_load_json(config_dir / "servers_pool.json"))
    monitored_hostnames = _parse_monitor_list(monitor_list_path)

    missing = [h for h in monitored_hostnames if h not in servers]
    if missing:
        raise ConfigError(
            f"Hostnames in monitor_list not found in servers_pool: {missing}"
        )

    return AppConfig(
        smtp=smtp,
        recipients=recipients,
        servers=servers,
        monitored_hostnames=monitored_hostnames,
        check_interval=check_interval,
        notification_interval=notification_interval,
        socket_timeout=socket_timeout,
        log_dir=log_dir,
    )
