import hashlib
import typing
import uuid

import jwt
from django.core.cache import cache
from loguru import logger
from user_agents import parse

from apps.users.models import UserDeviceLog
from config import settings

if typing.TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse
    from user_agents.parsers import UserAgent


REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_PREFIX_LOG_ONLY = "/api/"


class RequestIDMiddleware:
    def __init__(self, get_response: typing.Callable[["HttpRequest"], "HttpResponse"]):
        self.get_response = get_response

    def __call__(self, request: "HttpRequest") -> "HttpResponse":
        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))

        with logger.contextualize(request_id=request_id):
            response = self.get_response(request)

            if REQUEST_ID_HEADER not in response:
                response[REQUEST_ID_HEADER] = request_id

            return response


class DeviceLogMiddleware:
    def __init__(self, get_response: typing.Callable[["HttpRequest"], "HttpResponse"]):
        self.get_response = get_response

    def __call__(self, request: "HttpRequest") -> "HttpResponse":
        self._logging_device_info(request)
        return self.get_response(request)

    def _logging_device_info(self, request):
        if not request.path.startswith(REQUEST_PREFIX_LOG_ONLY):
            return

        if not (user_agent_http := request.META.get("HTTP_USER_AGENT", "")):
            return

        user_id = self.__get_user_from_jwt_token(request)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip_address = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else request.META.get("REMOTE_ADDR")

        cache_key = self.__get_cache_key(
            user_agent_http=user_agent_http,
            ip_address=ip_address,
            user_id=user_id if user_id else "anonymous",
        )

        if cache.get(cache_key):
            return

        user_agent_parsed: "UserAgent" = parse(user_agent_http)
        UserDeviceLog.objects.create(
            user_fk_id=user_id,
            ip_address=ip_address,
            os_name=f"{user_agent_parsed.os.family} {user_agent_parsed.os.version_string}",
            browser=f"{user_agent_parsed.browser.family} {user_agent_parsed.browser.version_string}",
            device_type=self.__get_device(user_agent_parsed),
            raw_user_agent=user_agent_http,
        )
        cache.set(cache_key, True, timeout=86400)

    def __get_user_from_jwt_token(self, request: "HttpRequest") -> typing.Optional[int]:
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header and auth_header.startswith("Bearer"):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=["HS256"],
                )
                return payload.get("user_id")
            except Exception as e:
                logger.error(f"{self.__class__.__name__}._logging_device_info: {e}")
                pass
        return None

    @staticmethod
    def __get_device(user_agent: "UserAgent") -> str:
        if user_agent.is_mobile:
            return "mobile"
        elif user_agent.is_tablet:
            return "tablet"
        elif user_agent.is_pc:
            return "pc"
        elif user_agent.is_bot:
            return "bot/crawler"
        return "unknown"

    @staticmethod
    def __get_cache_key(*, user_agent_http: str, ip_address: str, user_id: typing.Optional[int] = None) -> str:
        ua_hash = hashlib.md5(user_agent_http.encode("utf-8")).hexdigest()
        return f"device_logged_{user_id}_{ip_address}_{ua_hash}"
