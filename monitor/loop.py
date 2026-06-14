import logging
import threading
import time

from monitor import checker, notifier
from monitor.config import AppConfig
from monitor.notifier import NotificationError
from monitor.state import ServerState, ServerStatus, StateManager

logger = logging.getLogger(__name__)

class MonitorLoop:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._stop_event = threading.Event()
        self._state_manager = StateManager(config.monitored_hostnames)

    def stop(self) -> None:
        logger.info("Shutdown requested — stopping monitor loop")
        self._stop_event.set()

    def run(self) -> None:
        cfg = self._config
        logger.info(
            "Monitor started | servers=%s | check_interval=%ds | notification_interval=%ds",
            cfg.monitored_hostnames,
            cfg.check_interval,
            cfg.notification_interval,
        )
        try:
            while not self._stop_event.is_set():
                self._probe_round()
                self._stop_event.wait(timeout=cfg.check_interval)
        except Exception as exc:
            logger.error("Unhandled exception in monitor loop: %s", exc, exc_info=True)
            raise SystemExit(2) from exc
        logger.info("Monitor stopped")
    
    def _probe_round(self) -> None:
        cfg = self._config
        now_mono = time.monotonic()
        now_wall = time.time()

        logger.info("-- NEW PROBE START --")

        for hostname in cfg.monitored_hostnames:
            server = cfg.servers[hostname]
            state = self._state_manager.get(hostname)
            is_up = checker.check_server(server, timeout=cfg.socket_timeout)
            # if is_up:
            #   print(f"Servidor {hostname} ONLINE")
            # else:
            #   print(f"Servidor {hostname} OFFLINE")
            self._process_transition(state, server, is_up, now_mono, now_wall)

    def _process_transition(
        self,
        state: ServerState,
        server,
        is_up: bool,
        now_mono: float,
        now_wall: float,
    ) -> None:
        cfg = self._config
        prev_status = state.status
        new_status = ServerStatus.ONLINE if is_up else ServerStatus.OFFLINE

        if new_status == ServerStatus.ONLINE and prev_status == ServerStatus.OFFLINE:
            # Case OFFLINE-TO-ONLINE
            state.status = ServerStatus.ONLINE
            state.last_changed = now_mono
            state.consecutive_failures = 0
            state.offline_since = None
            still_offline = self._state_manager.all_offline()
            logger.info(
                "RECOVERY %s | still_offline=%s", server.hostname, still_offline
            )
            self._notify(
                notifier.send_recovery_notice,
                server,
                still_offline,
                cfg,
            )

        elif new_status == ServerStatus.OFFLINE and prev_status == ServerStatus.UNKNOWN:
            # Case UNKNOWN-TO-OFFLINE
            state.status = ServerStatus.OFFLINE
            state.last_changed = now_mono
            state.offline_since = now_wall
            state.consecutive_failures = 1
            state.last_notified = now_mono
            logger.warning("IS OFFLINE %s (%s:%d)", server.hostname, server.ip, server.port)
            self._notify(notifier.send_offline_alert, server, state, cfg)

        elif new_status == ServerStatus.OFFLINE and prev_status == ServerStatus.ONLINE:
            # Case ONLINE-TO-OFFLINE
            state.status = ServerStatus.OFFLINE
            state.last_changed = now_mono
            state.offline_since = now_wall
            state.consecutive_failures = 1
            state.last_notified = now_mono
            logger.warning("WENT OFFLINE %s (%s:%d)", server.hostname, server.ip, server.port)
            self._notify(notifier.send_offline_alert, server, state, cfg)

        elif new_status == ServerStatus.OFFLINE and prev_status == ServerStatus.OFFLINE:
            # Case OFFLINE-TO-OFFLINE
            state.consecutive_failures += 1
            elapsed = now_mono - state.last_notified
            state.last_notified = now_mono
            logger.warning(
                "STILL OFFLINE %s (failures=%d)",
                server.hostname,
                state.consecutive_failures,
            )
            self._notify(notifier.send_offline_alert, server, state, cfg)
            # if elapsed >= cfg.notification_interval:
            #     state.last_notified = now_mono
            #     logger.warning(
            #         "STILL OFFLINE %s (failures=%d)",
            #         server.hostname,
            #         state.consecutive_failures,
            #     )
            #     self._notify(notifier.send_offline_alert, server, state, cfg)

        else:
            # Case ONLINE-TO-ONLINE or UNKNOWN-TO-ONLINE (first successful probe).
            if prev_status != ServerStatus.ONLINE:
                state.status = ServerStatus.ONLINE
                state.last_changed = now_mono
                logger.info("INITIAL PROBE OK %s", server.hostname)
            else:
                logger.debug("OK %s", server.hostname)

    @staticmethod
    def _notify(fn, *args, **kwargs) -> None:
        try:
            fn(*args, **kwargs)
        except NotificationError as exc:
            logger.error("Notification failed: %s", exc)
