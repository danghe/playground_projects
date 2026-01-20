from google import genai
import os
import time


def build_deep_dive_prompt(ticker: str, role_type: str, context: dict) -> str:
    """
    Constructs a role-specific, constraint-based prompt for Gemini.
    """
    # 1. Pre-process Data (Anchor the LLM to facts)
    firepower_val = context.get('firepower', 0)
    # Handle potentially pre-formatted strings or raw numbers
    if isinstance(firepower_val, (int, float)):
        firepower_str = f"${firepower_val}B"
    else:
        firepower_str = str(firepower_val)

    # Leverage handling
    net_lev = context.get('net_leverage', None)
    leverage_str = f"{net_lev}x" if net_lev is not None else "N/A"
    
    # Context extraction
    spi_score = context.get('spi_score', 'N/A')
    br_score = context.get('br_score', 'N/A')
    sub_sector = context.get('sub_sector', 'General')
    drivers = context.get('drivers', 'Market Conditions')
    name = context.get('name', 'Unknown')

    # 2. Define Mission & Styling based on Role
    if role_type.lower() == 'buyer':
        # Buyer Logic: Focus on Capital Deployment
        accent_color = "#10b981"  # Emerald Green
        thesis_label = "Capital Deployment Mandate"
        role_instruction = f"""
        **YOUR ROLE: BUY-SIDE STRATEGIST**
        **MISSION**: Analyze {name} ({ticker}) as a potential ACQUIRER.
        This company has a Buyer Readiness Score of {br_score}/100.
        
        **ANALYSIS TASKS**:
        1. **Capacity Check**: {name} has **{firepower_str}** in Firepower. Is this enough for a platform deal in {sub_sector}, or just bolt-ons?
        2. **Leverage Reality**: With leverage at **{leverage_str}**, should {name} fund with Cash or Debt?
        3. **Targeting Strategy**: What specific asset type is {name} missing? (e.g., "AI capability", "Geographic expansion").
        """
    else:
        # Seller Logic: Focus on Pressure & Exit
        accent_color = "#ef4444"  # Red
        thesis_label = "Exit & Divestiture Thesis"
        role_instruction = f"""
        **YOUR ROLE: SELL-SIDE STRATEGIST**
        **MISSION**: Analyze {name} ({ticker}) as a potential TARGET.
        This company has a Seller Pressure Score of {spi_score}/100.
        
        **ANALYSIS TASKS**:
        1. **The Catalyst**: Link the score to the primary driver: "{drivers}". Why should {name} sell NOW?
        2. **The Asset**: Is this a **WholeCo Sale** (Take-Private) or a **Carve-Out** (Divestiture)?
        3. **The Buyer Universe**: Name 2-3 specific types of buyers (e.g., "Ideal LBO candidate" or "Strategic fit for [Competitor Name]").
        """

    # 3. The Master Prompt
    prompt = f"""
    You are a Senior Managing Director at a Tier-1 Investment Bank.
    Provide a **Strategic Tear Sheet** on the following MARKET PLAYER:

    **SUBJECT COMPANY**: {ticker} ({name})
    **SECTOR**: {sub_sector}
    **CURRENT DATE**: January 2026 (Treat 2024/2025 data as historical)
    
    **HARD DATA ANCHORS (CITE THESE)**:
    - Firepower: {firepower_str}
    - Net Leverage: {leverage_str}
    - Primary Context: {drivers}

    {role_instruction}

    **TASK ENRICHMENT**:
    - **Search & Enrich**: Search for the latest available market data (news, filings, macro trends) to enrich this analysis.
    - **Contextualize**: Synthesize the "latest real-world data" (2024/2025) as the most current available context for this Jan 2026 simulation.

    **STRICT OUTPUT RULES**:
    1. **No Definitions**: Do not explain what the company does. Assume the CEO knows.
    2. **Evidence-Based**: You MUST cite the Firepower/Leverage metrics in your text.
    3. **Format**: Return ONLY raw HTML code (no markdown blocks, no ```html wrappers). 
    4. **Style**: Use the specific HTML structure below tailored for a light-themed panel.

    **REQUIRED HTML STRUCTURE**:
    <div style="font-family: 'Segoe UI', sans-serif; color: #333;">
        
        <div style="background-color: #f8f9fa; border-left: 4px solid {accent_color}; padding: 12px; margin-bottom: 15px; border-radius: 0 4px 4px 0;">
            <h4 style="margin: 0; font-size: 11px; text-transform: uppercase; color: #777; letter-spacing: 1px; font-weight: 600;">{thesis_label}</h4>
            <p style="margin: 6px 0 0; font-size: 14px; font-weight: 700; color: #111; line-height: 1.4;">
                [Insert a single, high-conviction sentence summarizing the strategic opportunity.]
            </p>
        </div>

        <h5 style="color: #555; font-size: 12px; border-bottom: 1px solid #eee; padding-bottom: 4px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">Strategic Rationale</h5>
        <p style="font-size: 13px; line-height: 1.5; margin-bottom: 20px; color: #333;">
            [Deep dive analysis. <b>Bold key insights</b>. Explicitly reference the {firepower_str} Firepower or {leverage_str} Leverage context.]
        </p>

        <h5 style="color: #555; font-size: 12px; border-bottom: 1px solid #eee; padding-bottom: 4px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">
            {'TARGETING STRATEGY' if role_type.lower() == 'buyer' else 'LIKELY SUITORS & STRUCTURE'}
        </h5>
        <ul style="font-size: 13px; padding-left: 20px; margin-bottom: 0; color: #333; line-height: 1.5;">
            <li style="margin-bottom: 6px;"><b>[Theme 1]:</b> [Detail]</li>
            <li style="margin-bottom: 6px;"><b>[Theme 2]:</b> [Detail]</li>
            <li><b>[Risk/Opportunity]:</b> [Detail]</li>
        </ul>
    </div>
    """
    
    return prompt


