import streamlit as st

def display_market_info(market_obj, status_data: dict):
    """
    Display market information in a 4-column grid layout
    
    Args:
        market_obj (Market): Market object containing contract addresses
        status_data (dict): Market status data from API
    """
    if not status_data:
        st.warning("No market status data available")
        return
        
    # Addresses and Tokens
    st.subheader("Market Information")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.write("**Controller Address**")
        st.code(market_obj.controller)
    with col2:
        st.write("**AMM Address**")
        st.code(market_obj.amm)
    with col3:
        st.write("**Collateral Token**")
        st.code(status_data['collateral_token']['address'])
    with col4:
        st.write("**Stablecoin Token**")
        st.code(status_data['stablecoin_token']['address'])
    
    # Market Metrics
    st.subheader("Market Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    # Calculate utilization and collateral ratio
    utilization = status_data['total_debt'] / (status_data['total_debt'] + status_data['borrowable']) * 100
    collateral_ratio = status_data['collateral_amount_usd'] / status_data['total_debt'] * 100 if status_data['total_debt'] > 0 else 0
    
    with col1:
        st.metric("Total Debt", f"${status_data['total_debt']:,.2f}")
    with col2:
        st.metric("Borrowable", f"${status_data['borrowable']:,.2f}")
    with col3:
        st.metric("Utilization", f"{utilization:.2f}%")
    with col4:
        st.metric("Number of Loans", status_data['n_loans'])
        
    # Collateral Metrics
    st.subheader("Collateral Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Collateral Amount", f"{status_data['collateral_amount']:,.4f}")
    with col2:
        st.metric("Stablecoin Amount", f"${status_data['stablecoin_amount']:,.2f}")
    with col3:
        st.metric("Collateral Value (USD)", f"${status_data['collateral_amount_usd']:,.2f}")
    with col4:
        st.metric("Collateral Ratio", f"{collateral_ratio:.2f}%")