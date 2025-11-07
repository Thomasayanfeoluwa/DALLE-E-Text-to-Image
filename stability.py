import os
import time
import json
import base64
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()
STABILITY_KEY = os.getenv("STABILITY_KEY")
WORKER_TIMEOUT = int(os.getenv("WORKER_TIMEOUT", 500))
USE_ASYNC = os.getenv("USE_ASYNC", "true").lower() == "true"

if not STABILITY_KEY:
    raise Exception("Missing STABILITY_KEY environment variable")

app = Flask(__name__)

def sync_generate(prompt: str, width=512, height=512, output_format="png"):
    """
    Synchronous generation: immediate POST → image bytes response (Accept:image/*).
    Based on docs for Stable Image generation endpoint. :contentReference[oaicite:2]{index=2}
    """
    url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    headers = {
        "Authorization": f"Bearer {STABILITY_KEY}",
        "Accept": f"image/{output_format}"
    }
    payload = {
        "prompt": prompt,
        "width": width,
        "height": height
    }
    response = requests.post(url, headers=headers, json=payload)
    if not response.ok:
        raise Exception(f"HTTP {response.status_code}: {response.text}")
    image_bytes = response.content
    base64_str = base64.b64encode(image_bytes).decode("utf‑8")
    return f"data:image/{output_format};base64,{base64_str}"

def async_generate(prompt: str, width=512, height=512):
    """
    Asynchronous generation: POST returns id → poll results until ready.
    Based on docs for polling workflow. :contentReference[oaicite:3]{index=3}
    """
    url = "https://api.stability.ai/v2beta/text-to-image"
    headers = {
        "Authorization": f"Bearer {STABILITY_KEY}",
        "Accept": "application/json"
    }
    payload = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "samples": 1
    }
    response = requests.post(url, headers=headers, json=payload)
    if not response.ok:
        raise Exception(f"HTTP {response.status_code}: {response.text}")
    resp_json = response.json()
    gen_id = resp_json.get("id")
    if not gen_id:
        raise Exception("No generation id returned in async response")

    poll_url = f"https://api.stability.ai/v2beta/results/{gen_id}"
    start = time.time()
    status_code = 202
    while status_code == 202:
        time.sleep(5)
        poll_resp = requests.get(poll_url, headers={"Authorization": f"Bearer {STABILITY_KEY}"})
        status_code = poll_resp.status_code
        if not poll_resp.ok and status_code != 202:
            raise Exception(f"Polling HTTP {status_code}: {poll_resp.text}")
        if time.time() - start > WORKER_TIMEOUT:
            raise Exception(f"Timeout after {WORKER_TIMEOUT} seconds")
    result = poll_resp.json()
    base64_str = result["artifacts"][0]["base64"]
    return f"data:image/png;base64,{base64_str}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generateimages", methods=["POST"])
def generate_route():
    data = request.json or request.form
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Prompt cannot be blank"}), 400
    try:
        if USE_ASYNC:
            image_data = async_generate(prompt)
        else:
            image_data = sync_generate(prompt)
        return jsonify({"image": image_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
