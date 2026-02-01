"""
AlecaFrame API Client
Fetches inventory data directly from AlecaFrame using user's public token.

AlecaFrame API Documentation: https://docs.alecaframe.com/api
Swagger: https://stats.alecaframe.com/api/swagger/index.html
"""

import json
import struct
import base64
from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import re
from urllib.parse import urlparse, parse_qs, quote, unquote

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False


@dataclass
class AlecaFrameRelic:
    """Represents a relic from AlecaFrame inventory."""
    name: str
    era: str
    identifier: str  # e.g., "A1", "B2"
    refinement: str
    quantity: int
    vaulted: bool = False
    
    @property
    def full_name(self) -> str:
        return f"{self.era} {self.identifier}"


@dataclass
class AlecaFrameProfile:
    """User profile data from AlecaFrame."""
    username: Optional[str] = None
    mastery_rank: int = 0
    mastery_percentage: int = 0
    platinum: int = 0
    credits: int = 0
    endo: int = 0
    ducats: int = 0
    aya: int = 0
    relics_opened: int = 0
    trades: int = 0
    last_update: Optional[datetime] = None
    error: Optional[str] = None
    
    def format_credits(self) -> str:
        """Format credits with K/M suffix."""
        if self.credits >= 1_000_000:
            return f"{self.credits / 1_000_000:.2f}M"
        elif self.credits >= 1_000:
            return f"{self.credits / 1_000:.1f}K"
        return str(self.credits)
    
    def format_endo(self) -> str:
        """Format endo with K/M suffix."""
        if self.endo >= 1_000_000:
            return f"{self.endo / 1_000_000:.2f}M"
        elif self.endo >= 1_000:
            return f"{self.endo / 1_000:.2f}K"
        return str(self.endo)


@dataclass
class AlecaFrameInventory:
    """Container for AlecaFrame inventory data."""
    relics: list[AlecaFrameRelic] = field(default_factory=list)
    last_synced: Optional[datetime] = None
    username: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def total_relics(self) -> int:
        return sum(r.quantity for r in self.relics)


