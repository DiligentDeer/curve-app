def score_with_limits(score_this: float,
                      upper_limit: float, 
                      lower_limit: float,
                      direction: bool,
                      mid_limit: float = None) -> float:
    """
    Score the market based on the collateral ratio comparison
    
    Args:
        score_this (float): Value to be scored
        upper_limit (float): Upper boundary for scoring
        lower_limit (float): Lower boundary for scoring
        mid_limit (float): Middle point representing 0.5 score
        direction (bool): If True, higher values get higher scores
                        If False, lower values get higher scores
    
    Returns:
        float: Score between 0 and 1
    """
    
    if mid_limit is None:
        mid_limit = (upper_limit + lower_limit) / 2
    
    if direction:
        if score_this >= upper_limit:
            return 1.0
        elif score_this <= lower_limit:
            return 0.0
        else:
            # Score between lower and mid
            if score_this <= mid_limit:
                return 0.5 * (score_this - lower_limit) / (mid_limit - lower_limit)
            # Score between mid and upper
            else:
                return 0.5 + 0.5 * (score_this - mid_limit) / (upper_limit - mid_limit)
    else:
        if score_this >= upper_limit:
            return 0.0
        elif score_this <= lower_limit:
            return 1.0
        else:
            # Score between lower and mid
            if score_this <= mid_limit:
                return 1.0 - 0.5 * (score_this - lower_limit) / (mid_limit - lower_limit)
            # Score between mid and upper
            else:
                return 0.5 - 0.5 * (score_this - mid_limit) / (upper_limit - mid_limit)
    
    # Ensure score is between 0 and 1
    return max(0.0, min(1.0, score))

def score_bad_debt(bad_debt: float,
                   current_debt: float) -> float:
    
    if bad_debt == 0:
        return 1.0
    elif bad_debt < 0.001 * current_debt:
        # score between 0.5 and 1
        return 0.5 + 0.5 * (bad_debt / (0.001 * current_debt))
    elif bad_debt < 0.01 * current_debt:
        # score between 0 and 0.5
        return 0.5 * (bad_debt / (0.01 * current_debt))
    else:
        return 0.0
    

def score_debt_ceiling(recommended_debt_ceiling: float,
                       current_debt_ceiling: float,
                       current_debt: float) -> float:
    
    if current_debt_ceiling <= recommended_debt_ceiling:
        return 1.0
    elif current_debt <= recommended_debt_ceiling:
        # score between 0.5 and 1
        return 0.5 + 0.5 * ((recommended_debt_ceiling - current_debt) / recommended_debt_ceiling)
    else:
        return 0.0

