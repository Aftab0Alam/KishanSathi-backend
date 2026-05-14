"""
KisanSathi — Mandi Price Routes
Fetches real-time crop market prices from India's official
data.gov.in AGMARKNET API (resource: 9ef84268-d588-465a-a308-a864a43d0070).
If the primary API is unavailable, an alternate source may be configured
with DATA_GOV_IN_ALT_BASE / DATA_GOV_IN_ALT_KEY. Otherwise returns
curated sample data so the app continues to work.
"""

from fastapi import APIRouter, Query
import httpx
import time
import os
from loguru import logger

router = APIRouter(prefix="/api/mandi", tags=["mandi"])

DATA_GOV_IN_BASE = "https://api.data.gov.in/resource/35985678-0d79-46b4-9ed6-6f13308a1d24"
# API key — set DATA_GOV_IN_KEY env var in Railway to override
DATA_GOV_IN_KEY  = os.getenv(
    "DATA_GOV_IN_KEY",
    "579b464db66ec23bdd000001ca2bda2bc65b4c01721c23d6173ae944"
)
ALTERNATE_DATA_GOV_IN_BASE = os.getenv("DATA_GOV_IN_ALT_BASE", "").strip()
ALTERNATE_DATA_GOV_IN_KEY  = os.getenv("DATA_GOV_IN_ALT_KEY", DATA_GOV_IN_KEY)

# Short timeouts so Railway gateway (≈15 s) never kills us first
# If external API is slow/blocked we fall back to a second provider or sample data
_TIMEOUT = httpx.Timeout(connect=5.0, read=8.0, write=5.0, pool=5.0)


async def _fetch_mandi_source(base_url: str, params: dict, label: str):
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(base_url, params=params)

    if resp.status_code != 200:
        raise ValueError(f"{label} returned HTTP {resp.status_code}")

    raw = resp.json()
    records = raw.get("records", [])
    total = raw.get("total", len(records))

    if not records:
        raise ValueError(f"{label} returned 0 records")

    cleaned = []
    for r in records:
        try:
            cleaned.append({
                "state":       r.get("state", ""),
                "district":    r.get("district", ""),
                "market":      r.get("market", ""),
                "commodity":   r.get("commodity", ""),
                "variety":     r.get("variety", ""),
                "min_price":   float(r.get("min_price", 0) or 0),
                "max_price":   float(r.get("max_price", 0) or 0),
                "modal_price": float(r.get("modal_price", 0) or 0),
                "date":        r.get("arrival_date", r.get("date", "")),
            })
        except Exception:
            pass

    if not cleaned:
        raise ValueError(f"{label} returned only invalid records")

    return {
        "total":   total,
        "fetched": len(cleaned),
        "records": cleaned,
        "source":  label,
        "cached":  False,
    }

_cache: dict = {}
CACHE_TTL = 1800  # 30 minutes


def _cache_key(**kwargs) -> str:
    return "|".join(f"{k}={v}" for k, v in sorted(kwargs.items()))


def _cached(key: str):
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
    return None


def _store(key: str, data):
    _cache[key] = (time.time(), data)


# ── Rich fallback data (used when AGMARKNET is unreachable) ───────────────────
FALLBACK_RECORDS = [
    {"state":"Punjab","district":"Ludhiana","market":"Ludhiana","commodity":"Wheat","variety":"Dara","min_price":2150,"max_price":2400,"modal_price":2275,"date":"14/05/2025"},
    {"state":"Punjab","district":"Ludhiana","market":"Ludhiana","commodity":"Paddy","variety":"1121 (Basmati)","min_price":1900,"max_price":2050,"modal_price":1960,"date":"14/05/2025"},
    {"state":"Punjab","district":"Amritsar","market":"Amritsar","commodity":"Maize","variety":"Yellow","min_price":2000,"max_price":2200,"modal_price":2100,"date":"14/05/2025"},
    {"state":"Punjab","district":"Bathinda","market":"Bathinda","commodity":"Cotton","variety":"Desi","min_price":6400,"max_price":7000,"modal_price":6720,"date":"14/05/2025"},
    {"state":"Punjab","district":"Patiala","market":"Patiala","commodity":"Mustard","variety":"Sarson","min_price":4800,"max_price":5400,"modal_price":5100,"date":"14/05/2025"},
    {"state":"Punjab","district":"Jalandhar","market":"Jalandhar","commodity":"Garlic","variety":"Local","min_price":3500,"max_price":5000,"modal_price":4200,"date":"14/05/2025"},
    {"state":"Haryana","district":"Hisar","market":"Hisar","commodity":"Wheat","variety":"Dara","min_price":2100,"max_price":2350,"modal_price":2230,"date":"14/05/2025"},
    {"state":"Haryana","district":"Karnal","market":"Karnal","commodity":"Rice","variety":"Basmati","min_price":3200,"max_price":3800,"modal_price":3500,"date":"14/05/2025"},
    {"state":"Uttar Pradesh","district":"Agra","market":"Agra","commodity":"Potato","variety":"Jyoti","min_price":800,"max_price":1200,"modal_price":1000,"date":"14/05/2025"},
    {"state":"Uttar Pradesh","district":"Lucknow","market":"Lucknow","commodity":"Onion","variety":"Local","min_price":1400,"max_price":1900,"modal_price":1650,"date":"14/05/2025"},
    {"state":"Uttar Pradesh","district":"Varanasi","market":"Varanasi","commodity":"Arhar Dal","variety":"Desi","min_price":6500,"max_price":7200,"modal_price":6800,"date":"14/05/2025"},
    {"state":"Maharashtra","district":"Nashik","market":"Lasalgaon","commodity":"Onion","variety":"Red","min_price":1200,"max_price":2100,"modal_price":1700,"date":"14/05/2025"},
    {"state":"Maharashtra","district":"Pune","market":"Pune","commodity":"Tomato","variety":"Local","min_price":600,"max_price":1400,"modal_price":900,"date":"14/05/2025"},
    {"state":"Karnataka","district":"Tumkur","market":"Tumkur","commodity":"Groundnut","variety":"Bold","min_price":4800,"max_price":5500,"modal_price":5200,"date":"14/05/2025"},
    {"state":"Madhya Pradesh","district":"Indore","market":"Indore","commodity":"Soyabean","variety":"Yellow","min_price":4100,"max_price":4600,"modal_price":4350,"date":"14/05/2025"},
    {"state":"Rajasthan","district":"Jaipur","market":"Jaipur","commodity":"Bajra","variety":"Hybrid","min_price":1700,"max_price":2000,"modal_price":1850,"date":"14/05/2025"},
    {"state":"Gujarat","district":"Rajkot","market":"Rajkot","commodity":"Groundnut","variety":"Bold","min_price":5000,"max_price":5800,"modal_price":5400,"date":"14/05/2025"},
    {"state":"Andhra Pradesh","district":"Guntur","market":"Guntur","commodity":"Chilli","variety":"Teja","min_price":8000,"max_price":12000,"modal_price":9800,"date":"14/05/2025"},
    {"state":"West Bengal","district":"Hooghly","market":"Singur","commodity":"Rice","variety":"Common","min_price":1800,"max_price":2100,"modal_price":1950,"date":"14/05/2025"},
    {"state":"Bihar","district":"Patna","market":"Patna","commodity":"Maize","variety":"Yellow","min_price":1600,"max_price":1900,"modal_price":1750,"date":"14/05/2025"},
]


