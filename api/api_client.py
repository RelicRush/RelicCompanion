"""
API Client for fetching Warframe data from external sources.
This module provides integration with warframe.market and the Warframe API.
"""

import json
from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import threading
import time

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False


@dataclass
class MarketListing:
    """Represents a listing from warframe.market"""
    seller: str
    price: int
    quantity: int
    status: str  # online, offline, ingame
    
    @property
    def status_emoji(self) -> str:
        if self.status == "ingame":
            return "🟢"
        elif self.status == "online":
            return "🟡"
        return "⚫"


@dataclass  
class MarketItem:
    """Represents an item from warframe.market"""
    id: str
    url_name: str
    item_name: str
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    avg_price: Optional[float] = None


@dataclass
class PriceData:
    """Cached price data for an item"""
    item_name: str
    url_name: str
    lowest_price: Optional[int] = None
    avg_price: Optional[float] = None
    volume: Optional[int] = None
    listings: list[MarketListing] = field(default_factory=list)
    last_updated: Optional[datetime] = None
    error: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if the cached data is still valid (less than 5 minutes old)."""
        if self.last_updated is None:
            return False
        age = (datetime.now() - self.last_updated).total_seconds()
        return age < 300  # 5 minutes
    
    def get_price_display(self) -> str:
        """Get a formatted price display string."""
        if self.error:
            return "Error"
        if self.lowest_price is None:
            return "N/A"
        return f"{self.lowest_price}p"


class WarframeMarketAPI:
    """
    Client for the warframe.market API v2.
    Provides price data for Prime parts.
    """
    
    BASE_URL = "https://api.warframe.market/v2"
    PLATFORM = "pc"  # Can be: pc, xbox, ps4, switch, mobile
    
    def __init__(self, platform: str = "pc"):
        self.platform = platform
        self._cache: dict[str, PriceData] = {}
        self._item_list: list[MarketItem] = []
        self._item_list_loaded = False
        self._last_request_time = 0
        self._min_request_interval = 0.35  # ~3 requests per second (API v2 limit)
        
        # Setup session for requests library
        if HAS_REQUESTS:
            self._session = requests.Session()
            self._session.headers.update({
                "Platform": self.platform,
                "Language": "en",
                "Crossplay": "true",
                "User-Agent": "WarframeRelicCompanion/1.0 (contact: github.com/warframe-relic-companion)",
                "Accept": "application/json",
            })
    
    def _rate_limit(self):
        """Ensure we don't make requests too quickly."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _make_request(self, endpoint: str) -> Optional[dict]:
        """
        Make a GET request to the API.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            JSON response as dict, or None if request fails
        """
        self._rate_limit()
        url = f"{self.BASE_URL}{endpoint}"
        
        if HAS_REQUESTS:
            try:
                response = self._session.get(url, timeout=10)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                print(f"HTTP Error: {e.response.status_code}")
                return None
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                print(f"API Error: {e}")
                return None
        else:
            # Fallback to urllib
            headers = {
                "Platform": self.platform,
                "Language": "en",
                "Crossplay": "true",
                "User-Agent": "WarframeRelicCompanion/1.0 (contact: github.com/warframe-relic-companion)",
                "Accept": "application/json",
            }
            
            try:
                request = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(request, timeout=10) as response:
                    return json.loads(response.read().decode())
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                print(f"HTTP Error: {e.code}")
                return None
            except (urllib.error.URLError, json.JSONDecodeError) as e:
                print(f"API Error: {e}")
                return None
    
    def get_all_items(self) -> list[MarketItem]:
        """
        Get a list of all tradeable items.
        
        Returns:
            List of MarketItem objects
        """
        if self._item_list_loaded:
            return self._item_list
            
        response = self._make_request("/items")
        if not response:
            return []
        
        items = []
        # v2 API returns data directly in 'data' array
        for item_data in response.get("data", []):
            # v2 uses 'slug' instead of 'url_name', and 'i18n' for names
            i18n = item_data.get("i18n", {}).get("en", {})
            items.append(MarketItem(
                id=item_data.get("id", ""),
                url_name=item_data.get("slug", ""),
                item_name=i18n.get("name", item_data.get("slug", ""))
            ))
        
        self._item_list = items
        self._item_list_loaded = True
        return items
    
    def get_item_orders(self, url_name: str) -> list[MarketListing]:
        """
        Get current sell orders for an item.
        
        Args:
            url_name: The URL-safe item name (e.g., "trinity_prime_systems")
            
        Returns:
            List of MarketListing objects for sell orders
        """
        # v2 API uses /orders/item/{slug}/top for top 5 buy/sell from online users
        response = self._make_request(f"/orders/item/{url_name}/top")
        if not response:
            return []
        
        listings = []
        # v2 returns {data: {buy: [...], sell: [...]}}
        data = response.get("data", {})
        for order in data.get("sell", []):
            user = order.get("user", {})
            listings.append(MarketListing(
                seller=user.get("ingameName", "Unknown"),
                price=order.get("platinum", 0),
                quantity=order.get("quantity", 1),
                status=user.get("status", "offline")
            ))
        
        # Sort by price (lowest first)
        listings.sort(key=lambda x: x.price)
        return listings
    
    def get_all_item_orders(self, url_name: str) -> list[MarketListing]:
        """
        Get all sell orders for an item (not just top 5).
        
        Args:
            url_name: The URL-safe item name (e.g., "trinity_prime_systems")
            
        Returns:
            List of MarketListing objects for sell orders
        """
        response = self._make_request(f"/orders/item/{url_name}")
        if not response:
            return []
        
        listings = []
        for order in response.get("data", []):
            if order.get("type") == "sell":
                user = order.get("user", {})
                listings.append(MarketListing(
                    seller=user.get("ingameName", "Unknown"),
                    price=order.get("platinum", 0),
                    quantity=order.get("quantity", 1),
                    status=user.get("status", "offline")
                ))
        
        # Sort by price (lowest first)
        listings.sort(key=lambda x: x.price)
        return listings
    
    def get_item_statistics(self, url_name: str) -> Optional[dict]:
        """
        Get price statistics for an item.
        Note: v2 API doesn't have a direct statistics endpoint, 
        so we calculate from orders.
        
        Args:
            url_name: The URL-safe item name
            
        Returns:
            Dict with price statistics or None
        """
        # Get all orders to calculate statistics
        listings = self.get_all_item_orders(url_name)
        if not listings:
            return None
        
        prices = [l.price for l in listings]
        return {
            "avg_price": sum(prices) / len(prices) if prices else None,
            "min_price": min(prices) if prices else None,
            "max_price": max(prices) if prices else None,
            "volume": len(prices)
        }
    
    def get_lowest_price(self, url_name: str, online_only: bool = True) -> Optional[int]:
        """
        Get the lowest current sell price for an item.
        
        Args:
            url_name: The URL-safe item name
            online_only: If True, only consider online sellers
            
        Returns:
            Lowest price in platinum, or None if not found
        """
        listings = self.get_item_orders(url_name)
        
        if online_only:
            listings = [l for l in listings if l.status in ("online", "ingame")]
        
        if listings:
            return listings[0].price
        return None
    
    def get_price_data(self, item_name: str, force_refresh: bool = False) -> PriceData:
        """
        Get comprehensive price data for an item, with caching.
        
        Args:
            item_name: The item name (e.g., "Trinity Prime Systems Blueprint")
            force_refresh: If True, bypass cache
            
        Returns:
            PriceData object with price information
        """
        url_name = convert_to_url_name(item_name)
        
        # Check cache
        if not force_refresh and url_name in self._cache:
            cached = self._cache[url_name]
            if cached.is_valid:
                return cached
        
        # Fetch fresh data
        price_data = PriceData(
            item_name=item_name,
            url_name=url_name,
            last_updated=datetime.now()
        )
        
        try:
            # Get listings
            listings = self.get_item_orders(url_name)
            price_data.listings = listings[:10]  # Keep top 10
            
            # Calculate prices from online sellers
            online_listings = [l for l in listings if l.status in ("online", "ingame")]
            if online_listings:
                price_data.lowest_price = online_listings[0].price
            elif listings:
                price_data.lowest_price = listings[0].price
            
            # Get statistics
            stats = self.get_item_statistics(url_name)
            if stats:
                price_data.avg_price = stats.get("avg_price")
                price_data.volume = stats.get("volume")
                
        except Exception as e:
            price_data.error = str(e)
        
        # Cache the result
        self._cache[url_name] = price_data
        return price_data
    
    def get_price_data_async(self, item_name: str, callback: Callable[[PriceData], None],
                             force_refresh: bool = False):
        """
        Get price data asynchronously.
        
        Args:
            item_name: The item name
            callback: Function to call with the result
            force_refresh: If True, bypass cache
        """
        def fetch():
            result = self.get_price_data(item_name, force_refresh)
            callback(result)
        
        thread = threading.Thread(target=fetch, daemon=True)
        thread.start()
    
    def get_multiple_prices(self, item_names: list[str], 
                           callback: Callable[[dict[str, PriceData]], None],
                           delay: float = 0.35):
        """
        Get prices for multiple items with rate limiting.
        
        Args:
            item_names: List of item names to fetch
            callback: Function to call with results dict
            delay: Delay between requests to avoid rate limiting
        """
        def fetch_all():
            results = {}
            for item_name in item_names:
                url_name = convert_to_url_name(item_name)
                
                # Check cache first
                if url_name in self._cache and self._cache[url_name].is_valid:
                    results[item_name] = self._cache[url_name]
                else:
                    results[item_name] = self.get_price_data(item_name)
                    time.sleep(delay)  # Rate limiting
            
            callback(results)
        
        thread = threading.Thread(target=fetch_all, daemon=True)
        thread.start()
    
    def clear_cache(self):
        """Clear the price cache."""
        self._cache.clear()


