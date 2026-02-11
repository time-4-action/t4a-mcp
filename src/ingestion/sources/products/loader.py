"""Module for loading product data from the API."""
import requests

__all__ = ["get_products"]


def get_products():
    """Fetch products from the API.

    Returns:
        list: Product data from the API.

    Raises:
        requests.exceptions.HTTPError: If HTTP request fails.
        ValueError: If response is not valid JSON or success is false.
    """
    response = requests.get("https://api.time-4-action.com/api/export/product")
    
    # 1. Check HTTP status code
    response.raise_for_status()  # Raises exception for 4xx/5xx
    
    # 2. Check content type
    if "application/json" not in response.headers.get("Content-Type", ""):
        raise ValueError("Response is not JSON")

    # 3. Parse JSON
    data = response.json()

    # 4. Check response success field
    if not data.get("success"):
        raise ValueError("API returned status: false")

    # 5. Return products data
    return data.get("data", [])