import os
from google import genai
from google.genai import types
import pandas as pd
import json
from typing import Tuple

def gemini_forecast(history: pd.Series, steps: int = 12, rate_shock: int = 0, confidence_shock: int = 0, volatility_shock: int = 0) -> Tuple[pd.DataFrame, str]:
    """
    Generate a forecast using Google's Gemini model (via google-genai SDK).
    
    Args:
        history (pd.Series): Historical M&A Index values.
        steps (int): Number of months to forecast.
        rate_shock (int): User input for rate cut/hike (bps).
        confidence_shock (int): User input for CEO confidence (Index Pts).
        volatility_shock (int): User input for VIX/Volatility (Index Pts).
        
    Returns:
        pd.DataFrame: Forecast with columns ['forecast', 'lower80', 'upper80']
        str: Rationale/Explanation from the LLM.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
        
    client = genai.Client(api_key=api_key)
    
    # List of models to try in order of preference
    # Cascading from Best (v3/Pro) to Fastest (v2/Flash) to Legacy
    models_to_try = [
        'gemini-3-pro-preview', # Confirmed Available
        'gemini-3-flash-preview',
        'gemini-2.0-flash-exp', # Fallback
        'gemini-1.5-pro',       # Stable Fallback
    ]
    
    # Prepare Context - LIST FORMAT (Better for LLM Time Series)
    history_list = []
    for date, value in history.items():
        # Clean timestamp format to 'YYYY-MM'
        date_str = date.strftime("%Y-%m") if hasattr(date, 'strftime') else str(date)[:7]
        history_list.append(f"{date_str}: {value:.1f}")
    history_str = "\n".join(history_list)
    
    prompt = f"""
    **Role**: You are a world-renowned PhD in Economics with over 30 years of experience in Global M&A markets. You currently serve as the Chief Strategy Officer advising the CEO of **Intralinks**.

    **Goal**: Provide a strategic forecast of the "M&A Health Index" to help Intralinks leadership foresee market shifts and adjust their business strategy accordingly.

    **Context**:
    - The "M&A Health Index" is a composite score (0-100):
      - **>50**: Expansion/Boom (High Deal Flow)
      - **<50**: Contraction/Bust (Low Deal Flow)
    - **Historical Data** (Last 24 Months):
    {history_str}
    
    **Scenario Simulation (User Defined Strategic Shocks)**:
    - **Interest Rates**: {rate_shock} bps (Negative = Fed Cut / Stimulus, Positive = Rate Hike).
    - **CEO Confidence**: {confidence_shock} pts (Positive = Optimism, Negative = Pessimism).
    - **Market Volatility**: {volatility_shock} pts (Positive = High VIX/Fear, Negative = Stability).
    
    **Instructions**:
    1. **Analyze First (Chain of Thought)**: 
       - Explicitly calculate the "Net Impulse" of the provided shocks.
       - Determine if the market is trending UP, DOWN, or FLAT based on the combination of historical momentum and these new shocks.
       - *Important*: If Rate Cuts are present, apply a 3-6 month lag before the full positive effect kicks in.
       - *Important*: If Volatility is high, apply an immediate negative penalty.
    2. **Forecast**: 
       - Project the index value for the next {steps} months based on your analysis.
    3. **Strategic Narrative**: 
       - Write a high-impact Executive Briefing for the Intralinks CEO.
       - Focus on the *business implications* (e.g., "Expect a surge in due diligence activity in Q3...").

    **Output Format**:
    Return ONLY valid JSON with this exact structure (key order matters):
    {{
        "reasoning_trace": "Step 1: Analyzed shocks... Rate cut of -50bps implies...",
        "forecast": [val1, val2, ...],
        "lower80": [val1, val2, ...],
        "upper80": [val1, val2, ...],
        "rationale": "<h3>Executive Briefing for Intralinks CEO</h3><p>...</p>"
    }}
    """
    
    for model_name in models_to_try:
        try:
            print(f"=== [Gemini Forecast Service] ===", flush=True)
            print(f"> Action: Generating Forecast (Steps: {steps})", flush=True)
            print(f"> Model Attempt: {model_name}", flush=True)
            
            # New SDK usage
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            text = response.text
            
            print(f"> Status: Response Received (Length: {len(text)} chars)", flush=True)
            
            # Parse JSON (SDK might deliver it clean if response_mime_type is set, but extra safety check)
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                # Fallback clean
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]
                data = json.loads(text)

            print(f"> Result: Success (JSON Parsed)", flush=True)
            print(f"=================================\n", flush=True)
            
            # Create DataFrame
            last_date = history.index[-1]
            dates = pd.date_range(start=last_date, periods=steps + 1, freq="ME")[1:]
            
            fc_df = pd.DataFrame({
                "forecast": data["forecast"],
                "lower80": data["lower80"],
                "upper80": data["upper80"]
            }, index=dates)
            
            return fc_df, data.get("rationale", "No rationale provided.")
            
        except Exception as e:
            print(f"> WARNING: Model {model_name} failed: {e}", flush=True)
            print(f"> Retrying with next model...", flush=True)
            continue
            
    # If we reach here, all models failed
    print(f"> ERROR: All Gemini models failed. Falling back to simple linear projection.", flush=True)
    print(f"=================================\n", flush=True)
    last_val = history.iloc[-1]
    dates = pd.date_range(start=history.index[-1], periods=steps + 1, freq="ME")[1:]
    return pd.DataFrame({
        "forecast": [last_val] * steps,
        "lower80": [last_val - 5] * steps,
        "upper80": [last_val + 5] * steps
    }, index=dates), "Forecast failed: All AI models unavailable."
