from typing import List, Dict
import statistics

class IndustryTrendEngine:
    """
    Aggregates company-level data into Sub-Industry Intelligence.
    Generates Heatmap metrics + Trend Narrative.
    """
    
    @staticmethod
    def aggregate(results: List[Dict], sector_map: Dict) -> Dict:
        """
        Groups results by sub_industry (from sector_map) and calculates medians.
        Generates Heatmap metrics + Trend Narrative.
        """
        bins = {}
        
        # 1. Group by Sub-Industry
        for r in results:
            ticker = r['ticker']
            # Lookup sub_industry from UniverseService map or result itself if injected
            sub = r.get('sub_industry', "Other")
            if sub == "Other" and ticker in sector_map:
                sub = sector_map[ticker].get('sub_industry', "Other")
            
            if sub not in bins:
                bins[sub] = {"spi": [], "catalysts": 0, "count": 0, "val_scores": [], "price_change_proxy": []}
            
            # Data Collection
            bins[sub]['spi'].append(r['scores']['spi'])
            bins[sub]['catalysts'] += len(r.get('catalysts', []))
            bins[sub]['count'] += 1
            
            # Valuation (Collect if valid number)
            val = r['evidence'].get('val_score')
            if val and isinstance(val, (int, float)):
                bins[sub]['val_scores'].append(val)
                
            # Momentum Proxy: (Price / Low_52) or (Price / High_52)? 
            # We don't have historical price in "results" easily, but we have sparkline?
            # Or use (Price - 52wLow)/52wLow approx?
            # Let's use `price` vs `previous_close` is too short. 
            # Let's rely on `revenue_growth` as a proxy for business momentum for now?
            # User asked for "Relative Momentum: 3m return". We don't have 3m return in `results`.
            # We will use SPI Trend as proxy or skip if data missing.
            # Actually, `fetch_financials` doesn't get 3m return. 
            # We'll mark N/A for now and implement properly if we add `target_price` fields.
            pass
            
            
        # 2. Calculate Aggregates
        heatmap = []
        narrative_points = []
        
        for sub, data in bins.items():
            count = data['count']
            if count == 0: continue
            
            median_spi = statistics.median(data['spi']) if data['spi'] else 0
            cat_intensity = round((data['catalysts'] / count) * 10, 1) # Normalized per 10 companies
            
            # SPI Breadth: % of companies with SPI >= 60
            high_spi_count = sum(1 for s in data['spi'] if s >= 60)
            spi_breadth = round((high_spi_count / count) * 100, 1)
            
            # Median Valuation
            median_val = statistics.median(data['val_scores']) if data['val_scores'] else 0
            val_label = f"{median_val:.1f}x" if median_val > 0 else "N/A"
            
            # Deal Posture
            posture = "Neutral"
            if median_spi > 50: posture = "Pressured"
            elif median_spi < 25: posture = "Stable"
            
            heatmap.append({
                "sub_industry": sub,
                "median_spi": median_spi,
                "catalyst_intensity": cat_intensity,
                "spi_breadth": spi_breadth,
                "median_valuation": val_label,
                "posture": posture,
                "count": count
            })
            
            # 3. Generate Narrative Snippet (Data-Driven)
            # "Midstream SPI breadth 18% (>=60), catalysts 24/100/30d, median EV/EBITDA -12% vs 2y"
            # We don't have historical comparison yet, so straight numbers.
            
            details = []
            if spi_breadth > 30: details.append(f"High Distress ({spi_breadth}% > 60 SPI)")
            if cat_intensity > 3.0: details.append(f"Active ({cat_intensity} cats/10co)")
            if median_val > 0 and median_val < 8: details.append(f"Compressed Val ({val_label})")
            
            if details:
                snippet = f"**{sub}**: " + ", ".join(details) + "."
                narrative_points.append(snippet)
            elif median_spi > 45:
                 narrative_points.append(f"**{sub}**: Elevated pressure (SPI {median_spi}). Monitor for break-ups.")

        # Default narrative if empty
        if not narrative_points:
            narrative_points.append(f"Sector stable. No major sub-industry dislocations detected.")
            
        return {
            "heatmap": heatmap,
            "narrative": narrative_points[:4] # Top 4 bullets
        }
