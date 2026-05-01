import os
import json
import requests
from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)

# ===== কনফিগারেশন =====
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "myshop2024")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

BIZ_NAME = os.environ.get("BIZ_NAME", "আমাদের শপ")
BIZ_PRODUCT = os.environ.get("BIZ_PRODUCT", "বিভিন্ন পণ্য")
BIZ_EXTRA = os.environ.get("BIZ_EXTRA", "")

# ===== AI দিয়ে রিপ্লাই তৈরি =====
def generate_reply(comment_text):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    system_prompt = f"""তুমি একজন বাংলাদেশি ব্যবসার সোশ্যাল মিডিয়া ম্যানেজার।
তোমার কাজ Facebook ও Instagram পেজের কাস্টমারদের কমেন্টে বাংলায় রিপ্লাই দেওয়া।

বিজনেস তথ্য:
- নাম: {BIZ_NAME}
- পণ্য: {BIZ_PRODUCT}
{f'- বিশেষ তথ্য: {BIZ_EXTRA}' if BIZ_EXTRA else ''}

নিয়ম:
- শুধু বাংলায় লিখবে
- বন্ধুত্বপূর্ণ ও পেশাদার টোন
- ৩-৫ লাইনের মধ্যে
- শুধু রিপ্লাই টেক্সট দাও"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=system_prompt,
        messages=[{"role": "user", "content": f'কাস্টমারের কমেন্ট: "{comment_text}"\n\nবাংলায় রিপ্লাই লিখো।'}]
    )
    return message.content[0].text

# ===== Facebook-এ রিপ্লাই পোস্ট করা =====
def post_reply(comment_id, reply_text):
    url = f"https://graph.facebook.com/v19.0/{comment_id}/comments"
    payload = {"message": reply_text, "access_token": PAGE_ACCESS_TOKEN}
    response = requests.post(url, data=payload)
    return response.json()

# ===== Health Check =====
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "running", "message": "AI Auto Reply Bot চালু আছে!"})

# ===== Webhook Verification =====
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    print(f"Verify attempt: mode={mode}, token={token}, challenge={challenge}")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified!")
        return challenge, 200
    else:
        print(f"Verification failed! Expected token: {VERIFY_TOKEN}, Got: {token}")
        return "Forbidden", 403

# ===== Webhook Events =====
@app.route("/webhook", methods=["POST"])
def receive_webhook():
    data = request.json
    print(f"Received: {json.dumps(data, ensure_ascii=False)}")

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if change.get("field") == "feed" and value.get("item") == "comment":
                    comment_id = value.get("comment_id")
                    comment_text = value.get("message", "")
                    from_id = value.get("from", {}).get("id", "")
                    page_id = entry.get("id", "")

                    if from_id == page_id:
                        continue

                    if comment_id and comment_text:
                        print(f"Comment: {comment_text}")
                        try:
                            reply = generate_reply(comment_text)
                            print(f"Reply: {reply}")
                            post_reply(comment_id, reply)
                        except Exception as e:
                            print(f"Error: {e}")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
