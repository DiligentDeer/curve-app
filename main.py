import streamlit as st
from src.data_loader import load_markets
from src.visualization import display_market_info
from src.query_and_manipulation import get_latest_cr_ratio_row, get_market_health, analyze_price_drops, calculate_volatility_ratio, get_under_sl_ratios
from src.scoring import score_with_limits, score_bad_debt, score_debt_ceiling
import json
import numpy as np
import os
from PIL import Image

markets = load_markets()

# Set page to wide mode
st.set_page_config(layout="wide")


def show_changelog():
    st.title("Changelog")
    
    st.markdown("""
    ### Version 2.0.0 (2024-11-23)
    - Fixed debt ceiling scoring calculation bug
    - Restructured weights into tiered system:
        - Tier 1 (Critical): Debt Ceiling, Market Bad Debt (13% each)
        - Tier 2 (Core): Volatility, CR, SL Ratio (10% each)
        - Tier 3 (Secondary): Price Drop, Arb Profit, SL Response, Borrower Conc. (8% each)
        - Tier 4 (Interdependency): Momentum, Volatility (6% each)
    - Added interactive playground for score/weight simulations
    
    ### Version 1.5.1 (2024-11-22)
    - Change log added
    
    ### Version 1.5.0 (2024-11-19)
    - Initial release
    - Implemented market health scoring system
    - Added scoring breakdowns as:
        - Bad Debt Weight: 6%
        - Debt Ceiling Weight: 9.5%
        - Price Drop Weight: 9.5%
        - Volatility & Beta Weight: 9.5%
        - Collateral Ratio Weight: 9.5%
        - Collateral Under SL Weight: 9.5%
        - Borrower Distribution Weight: 9.5%
        - SL Responsiveness Weight: 9.5%
        - SL Profitability Weight: 9.5%
        
    ### Version 1.0.0 (2024-11-04)
    - Research phase
    - V1 Methodolody: Notebook available [here](https://hackmd.io/@diligentdeer/curvePortal)
    """)

    