class WarframeDropTableAPI:
    """
    Client for the official Warframe drop table data.
    """
    
    DROP_TABLE_URL = "https://drops.warframestat.us/data/relics.json"
    
    def get_relic_data(self) -> Optional[dict]:
        """
        Fetch current relic drop table data.
        
        Returns:
            Dict containing relic data or None
        """
        try:
            with urllib.request.urlopen(self.DROP_TABLE_URL, timeout=15) as response:
                return json.loads(response.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
            print(f"Error fetching drop tables: {e}")
            return None


def convert_to_url_name(item_name: str) -> str:
    """
    Convert an item name to URL-safe format for warframe.market.
    
    Args:
        item_name: The item name (e.g., "Trinity Prime Systems Blueprint")
        
    Returns:
        URL-safe name (e.g., "trinity_prime_systems_blueprint")
    """
    # Remove "Blueprint" suffix if present (market doesn't always use it)
    name = item_name.strip()
    
    # Handle special cases
    replacements = {
        "'": "",
        "&": "and",
        "-": "_",
    }
    
    for old, new in replacements.items():
        name = name.replace(old, new)
    
    return name.lower().replace(" ", "_")


def format_platinum(amount: Optional[int]) -> str:
    """Format a platinum amount for display."""
    if amount is None:
        return "N/A"
    return f"{amount}p"


# Example usage
if __name__ == "__main__":
    api = WarframeMarketAPI()
    
    # Example: Get price for Trinity Prime Systems
    item_name = "Trinity Prime Systems Blueprint"
    print(f"Fetching price for: {item_name}")
    
    price_data = api.get_price_data(item_name)
    print(f"Lowest price: {price_data.get_price_display()}")
    if price_data.avg_price:
        print(f"Average price: {price_data.avg_price:.1f}p")
    
    print("\nTop listings:")
    for listing in price_data.listings[:5]:
        print(f"  {listing.status_emoji} {listing.price}p x{listing.quantity} by {listing.seller}")
