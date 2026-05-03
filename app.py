import os
import json
import requests
from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "myshop2024")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
BIZ_NAME = os.environ.get("BIZ_NAME", "Our Shop")
BIZ_PRODUCT = os.environ.get("BIZ_PRODUCT", "products")
BIZ_EXTRA = os.environ.get("BIZ_EXTRA", "")

@app.route("/")
def home():
    return "WORKING!", 200

@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if change.get("field") == "feed" and value.get("item") == "comment":
                    comment_id = value.get("comment_id")
                    comment_text = value.get("message", "")
                    from_id = value.get("from", {}).get("id", "")
                    page_id = entry.get("id", "")
                    if from_id == page_id or not comment_id or not comment_text:
                        continue
                    try:
                        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                        msg = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=300,
                            system=f"You are a social media manager for {BIZ_NAME} selling {BIZ_PRODUCT}. {BIZ_EXTRA}. Reply to customer comments in Bengali only. Be friendly and brief (3-4 lines). Return only the reply text.",
                            messages=[{"role": "user", "content": f"Customer comment: {comment_text}"}]
                        )
                        reply = msg.content[0].text
                        requests.post(
                            f"https://graph.facebook.com/v19.0/{comment_id}/comments",
                            data={"message": reply, "access_token": PAGE_ACCESS_TOKEN}
                        )
                    except Exception as e:
                        print(f"Error: {e}")
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
