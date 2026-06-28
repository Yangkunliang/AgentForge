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

# 中文城市名 → 英文名映射（Open-Meteo Geocoding API 对部分中文短地名识别不稳定）
# 优先用英文名查询，保障准确性
_CITY_NAME_MAP: dict[str, str] = {
    # 直辖市
    "北京": "Beijing", "上海": "Shanghai", "天津": "Tianjin", "重庆": "Chongqing",
    # 省会 / 主要城市
    "广州": "Guangzhou", "深圳": "Shenzhen", "成都": "Chengdu", "杭州": "Hangzhou",
    "武汉": "Wuhan", "西安": "Xi'an", "南京": "Nanjing", "郑州": "Zhengzhou",
    "长沙": "Changsha", "沈阳": "Shenyang", "青岛": "Qingdao", "大连": "Dalian",
    "厦门": "Xiamen", "福州": "Fuzhou", "济南": "Jinan", "哈尔滨": "Harbin",
    "长春": "Changchun", "昆明": "Kunming", "贵阳": "Guiyang", "南宁": "Nanning",
    "海口": "Haikou", "三亚": "Sanya", "太原": "Taiyuan", "合肥": "Hefei",
    "南昌": "Nanchang", "石家庄": "Shijiazhuang", "呼和浩特": "Hohhot",
    "乌鲁木齐": "Urumqi", "拉萨": "Lhasa", "西宁": "Xining", "银川": "Yinchuan",
    "兰州": "Lanzhou", "南京": "Nanjing", "苏州": "Suzhou", "无锡": "Wuxi",
    "宁波": "Ningbo", "温州": "Wenzhou", "佛山": "Foshan", "东莞": "Dongguan",
    "珠海": "Zhuhai", "中山": "Zhongshan", "汕头": "Shantou",
    # 港澳台
    "香港": "Hong Kong", "澳门": "Macao", "台北": "Taipei", "台湾": "Taiwan",
    # 其他常见
    "烟台": "Yantai", "威海": "Weihai", "唐山": "Tangshan", "保定": "Baoding",
    "洛阳": "Luoyang", "开封": "Kaifeng", "徐州": "Xuzhou", "南通": "Nantong",
}


async def get_weather(city: str, unit: str = "celsius") -> dict[str, Any]:
    """
    查询城市实时天气。

    Returns:
        {
          "city": "厦门",
          "latitude": 24.48,
          "longitude": 118.08,
          "current": {
            "temperature": 30.2,
            "unit": "°C",
            "description": "局部多云",
            "humidity": 75,
            "wind_speed_kmh": 18.5,
            "feels_like": 35.1,
          },
          "forecast_3days": [
            {"date": "2026-06-28", "max": 33, "min": 27, "description": "小阵雨"},
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
    """Open-Meteo Geocoding API：城市名 → 经纬度

    查询顺序：
      1. 若城市名在 _CITY_NAME_MAP 中，优先用英文名查询（最可靠）
      2. 否则直接用原始名查询（支持中文，但部分短地名可能识别失败）
      3. 若失败，用英文再试一次
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"

    # 若有预设映射，优先用英文名
    query_name = _CITY_NAME_MAP.get(city, city)
    if query_name != city:
        logger.info("Geocoding: mapped '%s' → '%s'", city, query_name)

    async with httpx.AsyncClient(timeout=10) as client:
        # 尝试顺序：优先映射名（中文城市走英文），失败则 fallback 原名
        candidates = [query_name]
        if query_name == city:
            # 没有映射：先试中文，失败再试英文（open-meteo 有时识别中文）
            candidates = [city]
        # 若映射名与原名不同（已转英文），无需额外 fallback
        # 若完全没命中（偏远地名），最后追加一次英文搜索（language=en）
        if query_name == city:
            candidates.append(city + " China")  # 加 China 后缀提升识别率

        for name in candidates:
            try:
                params = {"name": name, "count": 1, "language": "zh", "format": "json"}
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                results = resp.json().get("results", [])
                if results:
                    r = results[0]
                    logger.info("Geocoding success: '%s' → %s", name, r.get("name"))
                    return {
                        "name": r.get("name", city),
                        "latitude": r["latitude"],
                        "longitude": r["longitude"],
                        "country": r.get("country", ""),
                    }
                logger.info("Geocoding '%s' returned no results", name)
            except Exception as e:
                logger.warning("Geocoding failed for '%s': %s", name, e)

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
