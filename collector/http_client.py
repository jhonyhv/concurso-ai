from __future__ import annotations

import time
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0.0.0 Safari/537.36 ConcursoAI/1.0"
)


class HttpClient:
    def __init__(self, delay_seconds: float = 0.8, timeout: int = 45) -> None:
        self.delay_seconds = delay_seconds
        self.timeout = timeout
        self._last_request = 0.0
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
                "Cache-Control": "no-cache",
            }
        )

    def get(self, url: str) -> requests.Response:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
        self._last_request = time.monotonic()
        response.raise_for_status()
        return response

    @staticmethod
    def domain_allowed(url: str, allowed_domains: tuple[str, ...]) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return any(host == domain or host.endswith("." + domain) for domain in allowed_domains)
