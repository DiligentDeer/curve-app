import pandas as pd
from src.models.mint_market import Market
from typing import List
from src.data import objects_path

def load_markets() -> dict[str, Market]:
    """
    Load market data from CSV and return dictionary of Market objects
    
    Returns:
        dict[str, Market]: Dictionary with market names as keys and Market objects as values
    """
    df = pd.read_csv(objects_path)
    
    markets = {}
    for _, row in df.iterrows():
        market = Market(
            market=row['market'],
            token=row['token'],
            amm=row['amm'],
            controller=row['controller'],
            policy=row['policy'],
            A=row['amp'],
            liq_discount=row['liq_discount'],
            gc_id=row['gc_id']
        )
        markets[row['market']] = market
        
    return markets
