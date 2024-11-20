from dataclasses import dataclass, field
import requests
from functools import lru_cache



@dataclass(frozen=True)  # Making the dataclass immutable
class Market:
    market: str
    token: str
    amm: str
    controller: str
    policy: str
    A: int
    liq_discount: float
    gc_id: str
    max_ltv: float = field(init=False)
    min_ltv: float = field(init=False)
    
    def __post_init__(self):
        object.__setattr__(self, 'max_ltv', 1 - self.liq_discount - (2/self.A))
        object.__setattr__(self, 'min_ltv', 1 - self.liq_discount - (25/self.A))
    
    def __hash__(self):
        return hash(self.controller.lower())
    
    def __eq__(self, other):
        if not isinstance(other, Market):
            return NotImplemented
        return self.controller.lower() == other.controller.lower()
        
    
    @staticmethod
    @lru_cache(maxsize=32)
    def get_active_markets(chain: str) -> list[dict]:
        """
        Get all active markets from the Curve API
        
        Args:
            chain (str): Chain name (e.g., 'ethereum')
            
        Returns:
            list[dict]: List of market data dictionaries
        """
        endpoint = f"https://prices.curve.fi/v1/crvusd/markets/{chain}?fetch_on_chain=true&page=1&per_page=10"
        response = requests.get(endpoint)
        raw_data = response.json()
        return raw_data["data"]
    
    def get_market_status(self, chain: str = "ethereum") -> dict:
        """
        Get status for this specific market
        
        Args:
            chain (str): Chain name (e.g., 'ethereum')
            
        Returns:
            dict: Market status data or None if not found
        """
        data = self.get_active_markets(chain)
        
        for market in data:
            if market['address'].lower() == self.controller.lower():
                return market
        return None