def main():
    
    # Load LlamaRisk logo
    logo_path = "./LR_logo_light.png"
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
    else:
        logo = None

    st.image(logo, width=200)
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Dashboard", "Playground", "Changelog"])

    with tab1:
        st.title("crvUSD Mint Market Data & Score")
    
        # Create dropdown with market names
        market_names = list(markets.keys())
        selected_market = st.selectbox(
            "Select a market",
            market_names
        )
        
        # Display market data when selected
        if selected_market:
            market_obj = markets[selected_market]
            status = market_obj.get_market_status("ethereum")
            health = get_market_health(market_obj)
            
            # # Get input for debt ceiling
            # recommended_debt_ceiling = st.number_input("Recommended Debt Ceiling", value=status["borrowable"] + status["total_debt"])
            
            
            # Display market info
            display_market_info(market_obj, status)
            
            
            ########## Calculate and display market score ##########
            
            
            ########## Collateral Ratio Score ##########
            
            cr_comparison = get_latest_cr_ratio_row(market_obj)
            
            # print(json.dumps(cr_comparison, indent=4))
            # print(1/cr_comparison["cr_ratio"])
            # print(f"max_ltv: {0.75*market_obj.max_ltv}")
            # print(f"min_ltv: {0.75*market_obj.min_ltv}")
            
            relative_cr_score = score_with_limits(cr_comparison["cr_7d/30d"],1.1,0.9,True)
            
            absolute_cr_score = score_with_limits(1/cr_comparison["cr_ratio"],0.75*market_obj.max_ltv,0.75*market_obj.min_ltv,False)
            
            aggregate_cr_score = (0.4*relative_cr_score + 0.6*absolute_cr_score)
            
            ########## Bad Debt Score ##########
            
            bad_debt_score = score_bad_debt(health["bad_debt"], status["total_debt"])
            
            ########## Debt Ceiling Score ##########
            
            # debt_ceiling_score = score_debt_ceiling(recommended_debt_ceiling, status["borrowable"] + status["total_debt"], status["total_debt"])
            
            ########## Price Drop & Beta Score ##########
            
            probabilities, beta = analyze_price_drops(market_obj,markets["WBTC"],[0.075, 0.15])
            
            # print(f"Beta: {beta}")
            
            beta_score = score_with_limits(beta,2.5,0.5,False,1)
            
            prob_drop1 = probabilities[f"drop1"]['parametric_probability']
            prob_drop2 = probabilities[f"drop2"]['parametric_probability']
            
            # print(f"Prob Drop 1: {prob_drop1}")
            # print(f"Prob Drop 2: {prob_drop2}")
            
            prob_drop1_score = score_with_limits(prob_drop1,0.03,0,False)
            prob_drop2_score = score_with_limits(prob_drop2,0.0075,0,False)
            
            aggregate_prob_drop_score = (0.5*prob_drop1_score + 0.5*prob_drop2_score)
            
            ########## Volatility Ratio Score ##########
            
            vol_45d, vol_180d, vol_ratio = calculate_volatility_ratio(market_obj)
            
            # print(f"Vol 45d: {vol_45d}")
            # print(f"Vol 180d: {vol_180d}")
            # print(f"Vol Ratio: {vol_ratio}")
            
            vol_ratio_score = score_with_limits(vol_ratio,1.5,0.75,False)
            
            aggregate_vol_ratio_score = (0.4*vol_ratio_score + 0.6*beta_score)
            
            
            ########## Under SL Ratio Score ##########
            
            current_collateral_under_sl_ratio, relative_collateral_under_sl_ratio = get_under_sl_ratios(market_obj)
            
            # print(f"Current Collateral Under SL Ratio: {current_collateral_under_sl_ratio}")
            # print(f"Relative Collateral Under SL Ratio: {relative_collateral_under_sl_ratio}")
            
            collateral_under_sl_score = score_with_limits(current_collateral_under_sl_ratio, 2, 0, False)
            
            # print(f"Collateral Under SL Score: {collateral_under_sl_score}")
            
            relative_collateral_under_sl_score = score_with_limits(relative_collateral_under_sl_ratio, 2.5, 0.5, False,1)
            
            # print(f"Relative Collateral Under SL Score: {relative_collateral_under_sl_score}")
            
            aggregate_collateral_under_sl_score = (0.4*collateral_under_sl_score + 0.6*relative_collateral_under_sl_score)
            
            st.divider()
            
            st.subheader("Market Health Score - Collateral Ratio")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "CR Ratio Score", 
                    f"{relative_cr_score:.2%}",
                    help="Score based on 7-day vs 30-day collateral ratio comparison"
                )
                st.caption(f"7d/30d CR ratio = {cr_comparison['cr_7d/30d']:.2f}. Scored between 0.9 (min) and 1.1 (max), higher is better.")
            with col2:
                st.metric(
                    "Absolute CR Score", 
                    f"{absolute_cr_score:.2%}",
                    help="Score based on current collateral ratio"
                )
                st.caption(f"Current LTV = {1/cr_comparison['cr_ratio']:.2%}. Scored between 75% of min LTV possible (min) (CR ~{1/(0.75*market_obj.min_ltv):.2f}, LTV ~{0.75*market_obj.min_ltv}) and 75% of max LTV possible (max) (CR ~{1/(0.75*market_obj.max_ltv):.2f}, LTV ~{0.75*market_obj.max_ltv}), lower is better.")
            with col3:
                st.metric(
                    "Final CR Score", 
                    f"{aggregate_cr_score:.2%}",
                    help="Score based on relative and absolute CR scores"
                )
                st.caption("Weighted average: 40% relative score + 60% absolute score.")
            with col4:
                st.metric(
                    "Final CR Score", 
                    f"{aggregate_cr_score:.2%}",
                    help="Score based on relative and absolute CR scores"
                )
                st.progress(aggregate_cr_score)
                

            st.subheader("Market Health Score - Bad Debt")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "Bad Debt Score", 
                    f"{bad_debt_score:.2%}",
                    help="Score based on current bad debt"
                )
                st.caption(f"Linear scoring. Bad debt ratio = {health['bad_debt']/status['total_debt']:.2%}. Perfect score (100%) if zero bad debt, 50% score if bad debt is 0.1% of total debt, 0% score if bad debt exceeds 1% of total debt.")
            with col4:
                st.metric(
                    "Final Bad Debt Score", 
                    f"{bad_debt_score:.2%}",
                    help="Score based on current bad debt"
                )
                st.progress(bad_debt_score)
                
        
            st.subheader("Market Health Score - Debt Ceiling")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                # Get input for debt ceiling
                recommended_debt_ceiling = st.number_input("Recommended Debt Ceiling", value=status["borrowable"] + status["total_debt"])
                debt_ceiling_score = score_debt_ceiling(recommended_debt_ceiling, status["borrowable"] + status["total_debt"], status["total_debt"])
            
                st.metric(
                    "Debt Ceiling Score", 
                    f"{debt_ceiling_score:.2%}",
                    help="Score based on current debt ceiling"
                )
                st.caption(f"Linear scoring. Current ceiling = {status['borrowable'] + status['total_debt']:,.0f}, recommended = {recommended_debt_ceiling:,.0f}. Perfect score (100%) if current ≤ recommended, 50% score if current debt ≤ recommended but ceiling > recommended, 0% score if current debt > recommended.")
            with col4:
                st.metric(
                    "Final Debt Ceiling Score", 
                    f"{debt_ceiling_score:.2%}",
                    help="Score based on current debt ceiling"
                )
                st.progress(debt_ceiling_score)
                
                
            st.subheader("Market Health Score - Price Drop")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "Price Drop 7.5%", 
                    f"{prob_drop1_score:.2%}",
                    help=f"Score based on current price drop probability of 7.5% drop = {prob_drop1:.2%}"
                )
                st.caption(f"Probability = {prob_drop1:.2%}. Scored between 0% (min) and 3% (max) probability, lower is better.")
            with col2:
                st.metric(
                    "Price Drop 15%", 
                    f"{prob_drop2_score:.2%}",
                    help=f"Score based on current price drop probability of 15% drop = {prob_drop2:.2%}"
                )
                st.caption(f"Probability = {prob_drop2:.2%}. Scored between 0% (min) and 0.75% (max) probability, lower is better.")
            with col3:
                st.metric(
                    "Final Price Drop Score", 
                    f"{aggregate_prob_drop_score:.2%}",
                    help="Score based on current price drop probabilities"
                )
                st.caption("Equal weight average of both drop probability scores.")
            with col4:
                st.metric(
                    "Final Price Drop Score", 
                    f"{aggregate_prob_drop_score:.2%}",
                    help="Score based on current price drop probabilities"
                )
                st.progress(aggregate_prob_drop_score)
        

            st.subheader("Market Health Score - Beta")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "Beta", 
                    f"{beta_score:.2%}",
                    help=f"Score based on current beta = {beta:.2}"
                )
                st.caption(f"Beta = {beta:.2f}. Scored between 0.5 (min) and 2.5 (max), lower is better.")
            with col2:
                st.metric(
                    "Volatility Ratio", 
                    f"{vol_ratio_score:.2%}",
                    help=f"Score based on current volatility ratio = {vol_ratio:.2}"
                )
                st.caption(f"30d/90d vol ratio = {vol_ratio:.2f}. Scored between 0.75 (min) and 1.5 (max), lower is better.")
            with col3:
                st.metric(
                    "Final Volatility Ratio Score", 
                    f"{aggregate_vol_ratio_score:.2%}",
                    help="Score based on current volatility ratio and beta"
                )
                st.caption("Weighted average: 40% volatility ratio + 60% beta score.")
            with col4:
                st.metric(
                    "Final Volatility Score", 
                    f"{aggregate_vol_ratio_score:.2%}",
                    help="Score based on current volatility ratio and beta"
                )
                st.progress(aggregate_vol_ratio_score)


            st.subheader("Market Health Score - Collateral Under SL")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "Collateral Under SL Score", 
                    f"{collateral_under_sl_score:.2%}",
                    help=f"Score based on current collateral under SL ratio = {current_collateral_under_sl_ratio:.2}"
                )
                st.caption(f"Current ratio = {current_collateral_under_sl_ratio:.2f}. Scored between 0 (min) and 2 (max), lower is better.")
            with col2:
                st.metric(
                    "Relative Collateral Under SL Score", 
                    f"{relative_collateral_under_sl_score:.2%}",
                    help=f"Score based on current relative collateral under SL ratio = {relative_collateral_under_sl_ratio:.2}"
                )
                st.caption(f"7d/30d ratio = {relative_collateral_under_sl_ratio:.2f}. Scored between 0.5 (min) and 2.5 (max), lower is better.")
            with col3:
                st.metric(
                    "Final Collateral Under SL Score", 
                    f"{aggregate_collateral_under_sl_score:.2%}",
                    help=f"Score based on current collateral under SL ratio and relative collateral under SL ratio"
                )
                st.caption("Weighted average: 40% current ratio + 60% relative ratio score.")
            with col4:
                st.metric(
                    "Final Collateral Under SL Score", 
                    f"{aggregate_collateral_under_sl_score:.2%}",
                    help="Score based on current collateral under SL ratio and relative collateral under SL ratio"
                )
                st.progress(aggregate_collateral_under_sl_score)
        

            
            
            st.subheader("Market Health Score - Borrower Distribution")
            st.caption("WIP - Herfindahl–Hirschman index method. As a proxy, use the slider to input a score between 0% and 100%.")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                borrower_distribution_score = st.slider(
                    "Benchmark Comparison Score", 
                    min_value=0.0, 
                    max_value=1.0, 
                    value=0.5,
                    help="Score based on current borrower distribution (0-100%)",
                    key="current_dist"
                )
                st.metric(
                    "Benchmark Comparison Score", 
                    f"{borrower_distribution_score:.2%}",
                    help="Score based on current borrower distribution"
                )
                st.caption("Manual score input between 0% (min) and 100% (max).")
            with col2:
                relative_borrower_distribution_score = st.slider(
                    "Relative Comparison Score", 
                    min_value=0.0, 
                    max_value=1.0, 
                    value=0.5,
                    help="Score based on relative borrower distribution (0-100%)",
                    key="relative_dist"
                )
                st.metric(
                    "Relative Comparison Score", 
                    f"{relative_borrower_distribution_score:.2%}",
                    help="Score based on relative borrower distribution"
                )            
                st.caption("Manual score input between 0% (min) and 100% (max).")

            # Calculate aggregate score
            aggregate_borrower_distribution_score = (0.5 * borrower_distribution_score + 
                                                0.5 * relative_borrower_distribution_score)

            with col3:
                st.metric(
                    "Final Distribution Score", 
                    f"{aggregate_borrower_distribution_score:.2%}",
                    help="Score based on current and relative borrower distribution"
                )
                st.caption("Equal weight average of both distribution scores.")
            with col4:
                st.metric(
                    "Final Distribution Score", 
                    f"{aggregate_borrower_distribution_score:.2%}",
                    help="Score based on current and relative borrower distribution"
                )
                st.progress(aggregate_borrower_distribution_score)


            st.subheader("Market Health Score - Soft-Liquidation Responsiveness")
            st.caption("WIP - Measures how quickly positions get repaid after entering soft-liquidation. Use slider to input a score between 0% and 100%.")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                sl_responsiveness_score = st.slider(
                    "Responsiveness Score", 
                    min_value=0.0, 
                    max_value=1.0, 
                    value=0.5,
                    help="Score based on soft-liquidation responsiveness (0-100%)",
                    key="sl_resp"
                )
                st.metric(
                    "SL Responsiveness Score", 
                    f"{sl_responsiveness_score:.2%}",
                    help="Score based on soft-liquidation responsiveness"
                )
                st.caption("Manual score input between 0% (min) and 100% (max).")
            with col4:
                st.metric(
                    "Final SL Responsiveness Score", 
                    f"{sl_responsiveness_score:.2%}",
                    help="Score based on soft-liquidation responsiveness"
                )
                st.progress(sl_responsiveness_score)

            st.subheader("Market Health Score - Soft-Liquidation Profitability")
            st.caption("WIP - Measures the profitability of soft-liquidations for liquidators. Use slider to input a score between 0% and 100%.")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                sl_profitability_score = st.slider(
                    "Profitability Score", 
                    min_value=0.0, 
                    max_value=1.0, 
                    value=0.5,
                    help="Score based on soft-liquidation profitability (0-100%)",
                    key="sl_prof"
                )
                st.metric(
                    "SL Profitability Score", 
                    f"{sl_profitability_score:.2%}",
                    help="Score based on soft-liquidation profitability"
                )
                st.caption("Manual score input between 0% (min) and 100% (max).")
            with col4:
                st.metric(
                    "Final SL Profitability Score", 
                    f"{sl_profitability_score:.2%}",
                    help="Score based on soft-liquidation profitability"
                )
                st.progress(sl_profitability_score)


            # '''
            # # Market Health Score Components

            # 1. Collateral Ratio Score
            # - `aggregate_cr_score` = 0.4 * relative_cr_score + 0.6 * absolute_cr_score

            # 2. Bad Debt Score
            # - `bad_debt_score` (final score, no aggregation)

            # 3. Debt Ceiling Score
            # - `debt_ceiling_score` (final score, no aggregation)

            # 4. Price Drop Score
            # - `aggregate_prob_drop_score` = 0.5 * prob_drop1_score + 0.5 * prob_drop2_score

            # 5. Volatility & Beta Score
            # - `aggregate_vol_ratio_score` = 0.4 * vol_ratio_score + 0.6 * beta_score

            # 6. Collateral Under SL Score
            # - `aggregate_collateral_under_sl_score` = 0.4 * collateral_under_sl_score + 0.6 * relative_collateral_under_sl_score

            # 7. Borrower Distribution Score
            # - `aggregate_borrower_distribution_score` = 0.5 * borrower_distribution_score + 0.5 * relative_borrower_distribution_score

            # 8. Soft-Liquidation Responsiveness Score
            # - `sl_responsiveness_score` (final score, no aggregation)

            # 9. Soft-Liquidation Profitability Score
            # - `sl_profitability_score` (final score, no aggregation)
            # '''
            
            st.subheader("Market Health Score - Interdependency on Price Momentum")
            st.caption("Uses score from Price Drop Score, Debt Ceiling Score, Collateral Ratio Score, Borrower Distribution Score")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                interdependency_score_price_momentum = np.median([aggregate_prob_drop_score, debt_ceiling_score, aggregate_cr_score, aggregate_borrower_distribution_score])
                st.metric(
                    "Interdependency on Price Momentum", 
                    f"{interdependency_score_price_momentum:.2%}",
                    help="Score based on interdependency on price momentum"
                )
                st.caption("Minimum of Price Drop Score, Debt Ceiling Score, Collateral Ratio Score, Borrower Distribution Score.")
            with col4:
                st.metric(
                    "Final Interdependency on Price Momentum", 
                    f"{interdependency_score_price_momentum:.2%}",
                    help="Score based on interdependency on price momentum"
                )
                st.progress(interdependency_score_price_momentum)
            
            
            st.subheader("Market Health Score - Interdependency on Volatility")
            st.caption("Uses score from Volatility & Beta Score, Soft-Liquidation Responsiveness Score, Soft-Liquidation Profitability Score, Collateral Under SL Score, Borrower Distribution Score")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                interdependency_score_volatility = np.median([aggregate_vol_ratio_score, sl_responsiveness_score, sl_profitability_score, aggregate_collateral_under_sl_score, aggregate_borrower_distribution_score])
                st.metric(
                    "Interdependency on Volatility", 
                    f"{interdependency_score_volatility:.2%}",
                    help="Score based on interdependency on volatility"
                )
                st.caption("Minimum of Volatility & Beta Score, Soft-Liquidation Responsiveness Score, Soft-Liquidation Profitability Score, Collateral Under SL Score, Borrower Distribution Score.")
            with col4:
                st.metric(
                    "Final Interdependency on Volatility", 
                    f"{interdependency_score_volatility:.2%}",
                    help="Score based on interdependency on volatility"
                )
                st.progress(interdependency_score_volatility)
                
            
            
            st.divider()

            st.subheader("Market Health Score - Final Score")
            st.caption("Uses scores from all components with weighted average")

            ### Version 1.5.0
            # Calculate ultimate score
            # ultimate_score = (interdependency_score_volatility*9 + 
            #                 interdependency_score_price_momentum*9 + 
            #                 bad_debt_score*6 + 
            #                 debt_ceiling_score*9.5 + 
            #                 aggregate_cr_score*9.5 + 
            #                 aggregate_prob_drop_score*9.5 + 
            #                 aggregate_vol_ratio_score*9.5 + 
            #                 aggregate_collateral_under_sl_score*9.5 + 
            #                 aggregate_borrower_distribution_score*9.5 + 
            #                 sl_responsiveness_score*9.5 + 
            #                 sl_profitability_score*9.5)/100
            
            ### Version 2.0.0
            ultimate_score = (interdependency_score_volatility*6 + 
                            interdependency_score_price_momentum*6 + 
                            bad_debt_score*13 + 
                            debt_ceiling_score*13 + 
                            aggregate_cr_score*10 + 
                            aggregate_collateral_under_sl_score*10 + 
                            aggregate_vol_ratio_score*10 +
                            aggregate_prob_drop_score*8 + 
                            aggregate_borrower_distribution_score*8 + 
                            sl_responsiveness_score*8 + 
                            sl_profitability_score*8)/100

            col1, col2 = st.columns([3, 1])
            with col1:
                # Create a detailed breakdown of score components
                st.markdown("#### Score Components Breakdown")
                components = {
                    "Bad Debt": [bad_debt_score, "13%"],
                    "Debt Ceiling": [debt_ceiling_score, "13%"],
                    "Collateral Ratio": [aggregate_cr_score, "10%"],
                    "Collateral Under SL": [aggregate_collateral_under_sl_score, "10%"],
                    "Volatility & Beta": [aggregate_vol_ratio_score, "10%"],
                    "Price Drop": [aggregate_prob_drop_score, "8%"],
                    "Borrower Distribution": [aggregate_borrower_distribution_score, "8%"],
                    "SL Responsiveness": [sl_responsiveness_score, "8%"],
                    "SL Profitability": [sl_profitability_score, "8%"],
                    "Interdependency (Volatility)": [interdependency_score_volatility, "6%"],
                    "Interdependency (Price Momentum)": [interdependency_score_price_momentum, "6%"]
                }
                
                for name, (score, weight) in components.items():
                    cols = st.columns([2, 1, 1])
                    with cols[0]:
                        st.write(f"**{name}**")
                    with cols[1]:
                        st.progress(score)
                    with cols[2]:
                        st.write(f"Weight: {weight}")

            with col2:
                # Display final score with large metric and color-coded progress bar
                st.metric(
                    "Final Market Health Score", 
                    f"{ultimate_score:.2%}",
                    help="Weighted average of all component scores"
                )
                st.progress(ultimate_score)
                
                # Add color-coded assessment
                if ultimate_score >= 0.8:
                    st.success("Excellent Health")
                elif ultimate_score >= 0.6:
                    st.info("Good Health")
                elif ultimate_score >= 0.4:
                    st.warning("Moderate Health")
                else:
                    st.error("Poor Health")
            
            st.divider()
            st.markdown("Detailed methodology can be found in this [notebook](https://hackmd.io/@diligentdeer/rkCvnWgMJe)")
            st.caption("Powered by LlamaRisk")
    
        with tab2:
            st.title("Market Health Score Playground")
            st.caption("Adjust scores and weights to see how they affect the overall market health score")

            # Define metrics with their tiers
            metrics = {
                "Tier 1 - Critical Metrics": {
                    "Debt Ceiling": {"default_score": 0.5, "default_weight": 13},
                    "Market Bad Debt": {"default_score": 0.5, "default_weight": 13}
                },
                "Tier 2 - Core Metrics": {
                    "Volatility Performance": {"default_score": 0.5, "default_weight": 10},
                    "Market Collateral Ratio": {"default_score": 0.5, "default_weight": 10},
                    "% of Loans in SL": {"default_score": 0.5, "default_weight": 10}
                },
                "Tier 3 - Secondary Metrics": {
                    "Price Drop Probability": {"default_score": 0.5, "default_weight": 8},
                    "Average Arb Profit": {"default_score": 0.5, "default_weight": 8},
                    "SL Responsiveness": {"default_score": 0.5, "default_weight": 8},
                    "Borrower Concentration": {"default_score": 0.5, "default_weight": 8}
                }
            }

            # Style definitions for tiers
            tier_styles = {
                "Tier 1 - Critical Metrics": "background-color: rgba(128, 128, 128, 0.1)",
                "Tier 2 - Core Metrics": "background-color: rgba(128, 128, 128, 0.1)",
                "Tier 3 - Secondary Metrics": "background-color: rgba(128, 128, 128, 0.1)"
            }

            # Create columns for headers
            col_name, col_score, col_weight = st.columns([2, 2, 1])
            with col_name:
                st.markdown("**Category**")
            with col_score:
                st.markdown("**Score**")
            with col_weight:
                st.markdown("**Weight**")

            # Dictionary to store all scores and weights
            scores = {}
            weights = {}
            
            # Display metrics by tier
            for tier, tier_metrics in metrics.items():
                # Display tier header
                st.markdown(f"""
                    <div style="{tier_styles[tier]}; padding: 10px; border-radius: 5px; margin: 15px 0;">
                        <b>{tier}</b>
                    </div>
                """, unsafe_allow_html=True)
                
                # Display metrics for this tier
                for metric, defaults in tier_metrics.items():
                    col_name, col_score, col_weight = st.columns([2, 2, 1])
                    
                    with col_name:
                        st.write(metric)
                    
                    with col_score:
                        scores[metric] = st.slider(
                            f"Score for {metric}",
                            0.0, 1.0,
                            defaults["default_score"],
                            key=f"score_{metric}",
                            label_visibility="collapsed"
                        )
                    
                    with col_weight:
                        weights[metric] = st.number_input(
                            f"Weight for {metric}",
                            min_value=0,
                            max_value=100,
                            value=defaults["default_weight"],
                            key=f"weight_{metric}",
                            label_visibility="collapsed"
                        )

            # Calculate interdependency scores
            price_metrics = ["Price Drop Probability", "Debt Ceiling", "Market Collateral Ratio", "Borrower Concentration"]
            vol_metrics = ["Volatility Performance", "SL Responsiveness", "Average Arb Profit", "% of Loans in SL", "Borrower Concentration"]

            st.markdown("""
                <div style="background-color: rgba(128, 128, 128, 0.1); padding: 10px; border-radius: 5px; margin: 5px 0;">
                    <b>Tier 4 - Interdependency Metrics</b>
                </div>
            """, unsafe_allow_html=True)

            # Calculate and display interdependency scores
            col_name, col_score, col_weight = st.columns([2, 2, 1])
            
            with col_name:
                st.write("Momentum Interdependency")
            with col_score:
                momentum_score = np.median([scores[m] for m in price_metrics if m in scores])
                st.metric("", f"{momentum_score:.2%}")
            with col_weight:
                weights["Momentum Interdependency"] = st.number_input(
                    "Weight for Momentum Interdependency",
                    min_value=0,
                    max_value=100,
                    value=6,
                    key="weight_momentum",
                    label_visibility="collapsed"
                )

            col_name, col_score, col_weight = st.columns([2, 2, 1])
            
            with col_name:
                st.write("Volatility Interdependency")
            with col_score:
                volatility_score = np.median([scores[m] for m in vol_metrics if m in scores])
                st.metric("", f"{volatility_score:.2%}")
            with col_weight:
                weights["Volatility Interdependency"] = st.number_input(
                    "Weight for Volatility Interdependency",
                    min_value=0,
                    max_value=100,
                    value=6,
                    key="weight_volatility",
                    label_visibility="collapsed"
                )

            scores["Momentum Interdependency"] = momentum_score
            scores["Volatility Interdependency"] = volatility_score

            st.divider()

            # Calculate total weight and normalize if needed
            total_weight = sum(weights.values())
            st.metric("Total Weight", f"{total_weight}%")
            
            if total_weight != 100:
                st.warning(f"Total weight ({total_weight}%) does not sum to 100%. Weights will be normalized.")
                normalized_weights = {k: v/total_weight*100 for k, v in weights.items()}
            else:
                normalized_weights = weights

            # Calculate final score
            final_score = sum(scores[k] * normalized_weights[k]/100 for k in scores.keys())

            # Display final score and breakdown
            st.subheader("Final Score Breakdown")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                for metric in scores.keys():
                    cols = st.columns([2, 1, 1])
                    with cols[0]:
                        st.write(f"**{metric}**")
                    with cols[1]:
                        st.progress(scores[metric])
                    with cols[2]:
                        st.write(f"{normalized_weights[metric]:.1f}%")

            with col2:
                st.metric("Final Market Health Score", f"{final_score:.2%}")
                st.progress(final_score)
                
                if final_score >= 0.8:
                    st.success("Excellent Health")
                elif final_score >= 0.6:
                    st.info("Good Health")
                elif final_score >= 0.4:
                    st.warning("Moderate Health")
                else:
                    st.error("Poor Health")
    
    with tab3:
        show_changelog()
        
if __name__ == "__main__":
    main()