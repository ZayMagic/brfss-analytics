"""
Safer example app.py
 - uses parameterized queries (prevents SQL injection)
 - uses environment variables for DB credentials
 - minimal error handling and proper connection close
"""
import os
import boto3
import json
from flask import Flask, jsonify, request, render_template
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# get secret from AWS Secrets Manager
def get_secret(secret_name, region_name="us-east-1"):
    client = boto3.client("secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=secret_name)
    secret = response["SecretString"]
    return json.loads(secret)

# use your stored secret
secrets = get_secret("brfss-db-credentials")  # replace with your secret name



# -------------- CONFIG (use env vars instead of hardcoding) --------------
DB_CONFIG = {
    "host": secrets["host"],
    "user": secrets["username"],
    "password": secrets["password"],
    "database": secrets["dbname"],
    "connection_timeout": 30,
}
# store real creds in environment variables:
#   PowerShell example:
#     $env:BRFSS_DB_PASS = "super_secret_password"

# ------------------ FRONTEND ROUTES ------------------

@app.route("/")
def home_page():
    return render_template("index.html")

@app.route("/bmi")
def bmi_page():
    return render_template("bmi.html")

@app.route("/about")
def about_page():
    return render_template("about.html")

# ------------------ API ROUTES ------------------

@app.route("/api/bmi-distribution")
def bmi_distribution():
    state = request.args.get("state")
    params = ()
    state_filter_sql = ""
    if state:
        try:
            state_int = int(state)
            state_filter_sql = " AND _STATE = %s"
            params = (state_int,)
        except ValueError:
            return jsonify({"error": "state must be an integer"}), 400

    query = f"""
        SELECT _BMI5CAT, COUNT(*) AS count
        FROM brfss_microdata
        WHERE _BMI5CAT IS NOT NULL
        {state_filter_sql}
        GROUP BY _BMI5CAT
    """

    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return jsonify(rows)
    except Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
