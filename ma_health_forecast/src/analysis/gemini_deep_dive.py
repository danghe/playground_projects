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
    You are advising the CEO of Intralinks on the broader market landscape.
    
    Provide a **Strategic Tear Sheet** on the following MARKET PLAYER:

    **SUBJECT COMPANY**: {ticker} ({name})
    **SECTOR**: {sub_sector}
    
    **HARD DATA ANCHORS (CITE THESE)**:
    - Firepower: {firepower_str}
    - Net Leverage: {leverage_str}
    - Primary Context: {drivers}

    {role_instruction}

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
        
        # Use the new prompt builder
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
