import requests
import json
import os
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:8b"
OUTPUT_DIR = r"C:\money-machine\youtube"

def ask_ollama(prompt, model=MODEL):
    """Send a prompt to local Ollama and return the response text."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.ConnectionError:
        return "ERROR: Ollama is not running. Start it with: ollama serve"
    except Exception as e:
        return f"ERROR: {str(e)}"

def generate_topics(niche):
    """Generate 30 YouTube topic ideas for a given niche."""
    prompt = f"""You are a YouTube strategist specializing in faceless channels.

Generate 30 high-potential video topics for a faceless YouTube channel in the {niche} niche.

For each topic provide (in this exact format):

TOPIC [number]:
Title: [clickable title, under 60 chars]
Keyword: [main target keyword]
Hook: [opening line for first 15 seconds - no 'welcome' or 'in this video']
Structure:
- [point 1]
- [point 2]
- [point 3]
- [point 4]
Volume: [Low / Medium / High]
Monetization: [ads / affiliate / digital product - can list multiple]

Rules:
- Titles must be specific and curiosity-driven
- Hooks must be a statement or shocking fact, never a question starting with 'have you ever'
- Mix evergreen and trending angles
- Target 8-15 minute video length
- Must be advertiser-friendly

Niche: {niche}

Generate all 30 now:"""

    print(f"Generating topics for niche: {niche}")
    print("Sending to Ollama... (this may take 60-120 seconds on CPU)")
    result = ask_ollama(prompt)
    return result

def save_results(niche, content):
    """Save results to a timestamped file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"s1-01_{niche.replace(' ', '_')}_{timestamp}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"S1-01: Niche Research & Topic Generation\n")
        f.write(f"Niche: {niche}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("="*60 + "\n\n")
        f.write(content)
    
    print(f"\nSaved to: {filepath}")
    return filepath

def main():
    print("="*50)
    print(" S1-01: YouTube Niche Research Tool")
    print(" Running on local Ollama (no API key needed)")
    print("="*50 + "\n")

    # Check Ollama is running
    test = ask_ollama("Say: READY")
    if "ERROR" in test:
        print(test)
        print("\nFix: Open a new terminal and run: ollama serve")
        print("Then run this script again.")
        return

    print("Ollama connection: OK\n")
    niche = input("Enter your niche (e.g. personal finance, cooking, productivity): ").strip()
    
    if not niche:
        niche = "personal finance"
        print(f"Using default niche: {niche}")
    
    topics = generate_topics(niche)
    
    if "ERROR" in topics:
        print(topics)
        return
    
    filepath = save_results(niche, topics)
    
    print("\nPREVIEW (first 500 chars):")
    print("-"*40)
    print(topics[:500])
    print("-"*40)
    print(f"\nFull results saved to:\n{filepath}")
    print("\nReady for S1-02 when you say NEXT.")

if __name__ == "__main__":
    main()