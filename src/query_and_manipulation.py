from src.data_loader import load_markets
from src.models.mint_market import Market
from datetime import datetime
import pandas as pd
import requests
from datetime import timedelta
from scipy import stats
import numpy as np
import os
from functools import lru_cache
import time

# Current unix timestamp (as integer)
now = int(datetime.now().timestamp())
six_months_ago = int(now - 180*24*60*60)


@lru_cache
def get_market_snapshots(market_obj: Market, 
                         chain: str = "ethereum") -> pd.DataFrame:
    """
    Fetch historical snapshots for a specific crvUSD market
    
    Parameters:
    -----------
    market_obj : Market
        The market address to fetch snapshots for
    chain : str
        The blockchain network (default: "ethereum")
    agg : str
        Aggregation period - 'day' or 'hour' (default: "day")
    """
    market_address = market_obj.controller
    
    url = f"https://prices.curve.fi/v1/crvusd/markets/{chain}/{market_address}/snapshots"
    params = {
        "fetch_on_chain": "false",
        "agg": "day"
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    # Convert to DataFrame
    df = pd.DataFrame(response.json()['data'])
    
    # Process DataFrame
    if not df.empty:
        # Convert timestamp to datetime
        df['dt'] = pd.to_datetime(df['dt'])
        df.set_index('dt', inplace=True)
        
        # Convert scientific notation columns to float
        scientific_columns = ['loan_discount', 'liquidation_discount']
        for col in scientific_columns:
            if col in df.columns:
                df[col] = df[col].astype(float)
        
        # Sort by date ascending
        df.sort_index(inplace=True)
    
    df["cr_ratio"] = df["total_collateral_usd"] / df["total_debt"]
    # 30day avg cr_ratio
    df["cr_ratio_30d"] = df["cr_ratio"].rolling(30).mean()
    # 7day ema cr_ratio
    df["cr_ratio_7d"] = df["cr_ratio"].rolling(7).mean()

    df["cr_7d/30d"] = df["cr_ratio_7d"] / df["cr_ratio_30d"]
    
    return df

def get_latest_cr_ratio_row(market_obj: Market, chain: str = "ethereum") -> dict:
    """
    Get the latest market metrics comparison
    
    Parameters:
    -----------
    market_obj : Market
        The market object to fetch data for
    chain : str
        The blockchain network (default: "ethereum")
        
    Returns:
    --------
    dict
        Latest market metrics including:
        - cr_ratio: Current collateral ratio
        - cr_ratio_7d: 7-day moving average of collateral ratio
        - cr_ratio_30d: 30-day moving average of collateral ratio
        - cr_7d/30d: Ratio of 7-day to 30-day averages
    """
    df = get_market_snapshots(market_obj, chain)
    if df.empty:
        return {
            "cr_ratio": 0.0,
            "cr_ratio_7d": 0.0,
            "cr_ratio_30d": 0.0,
            "cr_7d/30d": 0.0
        }
    
    latest_data = df.iloc[-1].to_dict()
    return {
        "cr_ratio": latest_data["cr_ratio"],
        "cr_ratio_7d": latest_data["cr_ratio_7d"],
        "cr_ratio_30d": latest_data["cr_ratio_30d"],
        "cr_7d/30d": latest_data["cr_7d/30d"]
    }

@lru_cache
def get_market_health(market_obj: Market, 
                      chain: str = "ethereum") -> pd.DataFrame:
    """
    Fetch historical snapshots for a specific crvUSD market
    
    Parameters:
    -----------
    market_obj : Market
        The market address to fetch snapshots for
    chain : str
        The blockchain network (default: "ethereum")
    agg : str
        Aggregation period - 'day' or 'hour' (default: "day")
    """
    market_address = market_obj.controller
    url = f"https://prices.curve.fi/v1/crvusd/liquidations/{chain}/{market_address}/overview"
    params = {
        "fetch_on_chain": "false"
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.json()




@lru_cache
def defillama_price(market_obj: Market, query_time_from: int = six_months_ago, chain: str = "ethereum"):
    """
    Fetch price data from DefiLlama API for a given market's collateral token
    
    Parameters:
    -----------
    token_address : str
        The token address to fetch prices for
    chain : str
        The blockchain network (default: "ethereum")
        
    Returns:
    --------
    pd.DataFrame
        DataFrame containing timestamp and price data
    """
    token_address = market_obj.token
    
    current_timestamp = int(datetime.now().timestamp())
    last_round_ts = query_time_from
    price_data_join = []
    
    while last_round_ts + 4000 < current_timestamp:
        url = f"https://coins.llama.fi/chart/{chain}:{token_address}"
                
        params = {
            "start": last_round_ts,
            "span": 500,
            "period": "1h"  # hourly data
        }
        
        response = requests.get(url, params)
                
        # Extract price data from response
        price_data = response.json()["coins"][f"{chain}:{token_address}"]["prices"]
        
        # Update timestamp for next iteration
        last_round_ts = price_data[-1]["timestamp"]
        
        # Append price_data into price_data_join
        price_data_join.extend(price_data)
        
        # Add a small delay to avoid rate limiting
        time.sleep(0.5)
    
    # Convert combined data to DataFrame
    df = pd.DataFrame(price_data_join)
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    
    # Remove any duplicates that might have occurred at chunk boundaries
    df = df.drop_duplicates(subset='timestamp')
    
    # Sort by timestamp
    df = df.sort_values('timestamp')
    
    return df

def create_daily_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert hourly price data into daily OHLC (Open, High, Low, Close) data
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with 'timestamp' and 'price' columns containing hourly data
        
    Returns:
    --------
    pd.DataFrame
        DataFrame with daily OHLC data
    """
    # Set timestamp as index if it's not already
    if 'timestamp' in df.columns:
        df = df.set_index('timestamp')
    
    # Resample to daily frequency and calculate OHLC
    daily_ohlc = pd.DataFrame({
        'open': df['price'].resample('D').first(),
        'high': df['price'].resample('D').max(),
        'low': df['price'].resample('D').min(),
        'close': df['price'].resample('D').last()
    })
    
    return daily_ohlc


# @lru_cache
def get_ohlc(market_obj: Market, chain: str = "ethereum") -> pd.DataFrame:
    """
    Get OHLC price data for a market, using cached CSV data when available
    and fetching only missing data from DefiLlama
    
    Parameters:
    -----------
    market_obj : Market
        Market object containing token information
    chain : str
        Blockchain network (default: "ethereum")
        
    Returns:
    --------
    pd.DataFrame
        DataFrame with daily OHLC price data
    """
    # Directly use relative path to data directory
    csv_path = f"src/data/{market_obj.market}_ohlc.csv"
    
    if os.path.exists(csv_path):
        # Load existing data
        df_existing = pd.read_csv(csv_path)
        df_existing.set_index('timestamp', inplace=True)
        df_existing.index = pd.to_datetime(df_existing.index)
        
        # Check if we need to fetch new data
        current_date = pd.Timestamp.now()
        last_date = df_existing.index.max()
        
        if (current_date - last_date).days > 1:
            # Calculate the timestamp to fetch from
            query_time_from = int(last_date.timestamp())
            
            # Fetch only missing data
            df_new = defillama_price(market_obj, query_time_from, chain)
            df_new = df_new[df_new['timestamp'] > last_date]
            
            if not df_new.empty:
                # Convert new data to OHLC
                df_new_ohlc = create_daily_ohlc(df_new)
                
                # Combine old and new data
                df_combined = pd.concat([df_existing, df_new_ohlc])
                df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
                df_combined = df_combined.sort_index()
                
                # Save updated data
                df_combined.to_csv(csv_path)
                return df_combined
            
            return df_existing
        return df_existing
    else:
        # No existing data, fetch all
        df = defillama_price(market_obj, six_months_ago, chain)
        df_ohlc = create_daily_ohlc(df)
        
        # Save to CSV
        df_ohlc.to_csv(csv_path)
        return df_ohlc
    
    # # Gives the last 180 days of OHLC data
    
    # market_address = market_obj.amm
    
    # # url = f"https://prices.curve.fi/v1/crvusd/llamma_ohlc/{chain}/{market_address}"
    # # params = {
    # #     "agg_number": 1,
    # #     "agg_units": "day",
    # #     "start": six_months_ago,
    # #     "end": now
    # # }
    
    # url = f"https://prices.curve.fi/v1/crvusd/llamma_ohlc/{chain}/{market_address}"
    # params = {
    #     "agg_number": 1,
    #     "agg_units": "day",
    #     "start": six_months_ago,
    #     "end": now
    # }

    # response = requests.get(url, params)
    # response.raise_for_status()
    
    # # Convert to DataFrame
    # data = response.json()['data']
    
    # # Convert timestamp to datetime
    # df = pd.DataFrame(data)
    
    # # Convert timestamp to datetime and set as index
    # df['time'] = pd.to_datetime(df['time'], unit='s')
    # df = df.set_index('time')
    
    return df


def gk_volatility(df):
    """
    Calculate Garman-Klass volatility with proper error handling
    """
    log_hl = np.log(df['high'] / df['low'])
    log_co = np.log(df['close'] / df['open'])
    
    # Calculate variance
    variance = (0.5 * log_hl.pow(2) - (2 * np.log(2) - 1) * log_co.pow(2)).mean()
    
    # Handle negative variance
    if variance <= 0:
        return np.nan
        
    return np.sqrt(variance)

    

def calculate_recent_gk_beta(asset_df: pd.DataFrame, 
                             btc_df: pd.DataFrame) -> float:
    """
    Calculate a single Garman-Klass beta value using the most recent days of data
    
    Parameters:
    -----------
    asset_df : pd.DataFrame
        DataFrame with asset OHLC data
    index_df : pd.DataFrame
        DataFrame with index OHLC data
    days : int
        Number of recent days to consider (default: 30)
        
    Returns:
    --------
    float
        Single GK beta value for the period
    """
        
    # Calculate returns for correlation
    asset_returns = np.log(asset_df['close'] / asset_df['close'].shift(1))
    btc_returns = np.log(btc_df['close'] / btc_df['close'].shift(1))
    
    # Calculate correlation
    correlation = asset_returns.corr(btc_returns)
    
    # Calculate volatilities
    asset_gk_vol = gk_volatility(asset_df)
    btc_gk_vol = gk_volatility(btc_df)
    
    # Calculate GK beta
    gk_beta = correlation * (asset_gk_vol / btc_gk_vol)
    
    return gk_beta



def analyze_price_drops(market_obj: Market, 
                        btc_market: Market, 
                        drop_thresholds=[0.075, 0.15]) -> dict:
    """
    Calculate probability of price drops using Garman-Klass volatility estimator
    
    Args:
        gc_id: CoinGecko ID for the asset
        drop_thresholds: List of drop thresholds as decimals (e.g., 0.075 for 7.5% drop)
        
    Returns:
        dict: Probabilities for each threshold
    """
    ohlc_df = get_ohlc(market_obj) # 6 months of OHLC data
    btc_ohlc_df = get_ohlc(btc_market) # 6 months of OHLC data
           
    # Calculate daily returns using all OHLC data
    daily_returns = (ohlc_df['close'] - ohlc_df['open']) / ohlc_df['open']
    
    # Calculate true range based returns for better volatility estimation
    true_range_pct = (ohlc_df['high'] - ohlc_df['low']) / ohlc_df['open']
    
    # Combine both metrics for a more complete picture
    all_returns = pd.concat([daily_returns, true_range_pct])
    
    
    # Remove outliers beyond 5 standard deviations
    returns_mean = all_returns.mean()
    returns_std = all_returns.std()
    clean_returns = all_returns[np.abs(all_returns - returns_mean) <= (5 * returns_std)]
    
    # Fit a t-distribution (better for crypto's fat tails)
    params = stats.t.fit(clean_returns)
    df, loc, scale = params
    
    probabilities = {}
    for index, threshold in enumerate(drop_thresholds):
        # Calculate probability of a drop greater than the threshold
        prob_parametric = stats.t.cdf(-threshold, df, loc, scale)
        
        # Calculate historical probability
        prob_historical = len(daily_returns[daily_returns <= -threshold]) / len(daily_returns)
        
        probabilities[f"drop{index+1}"] = {
            'parametric_probability': float(prob_parametric),
            'historical_probability': float(prob_historical),
            'threshold_pct': float(threshold * 100)
        }
        
    beta = calculate_recent_gk_beta(ohlc_df, btc_ohlc_df)
    
    return probabilities, beta

def calculate_volatility_ratio(market_obj: Market) -> tuple[float, float, float]:
    """
    Calculate volatility ratio using 15-day and 60-day rolling windows
    
    Args:
        market_obj: Market object containing contract addresses
        
    Returns:
        tuple: (15-day volatility, 60-day volatility, ratio of 15d/60d)
    """
    ohlc_df = get_ohlc(market_obj)
    
    log_hl = np.log(ohlc_df['high'] / ohlc_df['low'])
    log_co = np.log(ohlc_df['close'] / ohlc_df['open'])
    
    # Calculate rolling components for both windows
    hl_90d = log_hl.pow(2).rolling(window=90).mean()
    co_90d = log_co.pow(2).rolling(window=90).mean()
    
    # print(f"HL 90d: {hl_90d}")    
    # print(f"CO 90d: {co_90d}")
    
    hl_30d = log_hl.pow(2).rolling(window=30).mean()
    co_30d = log_co.pow(2).rolling(window=30).mean()
    
    # print(f"HL 30d: {hl_30d}")
    # print(f"CO 30d: {co_30d}")
    
    # Calculate variances for the last point in each window
    variance_90d = (0.5 * hl_90d - (2 * np.log(2) - 1) * co_90d).iloc[-1]
    variance_30d = (0.5 * hl_30d - (2 * np.log(2) - 1) * co_30d).iloc[-1]
    
    # print(f"Variance 90d: {variance_90d}")
    # print(f"Variance 30d: {variance_30d}")
    
    
    # Convert to daily volatility
    vol_90d = np.sqrt(max(variance_90d, 0))
    vol_30d = np.sqrt(max(variance_30d, 0))
    
    # Calculate ratio (handle division by zero)
    ratio = vol_30d / vol_90d if vol_90d != 0 else 1.0
    
    return vol_30d, vol_90d, ratio

def get_soft_liquidation_ratio(market_obj: Market, 
                               chain: str = "ethereum") -> pd.DataFrame:
    
    controller = market_obj.controller
    
    url = f"https://prices.curve.fi/v1/crvusd/liquidations/{chain}/{controller}/soft_liquidation_ratio"
    params = {
        "start": six_months_ago,
        "end": now
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    # Convert to DataFrame
    data = response.json()['data']
    
    # Convert timestamp to datetime
    df = pd.DataFrame(data)
    
    # Sort chronologically first
    df = df.sort_values('timestamp')

    # Parse the timestamp column correctly
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%dT%H:%M:%S')
    
    df["debt_under_sl_ratio_7d"] = df["debt_under_sl_ratio"].rolling(7).mean()
    df["debt_under_sl_ratio_30d"] = df["debt_under_sl_ratio"].rolling(30).mean()
    
    df["collateral_under_sl_ratio_7d"] = df["collateral_under_sl_ratio"].rolling(7).mean()
    df["collateral_under_sl_ratio_30d"] = df["collateral_under_sl_ratio"].rolling(30).mean()
    
    df.set_index('timestamp', inplace=True)
    
    return df

def get_under_sl_ratios(market_obj: Market, 
                        chain: str = "ethereum") -> tuple[float, float]:
    
    df = get_soft_liquidation_ratio(market_obj, chain)
    
    latest_row = df.iloc[-1].to_dict()
    
    current_collateral_under_sl_ratio = latest_row["collateral_under_sl_ratio"]
    
    # Handle division by zero case
    if latest_row["collateral_under_sl_ratio_30d"] == 0:
        relative_collateral_under_sl_ratio = 1.0  # Default value when denominator is zero
    else:
        relative_collateral_under_sl_ratio = latest_row["collateral_under_sl_ratio_7d"] / latest_row["collateral_under_sl_ratio_30d"]
    
    return current_collateral_under_sl_ratio, relative_collateral_under_sl_ratio