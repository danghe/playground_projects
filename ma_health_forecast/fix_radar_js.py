
import os

target_file = r"d:/00Intralinks/M&A Forecast Project/ma_health_forecast_project/ma_health_forecast/templates/deal_radar.html"

new_js = r"""
async function generateBrief(force = false) {
    console.log("[Client] Generating Brief. SubIndustry:", activeSubIndustry, "Force:", force);
    const container = document.getElementById('briefContainer');
    const meta = document.getElementById('briefMeta');
    
    // Smooth scroll
    container.scrollIntoView({ behavior: 'smooth', block: 'center' });
    
    container.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary mb-3" role="status"></div>
            <p class="text-muted">Analyzing Market Regime & ${activeSubIndustry} Drivers...</p>
        </div>
    `;

    try {
        const response = await fetch('/api/industry-brief', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sector: "{{ sector }}", // Jinja injected
                sub_industry: activeSubIndustry,
                force_refresh: force
            })
        });
        
        const result = await response.json();
        
        if (result.error) {
            container.innerHTML = `<div class="alert alert-danger">AI Service Error: ${result.error}</div>`;
            return;
        }
        
        const data = result.brief;
        const isCached = result.cached;
        
        // Render
        let html = `<div class="row">
            <div class="col-md-6 border-end border-secondary border-opacity-25">`;
        
        // Col 1: Takeaways & Guidance
        if (data.executive_takeaways) {
            html += `<h6 class="text-uppercase text-warning fw-bold mb-2 small">Executive Takeaways</h6>
                     <ul class="mb-3 text-light small">
                        ${data.executive_takeaways.map(t => `<li>${t}</li>`).join('')}
                     </ul>`;
        }
        
        if (data.regime_guidance) {
            html += `<div class="bg-secondary bg-opacity-10 p-2 rounded mb-3">
                        <h6 class="fw-bold mb-1 small text-light">Regime Guidance</h6>
                        <p class="mb-0 small text-white-50">${data.regime_guidance}</p>
                     </div>`;
        }
        
        html += `</div><div class="col-md-6 ps-md-3">`;
        
        // Col 2: Dynamics & Playbook
        if (data.industry_dynamics) {
            html += `<h6 class="text-uppercase text-info fw-bold mb-2 small">Industry Dynamics</h6>
                     <p class="small text-muted mb-3">${data.industry_dynamics}</p>`;
        }
        
        if (data.playbook) {
             html += `<h6 class="text-uppercase text-muted fw-bold mb-2 small">Strategic Playbook</h6>
                      <div class="d-flex gap-2">
                            <div class="border border-secondary border-opacity-25 p-2 rounded flex-fill">
                                <span class="badge bg-secondary mb-1" style="font-size:0.6rem">CEO</span>
                                <p class="small mb-0 text-white-50" style="font-size:0.75rem">${data.playbook.ceo}</p>
                            </div>
                            <div class="border border-secondary border-opacity-25 p-2 rounded flex-fill">
                                <span class="badge bg-primary mb-1" style="font-size:0.6rem">Banker</span>
                                <p class="small mb-0 text-white-50" style="font-size:0.75rem">${data.playbook.banker}</p>
                            </div>
                     </div>`;
        }
        
        html += `</div></div>`;
        
        container.innerHTML = html;
        
        // Meta
        const timestamp = new Date(result.metadata.created_at).toLocaleTimeString();
        meta.innerHTML = isCached 
            ? `<i class="bi bi-hdd-network me-1"></i>Loaded from cache (${timestamp})`
            : `<i class="bi bi-lightning-charge me-1"></i>Generated live (${timestamp})`;
            
    } catch (e) {
        container.innerHTML = `<div class="alert alert-danger">Network Error: ${e.message}</div>`;
    }
}
"""

with open(target_file, 'r', encoding='utf-8') as f:
    content = f.read()

marker = "// AI Brief Logic"
if marker not in content:
    print("Error: Marker not found")
    exit(1)

parts = content.split(marker)
header = parts[0] + marker + "\n"

# Rewrite
final_content = header + new_js + "\n</script>\n</body>\n</html>"

with open(target_file, 'w', encoding='utf-8') as f:
    f.write(final_content)

print(f"Successfully patched {target_file}")
