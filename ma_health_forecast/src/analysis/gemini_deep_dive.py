
import google.generativeai as genai
import os
import time

def analyze_company(ticker, type, context):
    """
    Performs a deep dive analysis using Gemini Pro (or Flash) model
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "<p>Error: Gemini API Key not found.</p>"
        
    genai.configure(api_key=api_key)
    
    # Use Flash for speed as requested (matching project standard)
    model = genai.GenerativeModel('gemini-3-flash-preview') 

    prompt = f"""
    Act as a Tier-1 M&A Investment Banker.
    Perform a "Deep Dive" strategic assessment on the following company:
    
    **Target**: {ticker} ({context.get('name', 'Unknown')})
    **Role**: {type.upper()} ({'Acquirer' if type == 'buyer' else 'Target Candidate'})
    **Sector**: {context.get('sub_sector', 'General')}
    
    **Context Data**:
    {context}
    
    **Instructions**:
    1. Augment this with your internal knowledge of the company's recent strategic moves, earnings calls, and market position.
    2. **CRITICAL**: Incorporate insights from trustworthy financial sources (e.g. 10-K filings, reputable news) to validate your assessment.
    3. Assess the rationale for them being a {type.upper()}. 
       - If SELLER: Why should they sell now? Who acts as the buyer? What is the "Forced" vs "Strategic" angle?
       - If BUYER: What is their M&A mandate? Do they have capacity? What should they buy?
    3. Provide a "Banker's View" summary in HTML format (no markdown code blocks, just raw HTML tags like <h5>, <p>, <ul>).
    4. Keep it concise (under 200 words) but insight-dense. Use bolding for key metrics.
    
    **Format**:
    <h5>Strategic Rationale</h5>
    <p>...analysis...</p>
    <h5>Key Risks / Opportunities</h5>
    <ul>
      <li>...</li>
    </ul>
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.replace("```html", "").replace("```", "")
    except Exception as e:
        print(f"Gemini Error: {e}")
        return f"<p class='text-muted'>AI Analysis unavailable: {str(e)}</p>"
