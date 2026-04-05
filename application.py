import os
import boto3
import pymysql
import uuid
import logging
from flask import Flask, request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from flask import redirect, url_for

logging.basicConfig(level=logging.INFO)

application = Flask(__name__)
application.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

s3 = boto3.client('s3', region_name='eu-north-1')
BUCKET_NAME = 'complaint-images-akansha'

def get_connection():
    return pymysql.connect(
        host=os.environ.get("DB_HOST") or "complaint-db.cf4igcgao0bx.eu-north-1.rds.amazonaws.com",
        user=os.environ.get("DB_USER") or "admin",
        password=os.environ.get("DB_PASSWORD") or "Admin#123",
        database=os.environ.get("DB_NAME") or "complaints_db",
        cursorclass=pymysql.cursors.Cursor
    )

# ------------------ ROUTES ------------------

@application.route("/")
def home():
    return render_template("login.html")

@application.route("/register-page")
def register_page():
    return render_template("register.html")

@application.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

from flask import session

@application.route("/admin_dashboard")
def admin_dashboard():
    return render_template("admin.html")


# ------------------ LOGIN ------------------

from flask import request, jsonify
from werkzeug.security import check_password_hash

from werkzeug.security import check_password_hash

from werkzeug.security import check_password_hash

@application.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()

        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Missing email or password"}), 400

        email = email.strip().lower()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT password, role FROM users WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()
        conn.close()

        if not user:
            return jsonify({"error": "User not found"}), 404

        db_password, role = user

        # SIMPLE CHECK
        if db_password != password:
            return jsonify({"error": "Incorrect password"}), 401

        return jsonify({
            "message": "Login successful",
            "role": role
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ------------------ REGISTER ------------------

@application.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()

        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        email = email.strip().lower()

        if not name or not email or not password:
            return jsonify({"error": "Missing fields"}), 400

        # NO HASHING (DIRECT STORE)
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
            (name, email, password, "user")
        )

        conn.commit()
        conn.close()

        return jsonify({"message": "User registered successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ ADD COMPLAINT ------------------

@application.route("/add-complaint", methods=["POST"])
def add_complaint():
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        user_id = request.form.get('user_id')
        file = request.files.get('file')

        if not title or not description or not user_id or not file:
            return jsonify({"error": "Missing required fields"}), 400

        filename = str(uuid.uuid4()) + ".jpg"

        s3.upload_fileobj(file, BUCKET_NAME, filename)

        file_url = f"https://complaint-images-akansha.s3.amazonaws.com/{filename}"

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO complaints (user_id, title, description, image_url) VALUES (%s, %s, %s, %s)",
            (user_id, title, description, file_url)
        )

        conn.commit()
        conn.close()

        return jsonify({"message": "Complaint added!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ VIEW COMPLAINTS ------------------

@application.route("/view_complaints", methods=["GET"])
def view_complaints():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM complaints")
        data = cursor.fetchall()

        conn.close()

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@application.route("/update-status", methods=["POST"])
def update_status():
    data = request.get_json()

    complaint_id = data.get("id")
    status = data.get("status")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE complaints SET status=%s WHERE id=%s",
        (status, complaint_id)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Status updated"})

from flask import session, redirect, url_for


# ------------------ MAIN ------------------

if __name__ == "__main__":
    application.run(debug=True)