@router.get("/prices")
async def get_mandi_prices(
    state:     str = Query(default="",  description="State name e.g. Punjab"),
    commodity: str = Query(default="",  description="Crop name e.g. Wheat"),
    district:  str = Query(default="",  description="District name"),
    limit:     int = Query(default=20,  ge=1, le=100),
):
    """
    Fetch live mandi prices from data.gov.in / AGMARKNET.
    Falls back to curated sample data if the external API is unavailable.
    """
    ck = _cache_key(state=state, commodity=commodity, district=district, limit=limit)
    cached = _cached(ck)
    if cached:
        logger.info(f"Mandi cache hit: {ck}")
        return cached

    params: dict = {
        "api-key": DATA_GOV_IN_KEY,
        "format":  "json",
        "limit":   limit,
        "offset":  0,
    }
    if state:     params["filters[state]"]     = state
    if commodity: params["filters[commodity]"] = commodity
    if district:  params["filters[district]"]  = district

    try:
        result = await _fetch_mandi_source(
            DATA_GOV_IN_BASE,
            params,
            "AGMARKNET / data.gov.in"
        )
        _store(ck, result)
        return result

    except Exception as primary_error:
        logger.warning(f"AGMARKNET unavailable ({primary_error})")

        if ALTERNATE_DATA_GOV_IN_BASE:
            logger.info("Attempting alternate mandi source")
            params["api-key"] = ALTERNATE_DATA_GOV_IN_KEY
            try:
                alt_result = await _fetch_mandi_source(
                    ALTERNATE_DATA_GOV_IN_BASE,
                    params,
                    "Alternate mandi API"
                )
                _store(ck, alt_result)
                return alt_result
            except Exception as alternate_error:
                logger.warning(
                    f"Alternate mandi source unavailable ({alternate_error}), using fallback data"
                )

        fb = list(FALLBACK_RECORDS)
        if state:     fb = [r for r in fb if state.lower()     in r["state"].lower()]
        if commodity: fb = [r for r in fb if commodity.lower() in r["commodity"].lower()]
        if district:  fb = [r for r in fb if district.lower()  in r["district"].lower()]
        if not fb:
            fb = list(FALLBACK_RECORDS)
        fb = fb[:limit]

        return {
            "total":    len(fb),
            "fetched":  len(fb),
            "records":  fb,
            "source":   "Sample data (AGMARKNET unreachable)",
            "cached":   False,
            "fallback": True,
        }


@router.get("/states")
async def get_states():
    return {
        "states": [
            "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh",
            "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
            "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
            "Odisha", "Punjab", "Rajasthan", "Tamil Nadu",
            "Telangana", "Uttar Pradesh", "Uttarakhand", "West Bengal",
        ]
    }


@router.get("/commodities")
async def get_commodities():
    return {
        "commodities": [
            "Wheat", "Rice", "Maize", "Bajra", "Jowar", "Barley",
            "Soyabean", "Mustard", "Groundnut", "Sunflower",
            "Cotton", "Sugarcane", "Jute",
            "Tomato", "Potato", "Onion", "Garlic",
            "Cabbage", "Cauliflower", "Brinjal", "Chilli",
            "Mango", "Banana", "Orange", "Lemon",
            "Moong Dal", "Masur Dal", "Arhar Dal", "Urad Dal",
        ]
    }
