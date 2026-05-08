# run.py

import os
from datetime import datetime

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)

# =========================
# CONFIG
# =========================

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "jwt-secret")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///taskflow.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# =========================
# MODELS
# =========================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(120), unique=True, nullable=False)

    password = db.Column(db.String(255), nullable=False)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(255), nullable=False)

    description = db.Column(db.Text)

    priority = db.Column(db.String(50), default="medium")

    completed = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

# =========================
# HELPERS
# =========================

def task_to_dict(task):
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "completed": task.completed,
        "created_at": task.created_at.isoformat(),
        "user_id": task.user_id
    }

# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return jsonify({
        "message": "TaskFlow API Running"
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy"
    })


# =========================
# AUTH
# =========================

@app.route("/register", methods=["POST"])
def register():

    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({
            "error": "username and password required"
        }), 400

    existing_user = User.query.filter_by(
        username=username
    ).first()

    if existing_user:
        return jsonify({
            "error": "user already exists"
        }), 409

    hashed_password = generate_password_hash(password)

    user = User(
        username=username,
        password=hashed_password
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "user registered successfully"
    }), 201


@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(
        username=username
    ).first()

    if not user:
        return jsonify({
            "error": "invalid credentials"
        }), 401

    if not check_password_hash(user.password, password):
        return jsonify({
            "error": "invalid credentials"
        }), 401

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "access_token": token
    })

# =========================
# TASK CRUD
# =========================

@app.route("/tasks", methods=["POST"])
@jwt_required()
def create_task():

    user_id = get_jwt_identity()

    data = request.get_json()

    title = data.get("title")

    if not title:
        return jsonify({
            "error": "title required"
        }), 400

    task = Task(
        title=title,
        description=data.get("description"),
        priority=data.get("priority", "medium"),
        user_id=user_id
    )

    db.session.add(task)
    db.session.commit()

    return jsonify(task_to_dict(task)), 201


@app.route("/tasks", methods=["GET"])
@jwt_required()
def get_tasks():

    user_id = get_jwt_identity()

    tasks = Task.query.filter_by(
        user_id=user_id
    ).all()

    return jsonify([
        task_to_dict(task)
        for task in tasks
    ])


@app.route("/tasks/<int:task_id>", methods=["PUT"])
@jwt_required()
def update_task(task_id):

    user_id = get_jwt_identity()

    task = Task.query.filter_by(
        id=task_id,
        user_id=user_id
    ).first()

    if not task:
        return jsonify({
            "error": "task not found"
        }), 404

    data = request.get_json()

    task.title = data.get("title", task.title)

    task.description = data.get(
        "description",
        task.description
    )

    task.priority = data.get(
        "priority",
        task.priority
    )

    task.completed = data.get(
        "completed",
        task.completed
    )

    db.session.commit()

    return jsonify(task_to_dict(task))


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
@jwt_required()
def delete_task(task_id):

    user_id = get_jwt_identity()

    task = Task.query.filter_by(
        id=task_id,
        user_id=user_id
    ).first()

    if not task:
        return jsonify({
            "error": "task not found"
        }), 404

    db.session.delete(task)
    db.session.commit()

    return jsonify({
        "message": "task deleted"
    })

# =========================
# FILE UPLOAD
# =========================

@app.route("/upload", methods=["POST"])
@jwt_required()
def upload_file():

    if "file" not in request.files:
        return jsonify({
            "error": "no file uploaded"
        }), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({
            "error": "empty filename"
        }), 400

    filename = secure_filename(file.filename)

    filepath = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    file.save(filepath)

    return jsonify({
        "message": "file uploaded",
        "filename": filename,
        "path": filepath
    })

# =========================
# INIT DB
# =========================

with app.app_context():
    db.create_all()

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
