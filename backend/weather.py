import hashlib
import math
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import httpx

from .network import get_network

OWM_API_KEY = os.getenv("OWM_API_KEY", "").strip()
OWM_BASE = "https://api.openweathermap.org/data/2.5"
CACHE_TTL_SECONDS = int(os.getenv("WEATHER_CACHE_TTL", "600"))

IST = timezone(timedelta(hours=5, minutes=30))


def is_demo_mode():
    return not OWM_API_KEY


class TTLCache:
   
    def __init__(self, ttl):
        self.ttl = ttl
        self._data = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key):
        with self._lock:
            item = self._data.get(key)
            if item and item[0] > time.time():
                self.hits += 1
                return item[1]
            self.misses += 1
            return None

    def set(self, key, value):
        with self._lock:
            self._data[key] = (time.time() + self.ttl, value)

    def stats(self):
        with self._lock:
            live = len(
                [1 for expires, _ in self._data.values() if expires > time.time()]
            )
        return {
            "entries": live,
            "hits": self.hits,
            "misses": self.misses,
            "ttl_seconds": self.ttl,
        }


_cache = TTLCache(CACHE_TTL_SECONDS)


def cache_stats():
    return _cache.stats()


def _slot(
    dt,
    temp,
    feels,
    humidity,
    cond_id,
    main,
    desc,
    wind,
    visibility,
    rain_mm,
    snow_mm,
    pop,
):
    
    return {
        "dt": int(dt),
        "time": datetime.fromtimestamp(dt, IST).isoformat(),
        "temp": round(temp, 1),
        "feels_like": round(feels, 1),
        "humidity": int(humidity),
        "condition_id": int(cond_id),
        "condition": main,
        "description": desc,
        "wind_speed": round(wind, 1),  # m/s
        "visibility": int(visibility),  # metres
        "rain_mm": round(rain_mm, 1),  # in the 3 hour window
        "snow_mm": round(snow_mm, 1),
        "pop": round(pop, 2),  # chance of rain, 0 to 1
    }


def _from_owm(item):
    
    w = (item.get("weather") or [{}])[0]
    rain = item.get("rain") or {}
    snow = item.get("snow") or {}
    return _slot(
        dt=item["dt"],
        temp=item["main"]["temp"],
        feels=item["main"].get("feels_like", item["main"]["temp"]),
        humidity=item["main"].get("humidity", 0),
        cond_id=w.get("id", 800),
        main=w.get("main", "Clear"),
        desc=w.get("description", ""),
        wind=item.get("wind", {}).get("speed", 0.0),
        visibility=item.get("visibility", 10000),
        rain_mm=rain.get("3h", rain.get("1h", 0.0)),
        snow_mm=snow.get("3h", snow.get("1h", 0.0)),
        pop=item.get("pop", 0.0),
    )


def _owm_get(path, lat, lon):
    params = {"lat": lat, "lon": lon, "appid": OWM_API_KEY, "units": "metric"}
    r = httpx.get(f"{OWM_BASE}/{path}", params=params, timeout=10.0)
    r.raise_for_status()
    return r.json()


def _cell(lat, lon):
    
    return round(lat * 4) / 4, round(lon * 4) / 4


def _live_forecast(lat, lon):
    fc = _owm_get("forecast", lat, lon)  
    cur = _owm_get("weather", lat, lon)  
    return {
        "lat": lat,
        "lon": lon,
        "source": "openweathermap",
        "sunrise": cur.get("sys", {}).get("sunrise"),
        "sunset": cur.get("sys", {}).get("sunset"),
        "current": _from_owm(cur),
        "slots": [_from_owm(x) for x in fc.get("list", [])],
    }




CONDITIONS = {
    # name: (OWM id, main, description)
    "clear": (800, "Clear", "clear sky"),
    "clouds": (803, "Clouds", "broken clouds"),
    "light_rain": (500, "Rain", "light rain"),
    "rain": (501, "Rain", "moderate rain"),
    "heavy_rain": (502, "Rain", "heavy intensity rain"),
    "storm": (211, "Thunderstorm", "thunderstorm"),
    "fog": (741, "Fog", "fog"),
    "haze": (721, "Haze", "haze"),
}


def _region(lat, lon):
    if lon > 88.5 and lat > 22:
        return "wet"  
    if lat < 22.7 and lon > 80 + max(0, lat - 13) * 0.55:
        return "coastal"  
    if lon < 74.6 and lat < 21.5 or lat < 13 and lon < 77.2:
        return "coastal"  
    if lat >= 24.5 and 73.5 <= lon <= 88.5:
        return "north_plains"
    if 16 <= lat < 24.5:
        return "hot_interior"
    return "other"


def _rng(*parts):
    
    seed = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return random.Random(int(seed[:16], 16))


def _pick_regime(region, roll):
    if region in ("coastal", "wet"):
        if roll < 0.14:
            return "storm"
        if roll < 0.28:
            return "heavy_rain"
        if roll < 0.55:
            return "rain"
        if roll < 0.80:
            return "clouds"
        return "clear"
    if region == "north_plains":
        if roll < 0.25:
            return "fog"
        if roll < 0.45:
            return "haze"
        if roll < 0.55:
            return "rain"
        if roll < 0.75:
            return "clouds"
        return "clear"
    if region == "hot_interior":
        if roll < 0.12:
            return "storm"
        if roll < 0.25:
            return "rain"
        if roll < 0.50:
            return "clouds"
        return "clear"
    if roll < 0.25:
        return "rain"
    if roll < 0.55:
        return "clouds"
    return "clear"


