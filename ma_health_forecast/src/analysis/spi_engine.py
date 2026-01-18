class SPIEngine:
    """
    Seller Pressure Index (SPI) Engine.
    Calculates a 0-100 score based on 5 components.
    Transparent, weight-based model.
    """
    
    # Weight Configuration (Total 100)
    WEIGHTS = {
        "price": 20,
        "earnings": 20,
        "balance_sheet": 25,
        "governance": 15,
        "strategic": 20
    }
    
    @staticmethod
    def calculate(ticker, market_data, sec_catalysts, gov_hits):
        """
        Returns:
        {
            "total_score": int,
            "breakdown": list[str],
            "components": { "price": int, ... }
        }
        """
        score = 0
        breakdown = []
        components = {k:0 for k in SPIEngine.WEIGHTS.keys()}
        
        # 1. PRICE STRESS (20 pts)
        # Components: Drawdown vs High, Beta Volatility
        price = market_data.get('previous_close', 0.0)
        high_52 = market_data.get('fifty_two_week_high', price)
        beta = market_data.get('beta', 1.0)
        
        pct_high = (price / high_52) if high_52 else 1.0
        
        # A. Drawdown (User Logic: < 70% of High is dislocation)
        if pct_high < 0.70:
            pts = 10
            components['price'] += pts
            breakdown.append(f"Price Dislocation ({int(pct_high*100)}% of High)")
        elif pct_high < 0.85:
            pts = 5
            components['price'] += pts
            
        # B. Volatility (High Beta > 1.5 implies stress in downtrend)
        if beta > 1.5 and pct_high < 0.90:
            pts = 10
            components['price'] += pts
            breakdown.append(f"High Volatility (Beta {beta:.1f})")

        # 2. EARNINGS STRESS (20 pts)
        # Components: Negative Margins, Revenue Contraction
        rev_growth = market_data.get('revenue_growth', 0.0)
        net_margin = market_data.get('profit_margins', 0.0)
        
        if rev_growth < 0:
            pts = 10
            components['earnings'] += pts
            breakdown.append(f"Rev. Contraction ({rev_growth*100:.1f}%)")
            
        if net_margin < -0.05: # -5% Margin
            pts = 10
            components['earnings'] += pts
            breakdown.append(f"Deep Losses (Margin {net_margin*100:.1f}%)")
        elif net_margin < 0:
            pts = 5
            components['earnings'] += pts

        # 3. BALANCE SHEET STRESS (25 pts)
        # Components: Leverage Ratio, Low Cash
        cash = market_data.get('total_cash', 0.0)
        debt = market_data.get('total_debt', 0.0)
        ebitda = market_data.get('ebitda', 0.0)
        market_cap = market_data.get('market_cap', 1.0)
        
        net_debt = debt - cash
        leverage = net_debt / ebitda if ebitda > 0 else (99.0 if net_debt > 0 else 0)
        
        if leverage > 4.5:
            pts = 15
            components['balance_sheet'] += pts
            breakdown.append(f"High Leverage ({leverage:.1f}x)")
        elif leverage > 3.0:
            pts = 10
            components['balance_sheet'] += pts
            
        # Liquidity Crunch (Cash < 3% of Market Cap)
        cash_ratio = cash / market_cap
        if cash_ratio < 0.03:
            pts = 10
            components['balance_sheet'] += pts
            breakdown.append("Liquidity Constraints")

        # 4. GOVERNANCE STRESS (15 pts)
        # Driven by SEC findings
        if gov_hits > 0:
            pts = 15
            components['governance'] += pts
            breakdown.append("Governance Instab. (SEC)")

        # 5. STRATEGIC INTENT (20 pts)
        # Keywords in filings or explicit "Strategic Review" events
        strategic_signals = [c for c in sec_catalysts if "Strategic" in c.get('implication', '') or "Restructuring" in c.get('type', '')]
        if strategic_signals:
            pts = 20
            components['strategic'] += pts
            breakdown.append("Strategic Actions Signal")

        # TOTAL
        total_score = sum(components.values())
        return {
            "total_score": min(total_score, 100),
            "breakdown": breakdown,
            "components": components
        }
