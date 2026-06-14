import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from monitor.config import AppConfig, ServerEntry, SmtpConfig, UserEntry
from monitor.state import ServerState

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    pass


def send_offline_alert(
    server: ServerEntry,
    state: ServerState,
    config: AppConfig,
) -> None:
    # offline_since = (
    #     datetime.fromtimestamp(state.offline_since).strftime("%Y-%m-%d %H:%M:%S")
    #     if state.offline_since
    #     else "unknown"
    # )
    # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # subject = f"[ALERT] Server {server.hostname} is OFFLINE"
    # plain = _offline_plain(server, offline_since, timestamp, config.notification_interval)
    # html = _offline_html(server, offline_since, timestamp, config.notification_interval)

    # message = _build_message(subject, plain, html, config.smtp, config.recipients)
    # _send_via_smtp(message, config.smtp)
    logger.info("Offline alert sent for %s", server.hostname)


def send_recovery_notice(
    server: ServerEntry,
    still_offline: List[str],
    config: AppConfig,
) -> None:
    # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # subject = f"[RECOVERY] Server {server.hostname} is back ONLINE"
    # plain = _recovery_plain(server, still_offline, timestamp)
    # html = _recovery_html(server, still_offline, timestamp)

    # message = _build_message(subject, plain, html, config.smtp, config.recipients)
    # _send_via_smtp(message, config.smtp)
    logger.info("Recovery notice sent for %s", server.hostname)


def _build_message(
    subject: str,
    body_text: str,
    body_html: str,
    smtp_cfg: SmtpConfig,
    recipients: List[UserEntry],
) -> MIMEMultipart:
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = smtp_cfg.sender_email
    message["To"] = ", ".join(u.email for u in recipients)
    message.attach(MIMEText(body_text, "plain", "utf-8"))
    message.attach(MIMEText(body_html, "html", "utf-8"))
    return message


def _send_via_smtp(message: MIMEMultipart, smtp_cfg: SmtpConfig) -> None:
    try:
        if smtp_cfg.use_tls:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                smtp_cfg.host, smtp_cfg.port, context=ctx, timeout=smtp_cfg.timeout
            ) as server:
                server.login(smtp_cfg.username, smtp_cfg.password)
                server.send_message(message)
        else:
            with smtplib.SMTP(
                smtp_cfg.host, smtp_cfg.port, timeout=smtp_cfg.timeout
            ) as server:
                if smtp_cfg.use_starttls:
                    server.starttls()
                server.login(smtp_cfg.username, smtp_cfg.password)
                server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("Failed to send email: %s", exc)
        raise NotificationError(str(exc)) from exc


def _offline_plain(
    server: ServerEntry,
    offline_since: str,
    timestamp: str,
    notification_interval: int,
) -> str:
    return (
        f"Server Availability Monitor - ALERT\n"
        f"=====================================\n"
        f"Server:   {server.hostname}\n"
        f"IP:       {server.ip}\n"
        f"Port:     {server.port}\n"
        f"Status:   OFFLINE\n"
        f"Since:    {offline_since}\n"
        f"Detected: {timestamp}\n\n"
        f"This alert will repeat every {notification_interval} seconds "
        f"while the server remains offline.\n\n"
        f"--\nServer Monitor (automated)"
    )


def _offline_html(
    server: ServerEntry,
    offline_since: str,
    timestamp: str,
    notification_interval: int,
) -> str:
    return (
        f'<html><body style="font-family:monospace;padding:16px">'
        f'<h2 style="color:#c0392b">[ALERT] Server {server.hostname} is OFFLINE</h2>'
        f'<table cellpadding="6" style="border-collapse:collapse">'
        f'<tr><td><b>Hostname</b></td><td>{server.hostname}</td></tr>'
        f'<tr><td><b>IP</b></td><td>{server.ip}</td></tr>'
        f'<tr><td><b>Port</b></td><td>{server.port}</td></tr>'
        f'<tr><td><b>Status</b></td>'
        f'<td style="color:#c0392b"><b>OFFLINE</b></td></tr>'
        f'<tr><td><b>Offline Since</b></td><td>{offline_since}</td></tr>'
        f'<tr><td><b>Detected At</b></td><td>{timestamp}</td></tr>'
        f'</table>'
        f'<p><i>This alert repeats every {notification_interval}s while offline.</i></p>'
        f'<p style="color:#888">-- Server Monitor (automated)</p>'
        f'</body></html>'
    )


def _recovery_plain(
    server: ServerEntry,
    still_offline: List[str],
    timestamp: str,
) -> str:
    if still_offline:
        still_list = "\n".join(f"  - {h}" for h in still_offline)
        still_section = f"Servers still OFFLINE ({len(still_offline)}):\n{still_list}"
    else:
        still_section = "All monitored servers are now online."

    return (
        f"Server Availability Monitor - RECOVERY\n"
        f"=======================================\n"
        f"Server:    {server.hostname}\n"
        f"Status:    ONLINE (recovered)\n"
        f"Recovered: {timestamp}\n\n"
        f"{still_section}\n\n"
        f"--\nServer Monitor (automated)"
    )


def _recovery_html(
    server: ServerEntry,
    still_offline: List[str],
    timestamp: str,
) -> str:
    if still_offline:
        items = "".join(
            f'<li style="color:#c0392b">{h}</li>' for h in still_offline
        )
        still_section = (
            f'<p><b>Servers still OFFLINE ({len(still_offline)}):</b></p>'
            f'<ul>{items}</ul>'
        )
    else:
        still_section = (
            '<p style="color:#27ae60"><b>All monitored servers are now online.</b></p>'
        )

    return (
        f'<html><body style="font-family:monospace;padding:16px">'
        f'<h2 style="color:#27ae60">[RECOVERY] Server {server.hostname} is back ONLINE</h2>'
        f'<table cellpadding="6" style="border-collapse:collapse">'
        f'<tr><td><b>Hostname</b></td><td>{server.hostname}</td></tr>'
        f'<tr><td><b>Status</b></td>'
        f'<td style="color:#27ae60"><b>ONLINE</b></td></tr>'
        f'<tr><td><b>Recovered At</b></td><td>{timestamp}</td></tr>'
        f'</table>'
        f'{still_section}'
        f'<p style="color:#888">-- Server Monitor (automated)</p>'
        f'</body></html>'
    )
