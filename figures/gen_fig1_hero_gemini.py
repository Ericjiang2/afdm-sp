import base64
import json
import os
import pathlib
import time
import urllib.request
import urllib.error


HERE = pathlib.Path(__file__).resolve().parent
SPEC_PATH = HERE / "data" / "hero_figure_spec.json"
OUT_PATH = HERE / "ai_generated" / "fig1_hero_pipeline.png"
RAW_JSON_PATH = HERE / "ai_generated" / "fig1_hero_pipeline_response.json"


def build_prompt(spec):
    positive = ", ".join(spec["positive_regimes"])
    negative = spec["negative_regime"]
    return f"""
Create a professional, publication-quality academic system diagram for an IEEE wireless communications paper.

Style requirements:
- clean white background
- subtle, polished academic design
- horizontal left-to-right layout
- thick dark arrows with clear arrowheads
- rounded rectangular modules
- minimal but readable text
- no decorative clip art
- print-friendly colors
- diagram should look like a carefully designed paper figure, not a marketing poster

Figure goal:
Show that smooth mean-residual correction fails, while a frozen decision-level corrector succeeds across multiple AFDM regimes but has a clear failure boundary.

Required layout:
1. On the far left, a block labeled "AFDM Input Frame".
2. Next, a larger blue module labeled "CurrentJoint Receiver".
3. Below or attached to it, a small block labeled "Observable Trajectory Features".
4. From the receiver, split into two paths:
   - upper red path labeled "Mean-Residual Distillation" ending in a red block labeled "Fails to move hard decisions"
   - lower green path labeled "Frozen Direct-Bit Corrector" ending in a green block labeled "Train once, test on many"
5. On the right side, add a grouped box titled "Positive Regimes" with four clean items: "{positive}".
6. Next to it, add a red boundary box titled "Failure Boundary" with the item "{negative}".
7. Along the bottom, add a slim orange strip labeled "Packet-Level Utility" with two large tags: "64-bit: +3.6% to +5.7%" and "256-bit: +5.0% to +11.3%".

Text handling:
- use only the exact short labels above
- make the labels large and simple
- avoid small paragraphs

Visual hierarchy:
- blue for the base receiver
- red for the failed route and negative regime
- green for the successful frozen corrector and positive regimes
- orange for packet utility

The final result should be a clean hero figure for a paper, showing one failed route, one successful route, positive transfer regimes, and an explicit failure boundary.
""".strip()


def call_gemini(prompt):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    models = [
        ("gemini-3.1-flash-image-preview", {"aspectRatio": "16:9", "imageSize": "2K"}),
        ("gemini-2.5-flash-image", {"aspectRatio": "16:9"})
    ]

    last_error = None
    for model, image_config in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"imageConfig": image_config}
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key
            },
            method="POST"
        )
        for backoff in (2, 6, 12):
            try:
                with urllib.request.urlopen(req) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code != 429:
                    break
                time.sleep(backoff)
    if last_error is not None:
        raise last_error
    raise RuntimeError("Gemini call failed without an HTTP error")


def extract_image(response_json):
    for cand in response_json.get("candidates", []):
        content = cand.get("content", {})
        for part in content.get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    raise RuntimeError("No image data found in Gemini response")


def main():
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    prompt = build_prompt(spec)
    response_json = call_gemini(prompt)
    RAW_JSON_PATH.write_text(json.dumps(response_json, indent=2), encoding="utf-8")
    image_bytes = extract_image(response_json)
    OUT_PATH.write_bytes(image_bytes)
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