class AlecaFrameAPI:
    """
    Client for the AlecaFrame Stats API.
    Fetches user relic inventory data using their public token.
    
    Users can get a public token by:
    1. Going to the "Stats" tab in AlecaFrame
    2. Click "Create Public Link"
    3. Make sure "relics" is selected
    4. Click "Generate token"
    """
    
    BASE_URL = "https://stats.alecaframe.com/api"
    
    # Relic era mapping from binary format
    ERA_MAP = {0: "Lith", 1: "Meso", 2: "Neo", 3: "Axi", 4: "Requiem"}
    
    # Refinement mapping from binary format
    REFINEMENT_MAP = {
        0: "Intact", 
        1: "Exceptional", 
        2: "Flawless", 
        3: "Radiant",
        4: "Exceptional",  # Duplicate in their format
        5: "Flawless", 
        6: "Radiant"
    }
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token
        
        if HAS_REQUESTS:
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": "WarframeRelicCompanion/1.0",
                "Accept": "application/octet-stream, application/json",
            })
    
    def set_token(self, token: str):
        """
        Set or update the API token.
        Accepts either:
        - A raw token string
        - A full AlecaFrame stats URL (will extract the token)
        """
        token = token.strip()
        
        # Check if user pasted a full URL
        if token.startswith('http'):
            extracted = self._extract_token_from_url(token)
            if extracted:
                token = extracted
        
        # URL-decode the token if it's encoded
        if '%' in token:
            token = unquote(token)
        
        self.api_token = token
        print(f"AlecaFrame: Token set (length: {len(token)})")
    
    def _extract_token_from_url(self, url: str) -> Optional[str]:
        """Extract the publicToken from an AlecaFrame stats URL."""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Try different parameter names
            for param_name in ['publicToken', 'token']:
                if param_name in params:
                    return params[param_name][0]
            
            return None
        except Exception as e:
            print(f"AlecaFrame: Could not parse URL: {e}")
            return None
    
    def _make_request(self, endpoint: str, binary: bool = False, param_name: str = "token") -> Optional[bytes | dict]:
        """Make a request to AlecaFrame Stats API."""
        if not self.api_token:
            return None
        
        url = f"{self.BASE_URL}{endpoint}"
        
        # URL-encode the token for the query parameter
        encoded_token = quote(self.api_token, safe='')
        
        # Add token as query parameter with the specified parameter name
        if "?" in url:
            url += f"&{param_name}={encoded_token}"
        else:
            url += f"?{param_name}={encoded_token}"
        
        # Debug: print URL (with token partially hidden)
        debug_url = url.replace(encoded_token, encoded_token[:8] + "..." if len(encoded_token) > 8 else "***")
        print(f"AlecaFrame: Requesting {debug_url}")
        
        headers = {
            "User-Agent": "WarframeRelicCompanion/1.0",
            "Accept": "*/*",  # Accept any content type
        }
        
        if HAS_REQUESTS:
            try:
                response = self._session.get(url, headers=headers, timeout=15)
                print(f"AlecaFrame: Response status {response.status_code}, content-type: {response.headers.get('content-type', 'unknown')}")
                response.raise_for_status()
                if binary:
                    return response.content
                return response.json()
            except requests.exceptions.HTTPError as e:
                # Try to get error details from response body
                error_body = ""
                try:
                    error_body = e.response.text[:200] if e.response.text else ""
                except:
                    pass
                
                if e.response.status_code == 400:
                    print(f"AlecaFrame: Bad request - {error_body}")
                elif e.response.status_code == 401:
                    print("AlecaFrame: Invalid or expired token")
                elif e.response.status_code == 403:
                    print("AlecaFrame: Token doesn't have relic access")
                elif e.response.status_code == 404:
                    print(f"AlecaFrame: Not found - {error_body}")
                elif e.response.status_code == 500:
                    print(f"AlecaFrame: Server error - {error_body}")
                else:
                    print(f"AlecaFrame HTTP Error: {e.response.status_code} - {error_body}")
                return None
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                print(f"AlecaFrame API Error: {e}")
                return None
        else:
            try:
                request = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(request, timeout=15) as response:
                    data = response.read()
                    if binary:
                        return data
                    return json.loads(data.decode())
            except urllib.error.HTTPError as e:
                error_body = ""
                try:
                    error_body = e.read().decode()[:200]
                except:
                    pass
                print(f"AlecaFrame HTTP Error: {e.code} - {error_body}")
                return None
            except (urllib.error.URLError, json.JSONDecodeError) as e:
                print(f"AlecaFrame API Error: {e}")
                return None
    
    def test_connection(self) -> tuple[bool, str]:
        """
        Test if the API token is valid.
        
        Returns:
            Tuple of (success, message)
        """
        if not self.api_token:
            return False, "No API token provided"
        
        # Try to fetch relic inventory - this will test the token
        # The relic inventory endpoint uses 'publicToken' as the parameter name
        result = self._make_request("/stats/public/getRelicInventory", binary=True, param_name="publicToken")
        
        if result is not None:
            # Try to parse it to make sure it's valid data
            try:
                relics = self._parse_binary_relic_data(result)
                return True, f"Success! Found {len(relics)} unique relic types."
            except:
                return True, "Token valid! Connected to AlecaFrame."
        
        # Token didn't work - provide helpful error message
        return False, (
            "Could not connect. Please ensure:\n"
            "1. Token was generated with 'relics' enabled\n"
            "2. Token has not expired\n"
            "3. Try generating a new token in AlecaFrame"
        )
    
    def get_inventory(self) -> AlecaFrameInventory:
        """
        Fetch the user's relic inventory from AlecaFrame.
        
        Returns:
            AlecaFrameInventory object with relic data
        """
        return self.get_relics_only()
    
    def get_relics_only(self) -> AlecaFrameInventory:
        """
        Fetch the relic inventory using the public token.
        
        Returns:
            AlecaFrameInventory object with relic data
        """
        inventory = AlecaFrameInventory(last_synced=datetime.now())
        
        if not self.api_token:
            inventory.error = "No API token configured. Go to AlecaFrame Stats tab → Create Public Link → Enable 'relics' → Generate token"
            return inventory
        
        # Fetch binary relic data
        # The relic inventory endpoint uses 'publicToken' as the parameter name
        data = self._make_request("/stats/public/getRelicInventory", binary=True, param_name="publicToken")
        
        if data is None:
            inventory.error = "Could not fetch relics. Make sure your token has 'relic' permission enabled."
            return inventory
        
        # Parse the binary data
        try:
            inventory.relics = self._parse_binary_relic_data(data)
        except Exception as e:
            inventory.error = f"Error parsing relic data: {e}"
            return inventory
        
        return inventory
    
    def get_profile(self) -> AlecaFrameProfile:
        """
        Fetch the user's profile data from AlecaFrame.
        
        Returns:
            AlecaFrameProfile object with user stats
        """
        profile = AlecaFrameProfile()
        
        if not self.api_token:
            profile.error = "No API token configured"
            return profile
        
        # Use the public stats endpoint
        data = self._make_request("/stats/public", binary=False, param_name="token")
        
        if data is None:
            profile.error = "Could not fetch profile data"
            return profile
        
        try:
            # Get username
            profile.username = data.get('usernameWhenPublic')
            
            # Get the latest data point from generalDataPoints
            data_points = data.get('generalDataPoints', [])
            if data_points:
                # Get the most recent data point (last in list)
                latest = data_points[-1]
                profile.mastery_rank = latest.get('mr', 0)
                profile.mastery_percentage = latest.get('percentageCompletion', 0)
                profile.platinum = latest.get('plat', 0)
                profile.credits = latest.get('credits', 0)
                profile.endo = latest.get('endo', 0)
                profile.ducats = latest.get('ducats', 0)
                profile.aya = latest.get('aya', 0)
                profile.relics_opened = latest.get('relicOpened', 0)
                profile.trades = latest.get('trades', 0)
                
                # Parse timestamp
                ts = latest.get('ts')
                if ts:
                    try:
                        profile.last_update = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    except:
                        pass
            
            # Also check lastUpdate from root
            if not profile.last_update:
                last_update = data.get('lastUpdate')
                if last_update:
                    try:
                        profile.last_update = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                    except:
                        pass
                        
        except Exception as e:
            profile.error = f"Error parsing profile data: {e}"
        
        return profile
    
    def _parse_binary_relic_data(self, data: bytes) -> list[AlecaFrameRelic]:
        """
        Parse the binary relic data format from AlecaFrame.
        
        The API returns base64-encoded binary data as a JSON string.
        
        Binary Format (little endian):
        - Uint32: Number of relics
        - For each relic (9 bytes):
            - Uint8: Relic type (0=Lith, 1=Meso, 2=Neo, 3=Axi, 4=Requiem)
            - Uint8: Refinement (0=Intact, 1=Exceptional, 2=Flawless, 3=Radiant)
            - char[3]: Name (e.g., "L1", "B21")
            - Uint32: Quantity
        """
        relics = []
        
        # Debug output
        print(f"AlecaFrame: Received {len(data)} bytes of data")
        
        # Check if data is a JSON string containing base64
        # The response comes as a base64 string wrapped in JSON quotes
        try:
            # First try to decode as JSON string (removes the surrounding quotes)
            decoded_str = data.decode('utf-8').strip()
            if decoded_str.startswith('"') and decoded_str.endswith('"'):
                # It's a JSON string, parse it
                decoded_str = json.loads(decoded_str)
            
            # Now decode the base64
            binary_data = base64.b64decode(decoded_str)
            print(f"AlecaFrame: Decoded base64 to {len(binary_data)} bytes")
            data = binary_data
        except Exception as e:
            print(f"AlecaFrame: Data is not base64-encoded JSON, treating as raw binary: {e}")
        
        if len(data) < 4:
            print(f"AlecaFrame: Data too short ({len(data)} bytes), expected at least 4")
            return relics
        
        # Read number of relics
        num_relics = struct.unpack('<I', data[0:4])[0]
        print(f"AlecaFrame: Header says {num_relics} relics")
        offset = 4
        
        for _ in range(num_relics):
            if offset + 9 > len(data):
                break
            
            # Read relic type (era)
            era_id = struct.unpack('<B', data[offset:offset+1])[0]
            era = self.ERA_MAP.get(era_id, "Unknown")
            offset += 1
            
            # Read refinement
            ref_id = struct.unpack('<B', data[offset:offset+1])[0]
            refinement = self.REFINEMENT_MAP.get(ref_id, "Intact")
            offset += 1
            
            # Read name (3 chars)
            name_bytes = data[offset:offset+3]
            # Strip null bytes and decode
            name = name_bytes.rstrip(b'\x00').decode('ascii', errors='ignore').strip()
            offset += 3
            
            # Read quantity
            quantity = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            
            if era != "Unknown" and name and quantity > 0:
                relics.append(AlecaFrameRelic(
                    name=f"{era} {name}",
                    era=era,
                    identifier=name,
                    refinement=refinement,
                    quantity=quantity,
                    vaulted=False  # We don't have this info from the API
                ))
        
        return relics
    
    def get_inventory_async(self, callback: Callable[[AlecaFrameInventory], None]):
        """
        Fetch inventory asynchronously.
        
        Args:
            callback: Function to call with the result
        """
        def fetch():
            result = self.get_inventory()
            callback(result)
        
        thread = threading.Thread(target=fetch, daemon=True)
        thread.start()
