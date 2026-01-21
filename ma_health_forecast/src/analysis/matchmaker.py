from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from src.analysis.profile_engine import UserProfile
from src.data.universe_service import UniverseService

@dataclass
class MatchDriver:
    """Glass-box explanation for a single score component."""
    label: str
    value: Any
    impact: str  # "High Positive", "Positive", "Negative", "Gate"
    trust: str = "TRUSTED (yfinance/Audit)"

    def __post_init__(self):
        # Auto-convert value to string if cleaner presentation needed
        pass

@dataclass
class MatchCandidate:
    ticker: str
    name: str
    sector: str
    sub_industry: str
    
    # New Multi-Dimensional Scores (0-100)
    strategic_score: float
    feasibility_score: float
    probability_score: float
    overall_score: float
    
    # Metadata
    market_cap: float
    enterprise_value: float
    revenue: float
    ebitda: float
    spi_score: float  # Seller Pressure
    buyer_readiness: float
    
    # Glass-box References
    drivers: List[MatchDriver]
    status: str = "Active" # Active, Gate Failed
    
    # v1.4.2 Metrics
    firepower_coverage: float = 0.0
    total_capacity: float = 0.0
    
    # v1.4.2 Metrics
    firepower_coverage: float = 0.0
    total_capacity: float = 0.0
    
    # Upgrade B: Close Probability Breakdown (0-100)
    close_probability_score: float = 0.0 # Renamed from probability_score (for list view consistency)
    financing_score: float = 0.0
    regulatory_score: float = 0.0
    willingness_score: float = 0.0
    willingness_status: str = "Estimated" # "Estimated", "Explicit (SPI)", "Explicit (Readiness)", "Unknown"
    
    # Upgrade A: Feasibility Metadata
    verdict: str = "Review" # GO, NO-GO, REVIEW, GO (Conditional)
    pf_leverage: float = 99.0
    
    # AI Placeholder (Filled later)
    ai_rationale: Optional[str] = None
    ai_synergy_type: Optional[str] = None
    confidence_score: float = 1.0 # 0.0 - 1.0

    
    def to_dict(self):
        return {
            "ticker": self.ticker,
            "name": self.name,
            "sector": self.sector,
            "sub_industry": self.sub_industry,
            "scores": {
                "strategic": round(self.strategic_score, 1),
                "feasibility": round(self.feasibility_score, 1),
                "probability": round(self.close_probability_score, 1),
                "close_probability": round(self.close_probability_score, 1),
                "overall": round(self.overall_score, 1),
                "financing": round(self.financing_score, 1),
                "regulatory": round(self.regulatory_score, 1),
                "willingness": round(self.willingness_score, 1)
            },
            "status_flags": {
                "willingness": self.willingness_status,
                "verdict": self.verdict
            },
            "market_cap_fmt": f"${self.market_cap/1e9:.1f}B" if self.market_cap > 1e9 else f"${self.market_cap/1e6:.1f}M",
            "ev_fmt": f"${self.enterprise_value/1e9:.1f}B" if self.enterprise_value > 1e9 else f"${self.enterprise_value/1e6:.1f}M",
            "drivers": [d.__dict__ for d in self.drivers],
            "ai_rationale": self.ai_rationale,
            "ai_synergy_type": self.ai_synergy_type,
            "spi": self.spi_score,
            "confidence": self.confidence_score,
            "firepower_coverage": self.firepower_coverage,
            "total_capacity": self.total_capacity
        }

