"""
KisanSathi — Mandi Price Routes
Fetches real-time crop market prices from India's official
data.gov.in AGMARKNET API (resource: 9ef84268-d588-465a-a308-a864a43d0070)
"""

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
import httpx
import time
from loguru import logger

router = APIRouter(prefix="/api/mandi", tags=["mandi"])

# Official India Open Gov Data — AGMARKNET daily mandi prices
DATA_GOV_IN_BASE = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
# Public / demo API key — users should replace with their own from data.gov.in
DATA_GOV_IN_KEY  = "579b464db66ec23bdd000001cdd3946e44ce4aad38d82be3b8fac29"

# Simple in-memory cache: {cache_key: (timestamp, data)}
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


@router.get("/prices")
async def get_mandi_prices(
    state:     str = Query(default="",   description="State name e.g. Punjab"),
    commodity: str = Query(default="",   description="Crop name e.g. Wheat"),
    district:  str = Query(default="",   description="District name"),
    limit:     int = Query(default=20,   ge=1, le=100),
):
    """
    Fetch live mandi prices from data.gov.in / AGMARKNET.
    Filters: state, commodity, district (all optional).
    Returns records with min_price, max_price, modal_price per market.
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
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(DATA_GOV_IN_BASE, params=params)
            resp.raise_for_status()
            raw = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"AGMARKNET API error: {e.response.status_code}")
        raise HTTPException(status_code=502, detail="Mandi data API unavailable. Try again later.")
    except Exception as e:
        logger.error(f"Mandi fetch error: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch mandi prices.")

    records = raw.get("records", [])
    total   = raw.get("total", len(records))

    # Normalize & clean records
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

    result = {
        "total":   total,
        "fetched": len(cleaned),
        "records": cleaned,
        "source":  "AGMARKNET / data.gov.in",
        "cached":  False,
    }
    _store(ck, result)
    return result


@router.get("/states")
async def get_states():
    """Return commonly supported states for the filter UI."""
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
    """Return popular commodities for the filter UI."""
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
