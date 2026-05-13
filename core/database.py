"""
KisanSathi AI - Supabase REST Client
Uses direct HTTP calls compatible with both legacy JWT and new sb_secret_/sb_publishable_ key formats.
No SDK-level key format validation.
"""
import httpx
from core.config import settings
from loguru import logger


class SupabaseRestClient:
    """Lightweight Supabase REST API client that supports all key formats."""

    def __init__(self, url: str, key: str):
        self.base_url = url.rstrip("/")
        self.key = key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _rest_url(self, table: str) -> str:
        return f"{self.base_url}/rest/v1/{table}"

    async def insert(self, table: str, data: dict) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(self._rest_url(table), json=data, headers=self.headers)
                r.raise_for_status()
                result = r.json()
                return result[0] if isinstance(result, list) else result
        except Exception as e:
            logger.warning(f"Supabase insert failed [{table}]: {e}")
            return None

    async def select(self, table: str, filters: dict | None = None) -> list:
        try:
            params = {}
            if filters:
                for k, v in filters.items():
                    params[k] = f"eq.{v}"
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(self._rest_url(table), params=params, headers=self.headers)
                r.raise_for_status()
                return r.json() if isinstance(r.json(), list) else []
        except Exception as e:
            logger.warning(f"Supabase select failed [{table}]: {e}")
            return []

    async def update(self, table: str, filters: dict, data: dict) -> dict | None:
        try:
            params = {k: f"eq.{v}" for k, v in filters.items()}
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.patch(self._rest_url(table), json=data, params=params, headers=self.headers)
                r.raise_for_status()
                result = r.json()
                return result[0] if isinstance(result, list) and result else result
        except Exception as e:
            logger.warning(f"Supabase update failed [{table}]: {e}")
            return None

    async def delete(self, table: str, filters: dict) -> bool:
        try:
            params = {k: f"eq.{v}" for k, v in filters.items()}
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.delete(self._rest_url(table), params=params, headers=self.headers)
                r.raise_for_status()
                return True
        except Exception as e:
            logger.warning(f"Supabase delete failed [{table}]: {e}")
            return False

    async def rpc(self, func_name: str, params: dict) -> dict | None:
        try:
            url = f"{self.base_url}/rest/v1/rpc/{func_name}"
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(url, json=params, headers=self.headers)
                r.raise_for_status()
                return r.json()
        except Exception as e:
            logger.warning(f"Supabase RPC failed [{func_name}]: {e}")
            return None

    async def ping(self) -> bool:
        """Test connection to Supabase."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base_url}/rest/v1/", headers=self.headers)
                return r.status_code < 500
        except Exception:
            return False


def get_supabase_client() -> SupabaseRestClient | None:
    """Create Supabase REST client. Supports sb_secret_, sb_publishable_, and legacy JWT keys."""
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY

    if not url or not key:
        logger.warning("Supabase credentials not set. Database operations will be skipped.")
        return None

    # Accept any key format — no validation
    logger.info(f"Supabase REST client initialized for: {url}")
    return SupabaseRestClient(url=url, key=key)


# Global client instance
supabase: SupabaseRestClient | None = get_supabase_client()
