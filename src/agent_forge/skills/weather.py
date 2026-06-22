"""内置天气查询 Skill — Open-Meteo（免费，无需 API Key）

使用两步 API：
  1. Open-Meteo Geocoding API：城市名 → 经纬度
  2. Open-Meteo Weather API：经纬度 → 天气数据

不捏造数据：所有天气信息来自真实 API 返回。
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ── OpenAI Tool 定义（注入 LLM 的 tools 参数）─────────────────

GET_WEATHER_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "查询指定城市的实时天气和未来 3 天预报。"
            "当用户询问天气、气温、是否下雨、要不要带伞等问题时调用此工具。"
            "不要凭记忆猜测天气，必须调用此工具获取真实数据。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，支持中文或英文，如 '北京'、'上海'、'London'、'Tokyo'",
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "温度单位，默认 celsius（摄氏度）",
                },
            },
            "required": ["city"],
        },
    },
}

# 天气代码映射（WMO Weather Interpretation Codes）
_WMO_CODES: dict[int, str] = {
    0: "晴空", 1: "基本晴天", 2: "局部多云", 3: "阴天",
    45: "雾", 48: "雨凇雾",
    51: "小毛毛雨", 53: "中毛毛雨", 55: "大毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "小阵雨", 81: "中阵雨", 82: "强阵雨",
    85: "小阵雪", 86: "强阵雪",
    95: "雷暴", 96: "轻冰雹雷暴", 99: "强冰雹雷暴",
}


async def get_weather(city: str, unit: str = "celsius") -> dict[str, Any]:
    """
    查询城市实时天气。

    Returns:
        {
          "city": "北京",
          "latitude": 39.9,
          "longitude": 116.4,
          "current": {
            "temperature": 26.5,
            "unit": "°C",
            "description": "晴空",
            "humidity": 40,
            "wind_speed_kmh": 12.3,
            "feels_like": 27.1,
          },
          "forecast_3days": [
            {"date": "2026-06-22", "max": 30, "min": 22, "description": "局部多云"},
            ...
          ]
        }
    """
    # Step 1: Geocoding
    geo = await _geocode(city)
    if not geo:
        return {"error": f"找不到城市：{city}，请检查城市名称是否正确。"}

    lat = geo["latitude"]
    lon = geo["longitude"]
    city_name = geo.get("name", city)

    # Step 2: Weather
    temp_unit = "celsius" if unit != "fahrenheit" else "fahrenheit"
    unit_symbol = "°C" if temp_unit == "celsius" else "°F"

    weather_data = await _fetch_weather(lat, lon, temp_unit)
    if not weather_data:
        return {"error": "天气 API 请求失败，请稍后重试。"}

    current = weather_data.get("current", {})
    daily = weather_data.get("daily", {})

    # 解析当前天气
    wmo_code = current.get("weather_code", 0)
    current_weather = {
        "temperature": current.get("temperature_2m"),
        "unit": unit_symbol,
        "description": _WMO_CODES.get(wmo_code, f"未知({wmo_code})"),
        "humidity": current.get("relative_humidity_2m"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "feels_like": current.get("apparent_temperature"),
    }

    # 解析未来 3 天预报
    dates = daily.get("time", [])[:3]
    max_temps = daily.get("temperature_2m_max", [])[:3]
    min_temps = daily.get("temperature_2m_min", [])[:3]
    daily_codes = daily.get("weather_code", [])[:3]

    forecast = [
        {
            "date": dates[i],
            "max": max_temps[i] if i < len(max_temps) else None,
            "min": min_temps[i] if i < len(min_temps) else None,
            "description": _WMO_CODES.get(daily_codes[i], "未知") if i < len(daily_codes) else "未知",
            "unit": unit_symbol,
        }
        for i in range(len(dates))
    ]

    return {
        "city": city_name,
        "latitude": lat,
        "longitude": lon,
        "current": current_weather,
        "forecast_3days": forecast,
    }


async def _geocode(city: str) -> dict | None:
    """Open-Meteo Geocoding API：城市名 → 经纬度"""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city, "count": 1, "language": "zh", "format": "json"}

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                # 尝试英文搜索
                logger.info("Geocoding '%s' in zh failed, trying en", city)
                params["language"] = "en"
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
            if results:
                r = results[0]
                return {
                    "name": r.get("name", city),
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                    "country": r.get("country", ""),
                }
        except Exception as e:
            logger.warning("Geocoding failed for '%s': %s", city, e)
    return None


async def _fetch_weather(lat: float, lon: float, temp_unit: str) -> dict | None:
    """Open-Meteo Weather API：获取当前天气 + 7 天预报"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "weather_code",
            "wind_speed_10m",
        ],
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
        ],
        "temperature_unit": temp_unit,
        "wind_speed_unit": "kmh",
        "timezone": "auto",
        "forecast_days": 4,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Weather API failed for (%s, %s): %s", lat, lon, e)
    return None
