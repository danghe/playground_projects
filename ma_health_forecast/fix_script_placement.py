
import os

target_file = r"d:/00Intralinks/M&A Forecast Project/ma_health_forecast_project/ma_health_forecast/templates/deal_radar.html"

with open(target_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the broken structure: </body>\n</html> followed by raw JS
# We need to:
# 1. Remove the premature </body></html>
# 2. Add <script> tag with all JS
# 3. Close properly with </script></body></html>

# Locate the problem
marker = "<!-- Modal Removed -->"
if marker not in content:
    print("Error: Marker not found")
    exit(1)

# Split at the marker
parts = content.split(marker)
header = parts[0] + marker + "\n"

# Now find where the actual JS starts (after </html>)
js_marker = "// Default View"
if js_marker not in content:
    print("Error: JS marker not found")
    exit(1)

# Get all JS content
js_start = content.find(js_marker)
js_content = content[js_start:]

# Remove trailing </script></body></html> if present from prior patches
js_content = js_content.replace("</script>", "").replace("</body>", "").replace("</html>", "").strip()

# Build the correct structure
final_content = header + """
<script>
""" + js_content + """
</script>
</body>
</html>
"""

with open(target_file, 'w', encoding='utf-8') as f:
    f.write(final_content)

print(f"Successfully fixed script placement in {target_file}")
