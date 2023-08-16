from requests import get as http_get


def get_currency_history(start_date: str, end_date: str, symbols: str, base: str) -> dict:
    """
    Retrieve historical currency exchange rates between a base currency and specified symbols.

    Args:
        start_date (str): The start date of the historical data in the format 'YYYY-MM-DD'.
        end_date (str): The end date of the historical data in the format 'YYYY-MM-DD'.
        symbols (str): Comma-separated list of currency symbols to get rates for (e.g., 'USD,EUR,GBP').
        base (str): The base currency for the exchange rates (e.g., 'USD').

    Returns:
        dict: A dictionary containing historical exchange rate data. The structure of the dictionary is as follows:
            {
                "success": True or False,
                "timeseries": True or False,
                "base": "BaseCurrencyCode",
                "start_date": "YYYY-MM-DD",
                "end_date": "YYYY-MM-DD",
                "rates": {
                    "YYYY-MM-DD": {
                        "CurrencyCode1": ExchangeRate1,
                        "CurrencyCode2": ExchangeRate2,
                        ...
                    },
                    ...
                }
            }
            If the request was not successful or the data is unavailable, an empty dictionary is returned.
    """
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "symbols": symbols,
        "base": base
    }

    for key in params.items():
        if not key[1]:
            return {}

    resp = http_get("https://api.exchangerate.host/timeseries", params=params)
    json_body = resp.json()

    if not json_body["success"]:
        return {}

    del json_body["motd"]

    return json_body
