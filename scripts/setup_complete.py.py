# Save as render_all_animations.py in C:\money-machine\tools\manim\
import subprocess
import sys

templates = [
    "money_counter",
    "budget_pie", 
    "savings_growth",
    "debt_waterfall",
    "income_streams",
    "credit_score"
]

for template in templates:
    print(f"\nRendering: {template}...")
    subprocess.run([
        sys.executable, "render_animation.py", template, "--quality", "medium"
    ])

print("\nAll animations rendered!")