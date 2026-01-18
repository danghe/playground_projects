from typing import Dict, List

class PlaybookEngine:
    """
    Deterministic Strategy Engine.
    Translates Market Regime (VIX, SPI, Financing) into actionable advice.
    """
    
    @staticmethod
    def generate_playbook(market_state: Dict, sector_stats: Dict) -> Dict:
        # Inputs
        vix = market_state.get('vix', 20.0)
        financing = market_state.get('financing_window', 'Neutral')
        spi_breadth = sector_stats.get('spi_breadth', 0.0) # % of universe with SPI > 60
        
        # 1. Regime Detection
        regime = "Status Quo"
        theme = "Wait and See"
        if vix > 25:
            if financing == "Closed":
                regime = "Crisis Defense"
                theme = "Preserve Cash & Survive"
            else:
                regime = "Distressed Opportunity"
                theme = "Calculated Risk Taking"
        elif spi_breadth > 30:
             regime = "Buyer's Market"
             theme = "Roll-up Consolidation"
        elif financing == "Open" and vix < 15:
             regime = "Aggressive Growth"
             theme = "Land Grab & IPOs"

        # 2. Action Plan Generation
        actions = {
            "CEO": [],
            "CorpDev": [],
            "Banker": []
        }

        if regime == "Distressed Opportunity":
            actions["CEO"] = [
                "Review core portfolio for non-strategic divestitures.",
                "Prepare defense against opportunistic activist campaigns."
            ]
            actions["CorpDev"] = [
                "Screen for competitors with leverage > 4.0x.",
                "Exploit 363 sales and restructuring processes."
            ]
            actions["Banker"] = [
                "Pitch restructuring and liability management.",
                "Identify Take-Private candidates for PE sponsors."
            ]
        
        elif regime == "Buyer's Market":
            actions["CEO"] = [
                "Accretive acquisitions to bolster growth.",
                "Use strong balance sheet to gain market share."
            ]
            actions["CorpDev"] = [
                "Target smaller players struggling with SPI > 60.",
                "Execute programmatic roll-up strategy."
            ]
            actions["Banker"] = [
                "Sell-side mandates for pressured assets.",
                "Buyside advisory for well-capitalized strategics."
            ]

        elif regime == "Aggressive Growth":
             actions["CEO"] = [
                "Accelerate R&D and geographic expansion.",
                "Consider IPO or dual-track process if private."
            ]
             actions["CorpDev"] = [
                "Pursue transformative 'Merger of Equals'.",
                "Pay up for high-growth technology assets."
            ]
             actions["Banker"] = [
                "IPO underwriting and capital raising.",
                "Cross-border mega-merger advisory."
            ]
            
        else: # Status Quo / Crisis Defense
             actions["CEO"] = [
                "Focus on operational efficiency and margins.",
                "Limit capex to essential projects."
            ]
             actions["CorpDev"] = [
                "Pause large M&A; focus on minor bolt-ons.",
                "Divest non-core assets to raise cash."
            ]
             actions["Banker"] = [
                "Fairness opinions and defense advisory.",
                "Private placements and credit facility amendments."
            ]

        return {
            "regime": regime,
            "theme": theme,
            "actions": actions,
            "stats": {
                "vix": vix,
                "spi_breadth": f"{round(spi_breadth)}%"
            }
        }
