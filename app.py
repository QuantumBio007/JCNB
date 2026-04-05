"""
JCNB Outreach Email Drafter
Reads eval_set.json, sends each case to Gemini via REST API, prints and saves results.

Usage:
    1. Create a .env file with your API key:  GOOGLE_API_KEY=your-key-here
    2. pip install python-dotenv requests
    3. python app.py
"""

import json
import os
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ──────────────────────────────────────────────────────────────
MODEL = "gemini-2.5-flash"
EVAL_FILE = "eval_set.json"
OUTPUT_FILE = "results.json"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds

# ── System prompt (v1) ─────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are an email drafting assistant for JCNB Biotech Consulting.

JCNB is a specialized analytics practice focused on quantitative risk and
forecasting for oncology drug supply in fragile and middle-income South
American markets. The firm is currently in exploration mode.

JCNB offers three services:
1. Oncology Drug Shortage Risk Assessment (country/region level) —
   scenario-based risk modeling for essential oncology drugs.
2. Hospital Oncology Supply Resilience Simulation (institution level) —
   stockout, budget, and ordering simulations for individual hospitals.
3. Blockchain-Ready Data and Traceability Blueprint — designing data
   architecture for supply-chain traceability (design/advisory only,
   NOT implementation).

STRICT RULES:
- Never fabricate statistics, patient numbers, or data JCNB does not have.
- Never overstate JCNB's track record. The firm is exploring, not established.
- Never promise services outside JCNB's scope. JCNB does NOT do: pricing
  negotiation, patent work, lobbying, manufacturing, or system implementation.
- If the input is vague or requests out-of-scope work, still produce a usable
  draft but set needs_human_review to true.
- Match the requested tone. Default to professional if none is specified.

OUTPUT FORMAT (strict JSON):
{
  "subject_line": "...",
  "email_body": "...",
  "needs_human_review": true/false,
  "review_reason": "..." or null
}

Return ONLY the JSON. No markdown fences, no commentary.
"""


def build_user_prompt(case_input: dict) -> str:
    """Turn structured input fields into the user-side prompt."""
    lines = ["Draft an outreach email with these details:\n"]
    field_labels = {
        "organization": "Organization",
        "contact_role": "Contact role",
        "country": "Country",
        "problem": "Problem",
        "jcnb_service": "JCNB service to highlight",
        "tone": "Tone",
        "call_to_action": "Call to action",
        "note": "Additional note",
    }
    for key, label in field_labels.items():
        value = case_input.get(key, "")
        if value:
            lines.append(f"- {label}: {value}")
    return "\n".join(lines)


def call_llm(user_prompt: str, api_key: str) -> str:
    """Send prompt to Gemini REST API and return raw response text."""
    url = API_URL.format(model=MODEL) + f"?key={api_key}"
    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": user_prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 4096,
        },
    }

    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.post(url, json=payload, timeout=30)

        if resp.status_code == 200:
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

        if resp.status_code == 429:
            wait = RETRY_DELAY * attempt
            print(f"  [RATE LIMITED] Retrying in {wait}s (attempt {attempt}/{MAX_RETRIES})...")
            time.sleep(wait)
            continue

        # Any other error — fail fast
        resp.raise_for_status()

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries (429 rate limit)")


def parse_response(raw: str) -> dict:
    """Try to parse LLM response as JSON; return raw text on failure."""
    cleaned = raw.strip()
    # Strip markdown fences if the model ignores instructions
    if cleaned.startswith("```"):
        cleaned = "\n".join(cleaned.split("\n")[1:])
    if cleaned.endswith("```"):
        cleaned = "\n".join(cleaned.split("\n")[:-1])
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"raw_text": raw, "parse_error": True}


def run_eval():
    """Load eval set, run each case through the LLM, save results."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: Set GOOGLE_API_KEY in your .env file.")
        print("  1. Go to https://aistudio.google.com/app/apikey")
        print("  2. Create a key")
        print('  3. Create .env file with: GOOGLE_API_KEY=your-key-here')
        return

    # Quick connectivity check
    print(f"Using model: {MODEL}")
    print(f"Testing API key...")
    test_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    test_resp = requests.get(test_url, timeout=10)
    if test_resp.status_code != 200:
        print(f"ERROR: API key check failed (HTTP {test_resp.status_code})")
        print(test_resp.text[:500])
        return
    print("API key valid.\n")

    # Load eval set
    with open(EVAL_FILE) as f:
        data = json.load(f)

    results = []

    for case in data["eval_set"]:
        case_id = case["id"]
        label = case["label"]
        print(f"\n{'='*60}")
        print(f"Case {case_id}: {label}")
        print(f"{'='*60}")

        user_prompt = build_user_prompt(case["input"])
        print(f"\n[PROMPT]\n{user_prompt}\n")

        try:
            raw = call_llm(user_prompt, api_key)
            parsed = parse_response(raw)
        except Exception as e:
            print(f"[ERROR] {e}")
            parsed = {"error": str(e)}
            raw = ""

        # Display result
        if "error" in parsed:
            print(f"[FAILED] {parsed['error']}")
        elif "parse_error" in parsed:
            print(f"[WARNING] Could not parse JSON. Raw response:\n{raw}")
        else:
            print(f"[SUBJECT] {parsed.get('subject_line', 'N/A')}")
            print(f"\n[BODY]\n{parsed.get('email_body', 'N/A')}")
            print(f"\n[NEEDS REVIEW] {parsed.get('needs_human_review', 'N/A')}")
            reason = parsed.get("review_reason")
            if reason:
                print(f"[REVIEW REASON] {reason}")

        # Print criteria for manual comparison
        print(f"\n[CRITERIA TO CHECK]")
        for i, c in enumerate(case["good_output_criteria"], 1):
            print(f"  {i}. {c}")

        results.append({
            "id": case_id,
            "label": label,
            "type": case["type"],
            "prompt_sent": user_prompt,
            "llm_response": parsed,
            "good_output_criteria": case["good_output_criteria"],
            "pass": None,  # YOU fill this in after reviewing
            "notes": "",   # YOUR notes on what worked / failed
        })

        # Small delay between calls to avoid rate limits
        time.sleep(2)

    # Save results
    output = {
        "model": MODEL,
        "timestamp": datetime.now().isoformat(),
        "prompt_version": "v1",
        "results": results,
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Done. {len(results)} cases processed.")
    print(f"Results saved to {OUTPUT_FILE}")
    print(f"Review each case, then fill in 'pass' and 'notes' in {OUTPUT_FILE}")


def main():
    run_eval()


if __name__ == "__main__":
    main()
