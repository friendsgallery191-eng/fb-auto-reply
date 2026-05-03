from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "WORKING!", 200

@app.route("/webhook")
def webhook():
    from flask import request
    challenge = request.args.get("hub.challenge")
    token = request.args.get("hub.verify_token")
    if token == "myshop2024":
        return challenge, 200
    return "Forbidden", 403