def _demo_forecast(lat, lon):
    region = _region(lat, lon)
    now = datetime.now(IST)
    start = now.replace(minute=0, second=0, microsecond=0)
    start -= timedelta(hours=start.hour % 3)


    base_temp = 36 - (lat - 12) * 0.55
    if now.month not in (4, 5, 6):
        base_temp -= 4
    if now.month in (12, 1, 2) and lat > 22:
        base_temp -= 7

    slots = []
    for i in range(40):  
        t = start + timedelta(hours=3 * i)
        day_rng = _rng(round(lat / 1.5), round(lon / 1.5), t.date().isoformat())
        slot_rng = _rng(lat, lon, t.isoformat())
        hour = t.hour
        temp = (
            base_temp
            - math.cos((hour - 3) / 24 * 2 * math.pi) * 4
            + day_rng.uniform(-2, 2)
        )

        regime = _pick_regime(region, day_rng.random())
        cond = regime
        if regime == "fog" and not (hour <= 9 or hour >= 21):
            cond = "haze"
        if regime in ("storm", "heavy_rain") and not (12 <= hour <= 23):
            cond = "rain" if slot_rng.random() < 0.6 else "clouds"
        if regime == "rain" and slot_rng.random() < 0.35:
            cond = "clouds"

        cid, main, desc = CONDITIONS[cond]
        rain = {"light_rain": 0.8, "rain": 4.5, "heavy_rain": 14.0, "storm": 18.0}.get(
            cond, 0.0
        )
        rain = rain * slot_rng.uniform(0.6, 1.4)
        wind = slot_rng.uniform(1.5, 5.0) + {
            "storm": 12.0,
            "heavy_rain": 6.0,
            "rain": 2.0,
        }.get(cond, 0.0)

        fog_vis = slot_rng.randint(80, 600)
        haze_vis = slot_rng.randint(1500, 4000)
        rain_vis = slot_rng.randint(1500, 4000)
        storm_vis = slot_rng.randint(1000, 3000)
        vis = {
            "fog": fog_vis,
            "haze": haze_vis,
            "heavy_rain": rain_vis,
            "storm": storm_vis,
        }.get(cond, 10000)

        if cond in ("rain", "heavy_rain", "storm"):
            temp -= 2
        humidity = 45 + slot_rng.uniform(-8, 8)
        if cond not in ("clear", "haze"):
            humidity += 35
        humidity = int(min(98, humidity))
        pop = {
            "clear": 0.0,
            "clouds": 0.1,
            "haze": 0.0,
            "fog": 0.05,
            "light_rain": 0.45,
            "rain": 0.7,
            "heavy_rain": 0.9,
            "storm": 0.95,
        }[cond]
        feels = temp + 2 if humidity > 70 else temp
        slots.append(
            _slot(
                int(t.timestamp()),
                temp,
                feels,
                humidity,
                cid,
                main,
                desc,
                wind,
                vis,
                rain,
                0.0,
                pop,
            )
        )

    return {
        "lat": lat,
        "lon": lon,
        "source": "demo",
        "sunrise": int(now.replace(hour=6, minute=5, second=0).timestamp()),
        "sunset": int(now.replace(hour=18, minute=10, second=0).timestamp()),
        "current": slots[0],
        "slots": slots,
    }


def get_forecast(code):
    net = get_network()
    if code not in net.stations:
        raise KeyError(code)
    lat, lon = _cell(*net.coords(code))
    key = ("demo:" if is_demo_mode() else "owm:") + f"{lat},{lon}"
    data = _cache.get(key)
    if data is None:
        if is_demo_mode():
            data = _demo_forecast(lat, lon)
        else:
            try:
                data = _live_forecast(lat, lon)
            except (httpx.HTTPError, KeyError, ValueError):
                
                data = _demo_forecast(lat, lon)
                data["source"] = "demo-fallback"
        _cache.set(key, data)
   
    s = net.stations[code]
    return {**data, "code": code, "city": s["name"], "lat": s["lat"], "lon": s["lon"]}


def get_forecasts(cities):
    
    unique = sorted(set(cities))
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(unique)))) as pool:
        results = list(pool.map(get_forecast, unique))
    return dict(zip(unique, results))


def source_label(forecasts):
    
    sources = {f.get("source") for f in forecasts.values()}
    if sources == {"openweathermap"}:
        return "openweathermap"
    if "openweathermap" in sources:
        return "partial"  
    if "demo-fallback" in sources:
        return "demo-fallback"
    return "demo"


def slot_at(forecast, when):
   
    slots = forecast.get("slots") or []
    if not slots:
        return None
    ts = when.timestamp()
    return min(slots, key=lambda s: abs(s["dt"] - ts))


def forecast_horizon(forecast):
    slots = forecast.get("slots") or []
    if not slots:
        return None
    return datetime.fromtimestamp(slots[-1]["dt"], IST)
