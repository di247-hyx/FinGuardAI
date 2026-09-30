import aiohttp
import statistics


COINGECKO_URL = "https://api.coingecko.com/api/v3"


COIN_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "TRX": "tron",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "ATOM": "cosmos",
    "ETC": "ethereum-classic",
    "UNI": "uniswap",
    "XLM": "stellar",
    "NEAR": "near",
    "APT": "aptos",
}

async def binance_request(endpoint, params=None):

    url = BINANCE_URL + endpoint

    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(timeout=timeout) as session:

        async with session.get(
            url,
            params=params
        ) as response:

            if response.status != 200:
                raise Exception(
                    f"Binance HTTP {response.status}"
                )

            return await response.json()


async def get_24h_ticker(symbol):

    symbol = symbol.upper().replace(
        "/", ""
    )

    if not symbol.endswith("USDT"):
        symbol += "USDT"

    data = await binance_request(
        "/api/v3/ticker/24hr",
        {
            "symbol": symbol
        }
    )

    return data


async def get_klines(
    symbol,
    interval="1h",
    limit=100
):

    symbol = symbol.upper().replace(
        "/", ""
    )

    if not symbol.endswith("USDT"):
        symbol += "USDT"

    return await binance_request(
        "/api/v3/klines",
        {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
    )


def sma(values, period):

    if len(values) < period:
        return None

    return sum(
        values[-period:]
    ) / period


def ema(values, period):

    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    result = sum(
        values[:period]
    ) / period

    for price in values[period:]:

        result = (
            price - result
        ) * multiplier + result

    return result


def calculate_rsi(values, period=14):

    if len(values) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):

        change = values[i] - values[i - 1]

        if change >= 0:
            gains.append(change)
            losses.append(0)

        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(
        gains[-period:]
    ) / period

    avg_loss = sum(
        losses[-period:]
    ) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss

    return 100 - (
        100 / (1 + rs)
    )


def calculate_volatility(values):

    if len(values) < 2:
        return 0

    returns = []

    for i in range(1, len(values)):

        if values[i - 1] == 0:
            continue

        returns.append(
            (values[i] / values[i - 1] - 1)
            * 100
        )

    if len(returns) < 2:
        return 0

    return statistics.stdev(returns)


async def get_price(symbol):

    ticker = await get_24h_ticker(symbol)

    return {
        "symbol": ticker["symbol"],
        "price": float(ticker["lastPrice"]),
        "change_24h": float(ticker["priceChangePercent"]),
        "volume": float(ticker["volume"]),
        "high_24h": float(ticker["highPrice"]),
        "low_24h": float(ticker["lowPrice"]),
    }


async def get_market_analysis(symbol):

    ticker = await get_price(symbol)

    candles = await get_klines(
        symbol,
        "1h",
        100
    )

    closes = [
        float(candle[4])
        for candle in candles
    ]

    volumes = [
        float(candle[5])
        for candle in candles
    ]

    current_price = closes[-1]

    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)

    ema20 = ema(closes, 20)

    rsi = calculate_rsi(closes)

    volatility = calculate_volatility(closes)

    avg_volume = sum(
        volumes[-20:]
    ) / min(20, len(volumes))

    volume_ratio = (
        volumes[-1] / avg_volume
        if avg_volume
        else 0
    )

    if sma20 and current_price > sma20:
        trend = "Восходящий"

    elif sma20 and current_price < sma20:
        trend = "Нисходящий"

    else:
        trend = "Нейтральный"

    anomaly_score = 0

    if volume_ratio > 2:
        anomaly_score += 30

    elif volume_ratio > 1.5:
        anomaly_score += 15

    if abs(ticker["change_24h"]) > 10:
        anomaly_score += 30

    elif abs(ticker["change_24h"]) > 5:
        anomaly_score += 15

    if volatility > 5:
        anomaly_score += 20

    anomaly_score = min(
        anomaly_score,
        100
    )

    return {
        **ticker,

        "sma20": sma20,
        "sma50": sma50,
        "ema20": ema20,

        "rsi": rsi,
        "volatility": volatility,

        "volume_ratio": volume_ratio,

        "trend": trend,

        "anomaly_score": anomaly_score
    }
