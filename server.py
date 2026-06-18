import glob, os
from flask import Flask, jsonify, send_from_directory
from dashboard import detect_format, load_long, pivot_long, build_long, load_wide, pivot_wide, build_wide

app      = Flask(__name__)
BASE_DIR = os.path.dirname(__file__)
LOGS_DIR = os.path.join(BASE_DIR, "logs")

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "template.html")

@app.route("/<path:filename>")
def static_file(filename):
    return send_from_directory(BASE_DIR, filename)

@app.route("/api/logs")
def list_logs():
    names = sorted(
        os.path.basename(p).replace(".csv", "")
        for p in glob.glob(os.path.join(LOGS_DIR, "*.csv"))
    )
    return jsonify(names)

@app.route("/api/logs/<name>")
def get_log(name):
    path = os.path.join(LOGS_DIR, name + ".csv")
    if not os.path.exists(path):
        return jsonify({"error": "not found"}), 404
    fmt = detect_format(path)
    try:
        if fmt == "long":
            tl, ad, m = build_long(pivot_long(load_long(path)))
        elif fmt == "wide":
            tl, ad, m = build_wide(pivot_wide(load_wide(path)))
        else:
            return jsonify({"error": "unknown format"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"timeline": tl, "all": ad, "meta": m})

if __name__ == "__main__":
    print("BimmerLink running → http://localhost:8000")
    app.run(port=8000, debug=True)