def build_radar_dossier_prompt(ticker: str, context: dict) -> str:
    """
    Constructs a data-rich 'Dossier' prompt for the Strategic Radar (Legacy Style).
    Focuses on 'Why It Matters', 'M&A Posture', 'Next 90 Days'.
    """
    # Parsing context
    name = context.get('name', 'Unknown')
    sector = context.get('sector', 'General')
    drivers = context.get('drivers', 'Market Data')
    spi = context.get('spi_score', 'N/A')
    
    prompt = f"""
    You are a Senior M&A Strategist at a major Investment Bank.
    Provide a **Strategic Dossier** on the following company for the 'Strategic Radar' watchlist.

    **SUBJECT**: {ticker} ({name})
    **SECTOR**: {sector}
    **CURRENT DATE**: January 2026 (Treat 2024/2025 data as historical)
    **CONTEXT**: {drivers}
    **SELLER PRESSURE**: {spi}/100
    
    **TASK**:
    Generate a data-heavy, executive summary covering the following 4 distinct sections.
    Use your internal knowledge to augment the provided context.
    
    **TASK ENRICHMENT**:
    - **Search & Enrich**: Search for the latest available market data (news, filings, macro trends) to enrich this analysis.
    - **Contextualize**: Synthesize the "latest real-world data" (2024/2025) as the most current available context for this Jan 2026 simulation.

    **REQUIRED HTML STRUCTURE**:
    <div style="font-family: 'Segoe UI', sans-serif; color: #333;">

        <!-- Section 1: Why It Matters Now -->
        <h5 style="color: #444; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 8px;">
            <i class="bi bi-lightning-charge-fill text-warning me-1"></i> WHY IT MATTERS NOW
        </h5>
        <ul style="font-size: 13px; padding-left: 20px; margin-bottom: 15px; line-height: 1.5;">
            <li style="margin-bottom: 5px;"><b>[Key Catalyst]:</b> [Detail on recent news, filing, or market move]</li>
            <li style="margin-bottom: 5px;"><b>[Financial Signal]:</b> [Detail on valuation/revenue trend]</li>
            <li><b>[Strategic Shift]:</b> [Detail on management/governance/product]</li>
        </ul>

        <!-- Section 2: M&A Posture -->
        <h5 style="color: #444; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 8px;">
            M&A POSTURE
        </h5>
        <div style="background-color: #f1f5f9; padding: 10px; border-radius: 4px; margin-bottom: 15px; font-size: 13px;">
            <div style="margin-bottom: 6px;">
                <span style="font-weight: 700; color: #0f172a;">Likely Role:</span> 
                <span style="background-color: #e2e8f0; padding: 2px 6px; border-radius: 3px; font-size: 12px; font-weight: 600;">SELLER / TARGET</span>
            </div>
            <div style="margin-bottom: 6px;">
                 <span style="font-weight: 700; color: #0f172a;">Confidence:</span> High / Medium / Low
            </div>
            <div>
                <b>Rationale:</b> [1 sentence summary of why they are a target, citing the {spi} SPI score]
            </div>
        </div>

        <!-- Section 3: Next 90 Days -->
        <h5 style="color: #444; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 8px;">
            NEXT 90 DAYS
        </h5>
        <p style="font-size: 13px; line-height: 1.5; margin-bottom: 15px;">
            [Predict specific upcoming events: Earnings surprise, Debt maturity, Activist campaign, or Strategic review announcement.]
        </p>

        <!-- Section 4: Deal Usage -->
        <h5 style="color: #444; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 8px;">
            DEAL USAGE
        </h5>
        <div style="font-size: 13px; display: flex; gap: 10px;">
            <div style="flex: 1; border: 1px solid #cff4fc; background-color: #f0faff; padding: 8px; border-radius: 4px;">
                <div style="font-weight: 700; color: #055160; font-size: 11px; text-transform: uppercase; margin-bottom: 4px;">Recommended</div>
                [Specific Deal Type: e.g. LBO]
            </div>
            <div style="flex: 1; border: 1px solid #f8d7da; background-color: #fef1f2; padding: 8px; border-radius: 4px;">
                <div style="font-weight: 700; color: #842029; font-size: 11px; text-transform: uppercase; margin-bottom: 4px;">Avoid</div>
                [Specific Deal Type: e.g. Merger]
            </div>
        </div>
    </div>
    
    **STRICT RULES**:
    1. Return ONLY raw HTML.
    2. Be specific and data-driven.
    3. Do NOT mention "Intralinks" or "Client". Focus on the company ({ticker}).
    """
    return prompt

def analyze_company(ticker, type, context):
    """
    Performs a deep dive analysis using Gemini Pro (or Flash) model.
    UPDATED: Uses google-genai SDK (v1.0+) for Cloud Run compatibility.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "<p>Error: Gemini API Key not found.</p>"
        
    try:
        client = genai.Client(api_key=api_key)
        
        # Use Flash for speed (matching project standard)
        # Using 2.0 Flash as it is stable in the new SDK
        model_name = 'gemini-2.0-flash-exp' 
        
        # Select Prompt Builder based on Type
        if type == 'radar_target':
            prompt = build_radar_dossier_prompt(ticker, context)
        else:
            # Default to Banker Deep Dive (Deal Command)
            prompt = build_deep_dive_prompt(ticker, type, context)
        
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        
        # Parse response (handle markdown wrapping if present)
        text = response.text
        if "```html" in text:
            text = text.replace("```html", "").replace("```", "")
        elif "```" in text:
            text = text.replace("```", "")
            
        return text.strip()

    except Exception as e:
        print(f"Gemini Deep Dive Error: {e}")
        return f"<p class='text-muted'>AI Analysis unavailable: {str(e)}</p>"
