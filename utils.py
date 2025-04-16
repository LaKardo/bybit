def is_invalid_api_key(api_key, api_secret):
    if not api_key or not api_secret:
        return True
    default_keys = [
        "your_bybit_api_key_here",
        "your_bybit_api_secret_here",
        "your_api_key_here",
        "your_api_secret_here",
        "test_api_key",
        "test_api_secret"
    ]
    if api_key in default_keys or api_secret in default_keys:
        return True
    if len(api_key) < 10 or len(api_secret) < 10:
        return True
    return False
def convert_timeframe(timeframe, from_format='bybit_v5', to_format='human'):
    bybit_v5_to_human = {
        '1': '1m', '3': '3m', '5': '5m', '15': '15m', '30': '30m',
        '60': '1h', '120': '2h', '240': '4h', '360': '6h', '720': '12h',
        'D': '1d', 'W': '1w', 'M': '1M'
    }
    human_to_bybit_v5 = {v: k for k, v in bybit_v5_to_human.items()}
    if from_format == 'bybit_v5':
        human_tf = bybit_v5_to_human.get(timeframe, timeframe)
    else:  
        human_tf = timeframe
    if to_format == 'bybit_v5':
        return human_to_bybit_v5.get(human_tf, human_tf)
    else:  
        return human_tf
