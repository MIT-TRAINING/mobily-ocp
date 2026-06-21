from flask import Flask, jsonify
app = Flask(__name__)

TARIFFS = [
    {"code": "PRE-VISITOR",   "type": "prepaid",  "monthly_sar": 0,   "data_gb": 5},
    {"code": "POST-PRO-200",  "type": "postpaid", "monthly_sar": 200, "data_gb": 150},
    {"code": "POST-UNLTD-400","type": "postpaid", "monthly_sar": 400, "data_gb": "unlimited"},
]

@app.get("/health")
def health(): return jsonify(status="ok")

@app.get("/tariffs")
def tariffs(): return jsonify(TARIFFS)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)