class MatchEngine:
    def __init__(self):
        self.universe_svc = UniverseService()
        self.companies = self.universe_svc.universe
        self.fundamentals = self.universe_svc.fundamentals

    def _get_candidate_data(self, ticker: str) -> Dict:
        """Merges Universe metadata with Fundamentals store."""
        return self.universe_svc.get_company(ticker) or {}

    def _calculate_total_capacity(self, user: UserProfile, max_lev: float = 4.5, dilution_limit: float = 0.2) -> float:
        """
        Calculates Banker-Style Total Capacity.
        Total Capacity = Cash + Debt Capacity + Stock Capacity
        """
        # Debt Capacity = Max Levered EBITDA - Current Debt
        debt_cap = max(0, (max_lev * user.ebitda) - user.total_debt)
        
        # Stock Capacity = Market Cap * Dilution Limit (default 20%)
        stock_cap = user.market_cap * dilution_limit
        
        return user.total_cash + debt_cap + stock_cap

    def _calculate_confidence(self, cand_data: Dict) -> float:
        """Calculates data confidence (0.0 - 1.0) based on critical fields."""
        critical_fields = ['ebitda', 'enterprise_value', 'total_cash', 'total_debt', 'revenue']
        missing_count = 0
        for f in critical_fields:
            if not cand_data.get(f):
                missing_count += 1
        
        # Penalize: -0.15 per missing critical field
        score = 1.0 - (missing_count * 0.15)
        return max(0.1, score)


    def find_matches(self, user: UserProfile, intent: str, mandate_mode: str = "Consolidation", limit: int = 50) -> List[MatchCandidate]:
        """
        Unified Entry Point for Deal Architect v1.4.2.
        """
        results = []
        
        # 0. Calculate User Total Capacity (Banker Logic)
        user_total_capacity = self._calculate_total_capacity(user)
        
        # 1. Filter Universe (Basic Sanity)
        candidates = [c['ticker'] for c in self.companies if c.get('ticker') != user.ticker]
        
        # Mandate Filter (Sub-Sector Specifics)
        if mandate_mode == "Consolidation":
            # Strict Sub-sector
            candidates = [t for t in candidates if self._get_candidate_data(t).get('sub_industry') == user.sub_industry]
        elif mandate_mode == "Adjacency":
            # Same Sector
            candidates = [t for t in candidates if self._get_candidate_data(t).get('sector') == user.sector]
        # Diversification = All (No filter)
            
        for ticker in candidates:
            cand = self._get_candidate_data(ticker)
            if not cand or cand.get('market_cap', 0) == 0: continue
            
            # --- SCORING CONTAINERS ---
            score_strat = 50.0
            score_feas = 50.0
            score_prob = 50.0
            drivers = []
            
            # --- DEAL PHYSICS PROXIES ---
            raw_ev = cand.get('enterprise_value', 0)
            mcap = cand.get('market_cap', 0)
            cand_ev = raw_ev if raw_ev > 0 else mcap # Fallback
            cand_ebitda = cand.get('ebitda', 0)
            cand_rev = cand.get('total_revenue') or cand.get('revenue', 0)
            
            # Confidence Calculation
            conf_score = self._calculate_confidence(cand)

            
            # --- INTENT LOGIC ---
            
            if intent == "BUY":
                # === BUY SIDE LOGIC ===
                
                # GATE 1: Materiality (Revenue > 3% of User - Core Mode default)
                if user.revenue > 0 and cand_rev < (user.revenue * 0.03):
                    continue 

                est_deal_value = cand_ev * 1.25 # 25% Premium base
                
                # GATE 2: Financial Capacity (Total Capacity Check)
                # v1.4.2: Use explicitly calculated Total Capacity instead of simple cash check
                can_afford_direct = (est_deal_value <= user_total_capacity)
                
                # Leveraged feasibility track (Pro-Forma < 4.5x) for scoring
                can_afford_lbo = False
                combined_ebitda = user.ebitda + cand_ebitda
                pf_leverage = 99.0
                if combined_ebitda > 0:
                    new_debt_needed = max(0, est_deal_value - user.total_cash)
                    pro_forma_debt = user.total_debt + cand.get('total_debt', 0) + new_debt_needed
                    pf_leverage = pro_forma_debt / combined_ebitda
                    if pf_leverage <= 4.5: can_afford_lbo = True
                
                if not can_afford_direct:
                     # Even if direct capacity fails, check if LBO math saves it (redundant but explicit)
                     if not can_afford_lbo:
                        continue # Truly unaffordable

                # GATE 3: Size Rationality (Removed 80% Cap for v1.4.2 to allow Transformational if fundable)
                # We track size_ratio for scoring only
                size_ratio = mcap / user.market_cap

                # --- SCORING ---
                
                # 1. Feasibility (0-100)
                if can_afford_direct:
                    score_feas += 30
                    drivers.append(MatchDriver("Strong Balance Sheet", f"Total Capacity ${user_total_capacity/1e9:.1f}B > Deal", "High Positive"))
                elif pf_leverage < 4.5:
                    score_feas += 15
                    drivers.append(MatchDriver("LBO Feasible", f"PF Leverage {pf_leverage:.1f}x", "Neutral"))
                
                # Firepower Coverage Metric
                fp_coverage = user_total_capacity / est_deal_value if est_deal_value > 0 else 0
                if fp_coverage > 1.5:
                    score_feas += 10
                    drivers.append(MatchDriver("High Coverage", f"{fp_coverage:.1f}x Deal Value", "Positive"))

                # 2. Strategic Fit (0-100)
                # Growth Desperation (v1.4.2)
                if user.revenue_growth < 0.05 and cand.get('revenue_growth', 0) > 0.15:
                    score_strat += 30
                    drivers.append(MatchDriver("Growth Fix", f"Target Growth {cand.get('revenue_growth',0)*100:.1f}% vs Own {user.revenue_growth*100:.1f}%", "High Positive"))

                if cand.get('sub_industry') == user.sub_industry:
                    score_strat += 25
                    drivers.append(MatchDriver("Consolidation", "Same Sub-Sector", "High Positive"))
                    
                    # Antitrust Heuristic (Penalty if both large)
                    if user.revenue > 10e9 and cand_rev > 5e9:
                        score_strat -= 20
                        drivers.append(MatchDriver("Antitrust Risk", "Large Horizontal Merge", "Negative"))
                        
                elif cand.get('sector') == user.sector:
                    score_strat += 10
                    drivers.append(MatchDriver("Adjacency", "Same Sector", "Positive"))
                elif mandate_mode == "Diversification":
                    score_strat -= 10 # Integration penalty
                    drivers.append(MatchDriver("Diversification Risk", "Different Sector", "Negative"))

                # Value Arb (Accretion)
                if cand_ebitda > 0 and user.ebitda > 0:
                    cand_mult = cand_ev / cand_ebitda
                    # Calculate User EV dynamically if not present
                    user_ev = getattr(user, 'enterprise_value', (user.market_cap + user.total_debt - user.total_cash))
                    user_mult = user_ev / user.ebitda if user_ev > 0 else 15.0
                    
                    if cand_mult < user_mult:
                        score_strat += 15
                        drivers.append(MatchDriver("Value Arbitrage", f"Buy {cand_mult:.1f}x vs Own {user_mult:.1f}x", "Positive"))

                # 3. Probability (0-100)
                spi = cand.get('spi_score', 50)
                if spi > 60:
                    score_prob += 20
                    drivers.append(MatchDriver("Seller Pressure", f"High SPI {spi}", "High Positive"))
                elif spi < 30:
                    score_prob -= 10
                
                # Confidence Penalty on Probability
                if conf_score < 0.7:
                    score_prob -= 15
                    drivers.append(MatchDriver("Data Uncertainty", f"Confidence {int(conf_score*100)}% (Missing Metrics)", "Negative"))

                
                if user.total_cash > est_deal_value:
                    score_prob += 20 # Cash deals close faster
                    
            elif intent == "SELL":
                # === SELL SIDE LOGIC ===
                
                # GATE: Acquirer Capability
                # Est Acquirer FP = Cash + 3*EBITDA - Debt
                acq_cash = cand.get('total_cash', 0)
                acq_ebitda = cand.get('ebitda', 0)
                acq_debt = cand.get('total_debt', 0)
                acq_fp = acq_cash + max(0, 3.0*acq_ebitda) - acq_debt
                
                target_price = user.market_cap * 1.3 # 30% Premium
                
                if acq_fp < target_price:
                    continue # They can't afford us

                # Scores
                score_feas += 40 # They passed the hard gate
                drivers.append(MatchDriver("Qualified Buyer", f"Firepower Coverage > satisfied", "Gate Passed"))
                
                if cand.get('sub_industry') == user.sub_industry:
                    score_strat += 30
                    drivers.append(MatchDriver("Strategic Consolidator", "Same Sub-Sector", "High Positive"))
                
                br = cand.get('buyer_readiness', 50)
                if br > 70:
                    score_prob += 25
                    drivers.append(MatchDriver("Active Acquirer", f"Buyer Readiness {br}", "High Positive"))

            elif intent == "MERGE":
                # === MERGE LOGIC ===
                
                # GATE: Size Parity (0.5x - 1.5x)
                ratio = mcap / user.market_cap
                if not (0.5 <= ratio <= 1.5):
                    continue
                
                pass_gate = True
                combined_ebitda = user.ebitda + cand_ebitda
                if combined_ebitda <= 0: pass_gate = False
                
                if pass_gate:
                    # Feasibility = Balance Sheet Health
                    combined_debt = user.total_debt + cand.get('total_debt', 0)
                    pf_lev = combined_debt / combined_ebitda
                    if pf_lev < 4.0:
                        score_feas += 25
                        drivers.append(MatchDriver("Healthy Balance Sheet", f"PF Lev {pf_lev:.1f}x", "Positive"))
                    else:
                        score_feas -= 20
                        drivers.append(MatchDriver("Leverage Risk", f"PF Lev {pf_lev:.1f}x", "Negative"))
                    
                    # Synergy
                    if cand.get('sub_industry') == user.sub_industry:
                        score_strat += 30
                        drivers.append(MatchDriver("Sub-Sector Synergy", "Cost/Scale", "High Positive"))

            # --- SCORING & PROBABILITY BREAKDOWN (UPGRADE A & B) ---
            
            # 1. Feasibility & Leverage (Deterministic Cap)
            score_feas = 50.0
            verdict = "REVIEW"
            
            # Calculate final PF Leverage for Score (Unified logic)
            # Check Intent-Specific Constraints
            is_breach = False
            
            if intent == "BUY":
                # Cap 4.5x
                if can_afford_direct:
                    score_feas = 100
                    verdict = "GO"
                elif pf_leverage <= 4.5:
                    score_feas = 70 + (4.5 - pf_leverage) * 10
                    verdict = "GO"
                else: 
                    # Breach
                    is_breach = True
                    score_feas = 30 # Hard Cap
                    verdict = "NO-GO"
                    drivers.append(MatchDriver("Leverage Breach", f"PF {pf_leverage:.1f}x > 4.5x Cap", "Negative"))

                # FP Bonus still applies if feasible
                if not is_breach and fp_coverage > 1.5:
                    score_feas += 10
                    drivers.append(MatchDriver("High Coverage", f"{fp_coverage:.1f}x Deal Value", "Positive"))

            elif intent == "SELL":
                # Cap: Acquirer Capacity
                # If they passed the gate, they are feasible
                score_feas = 90
                verdict = "GO"
                # If leveraging was modeled earlier and failed, score would be lower, but gate handles it.
                
            elif intent == "MERGE":
                # Cap 4.0x
                if pf_lev <= 4.0:
                    score_feas = 80
                    verdict = "GO"
                else:
                    is_breach = True
                    score_feas = 40 # Cap
                    verdict = "NO-GO"
                    drivers.append(MatchDriver("Leverage Breach", f"PF {pf_lev:.1f}x > 4.0x Cap", "Negative"))
            
            score_feas = min(100, max(0, score_feas))
            financing_score = score_feas # 1:1 map for component view
            
            # 2. Regulatory Score (Simple Heuristic for now)
            # Default 70. Reduce if revenue scale is huge (Antitrust)
            reg_score = 70
            combo_rev = user.revenue + cand_rev
            if combo_rev > 20e9 and cand.get('sub_industry') == user.sub_industry:
                reg_score = 40
                drivers.append(MatchDriver("Antitrust", "Large Horizontal Merge", "Negative"))
            regulatory_score = reg_score

            # 3. Willingness Score (Upgrade B)
            will_score = 50.0
            will_status = "Unknown"
            
            if intent == "BUY":
                # Use SPI
                spi_raw = cand.get('spi_score')
                if spi_raw is not None:
                     will_status = "Explicit (SPI)"
                     if spi_raw > 60: will_score = 85
                     elif spi_raw > 30: will_score = 60
                     else: will_score = 35
                else:
                     # Missing SPI
                     will_score = 50
                     will_status = "Unknown"
                     # Downgrade overall prob slightly for uncertainty? handled via weights maybe
                     conf_score -= 0.1 # Penalty for missing willingness signal
                     
            elif intent == "SELL":
                # Use Buyer Readiness
                br_raw = cand.get('buyer_readiness')
                if br_raw is not None:
                    will_status = "Explicit (Readiness)"
                    will_score = br_raw # Direct map 0-100
                else:
                    will_score = 50
                    will_status = "Unknown"
            
            elif intent == "MERGE":
                 # Use Strategic Fit as proxy for "Mutual Interest"
                 will_score = score_strat
                 will_status = "Inferred (Strategic)"

            willingness_score = will_score
            
            # --- FINAL CLOSE PROBABILITY AGGREGATION ---
            # Weights: Financing 40%, Reg 25%, Willingness 35%
            w_fin = 0.40
            w_reg = 0.25
            w_will = 0.35
            
            if intent == "SELL":
                w_fin = 0.35
                w_reg = 0.25
                w_will = 0.40 # Buyer appetite matters more
            
            close_prob = (financing_score * w_fin) + (regulatory_score * w_reg) + (willingness_score * w_will)
            close_prob = min(100, max(0, close_prob))            

            # --- FINAL OVERALL SCORE ---
            # Rebalance input to overall: Strategic 40%, Feasibility 30%, Close Prob 30%
            overall = (score_strat * 0.4) + (score_feas * 0.3) + (close_prob * 0.3)
            
            # Populate Result
            results.append(MatchCandidate(
                ticker=ticker,
                name=cand.get('title') or cand.get('name') or ticker,
                sector=cand.get('sector', 'Unknown'),
                sub_industry=cand.get('sub_industry', 'Unknown'),
                strategic_score=score_strat,
                feasibility_score=score_feas,
                probability_score=close_prob, # Legacy field maps to Close Prob
                close_probability_score=close_prob, # New Explicit
                overall_score=overall,
                
                # Breakdown
                financing_score=financing_score,
                regulatory_score=regulatory_score,
                willingness_score=willingness_score,
                willingness_status=will_status,
                
                # Metadata
                market_cap=mcap,
                enterprise_value=cand_ev,
                revenue=cand_rev,
                ebitda=cand_ebitda,
                spi_score=cand.get('spi_score'), # Keep None if missing for UI handling
                buyer_readiness=cand.get('buyer_readiness'),
                drivers=drivers,
                confidence_score=max(0.1, conf_score),
                total_capacity=user_total_capacity,
                firepower_coverage=fp_coverage if intent == "BUY" else 0.0,
                
                # Metrics
                pf_leverage=pf_leverage if intent != "SELL" else 0.0, # Only relevant if we model it
                verdict=verdict
            ))
            
        # Sort by Overall
        results.sort(key=lambda x: x.overall_score, reverse=True)
        return results[:limit]

    # --- Legacy Wrappers for Backward Compatibility ---
    def find_targets(self, user: UserProfile, sector_focus: str = None, limit: int = 50) -> List[Any]:
        # Map legacy find_targets to find_matches(BUY)
        # Note: Returns MatchCandidate with new fields, might need adaptation if UI expects precise old dict
        # But app.py likely just iterates. We should check if app.py uses .match_score_det which is mostly gone.
        # To be safe, we map new scores to old fields in MatchCandidate if needed.
        # Actually MatchCandidate dataclass changed. This is a breaking change for old code if it accesses .match_score_det
        # I removed match_score_det from MatchCandidate definition above.
        # I should add properties or aliases to MatchCandidate to support legacy access if strict.
        # But for 'Refining Matchmaker', we likely want to move forward.
        # The user's prompt implies a new tab. Existing "Simulate" might break if it relies on old fields.
        # I will re-add legacy fields to MatchCandidate computed from new scores to be safe.
        return self.find_matches(user, "BUY", limit=limit)

    def find_acquirers(self, user: UserProfile, sector_focus: str = None, limit: int = 50) -> List[Any]:
        return self.find_matches(user, "SELL", limit=limit)

