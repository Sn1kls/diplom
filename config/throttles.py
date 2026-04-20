import logging

from ninja.throttling import AuthRateThrottle

logger = logging.getLogger(__name__)


class LoggingAuthRateThrottle(AuthRateThrottle):
    def allow_request(self, request):
        user_info = getattr(request.user, "id", "Anonymous")
        key = self.get_cache_key(request)

        logger.info("=" * 50)
        logger.info(f"[THROTTLE] Request from User ID: {user_info}, Path: {request.path}")
        logger.info(f"[THROTTLE] Generated Cache Key: {key}")

        current_self_key = getattr(self, "key", "EMPTY")
        current_self_history = getattr(self, "history", [])

        if current_self_key != "EMPTY" and current_self_key != key:
            logger.warning(
                f"[THROTTLE] DANGER: STATE LEAK DETECTED! Previous key '{current_self_key}' still in memory!"
            )
        else:
            logger.info(f"[THROTTLE] self.key BEFORE execution: {current_self_key}")

        logger.info(f"[THROTTLE] self.history size BEFORE execution: {len(current_self_history)}")

        result = super().allow_request(request)

        logger.info(f"[THROTTLE] self.key AFTER execution: {getattr(self, 'key', 'EMPTY')}")
        logger.info(f"[THROTTLE] self.history size AFTER execution: {len(getattr(self, 'history', []))}")
        logger.info(f"[THROTTLE] Request Allowed (True/False): {result}")
        logger.info("=" * 50)

        return result
