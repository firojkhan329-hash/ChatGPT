from __future__ import annotations

import base64
import json
import os
import sqlite3
from datetime import datetime
from typing import Any

from flask import Flask, jsonify, request

DATABASE_PATH = os.environ.get("VISITOR_DB_PATH", "visitor_management.db")

app = Flask(__name__)


CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS branches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        role TEXT NOT NULL,
        branch_id INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY(branch_id) REFERENCES branches(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS visitors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        company TEXT,
        email TEXT,
        phone TEXT,
        branch_id INTEGER,
        status TEXT NOT NULL,
        pre_approved INTEGER NOT NULL DEFAULT 0,
        access_level TEXT,
        visit_purpose TEXT,
        scheduled_time TEXT,
        check_in_time TEXT,
        check_out_time TEXT,
        government_id TEXT,
        photo TEXT,
        id_proof TEXT,
        is_blacklisted INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(branch_id) REFERENCES branches(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        visitor_id INTEGER,
        channel TEXT NOT NULL,
        payload TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(visitor_id) REFERENCES visitors(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS paths (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        branch_id INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY(branch_id) REFERENCES branches(id)
    );
    """,
]


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        for statement in CREATE_TABLES:
            connection.execute(statement)
        connection.commit()


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def fetch_one(query: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    with get_connection() as connection:
        cursor = connection.execute(query, params)
        row = cursor.fetchone()
    return dict(row) if row else None


def validate_base64_payload(payload: str | None) -> str | None:
    if payload is None:
        return None
    try:
        base64.b64decode(payload, validate=True)
    except (base64.binascii.Error, ValueError) as exc:
        raise ValueError("Invalid base64 payload") from exc
    return payload


@app.before_first_request
def setup_database() -> None:
    init_db()


@app.route("/branches", methods=["POST"])
def create_branch() -> Any:
    data = request.get_json(force=True)
    name = data.get("name")
    location = data.get("location")
    if not name or not location:
        return jsonify({"error": "name and location are required"}), 400
    created_at = now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO branches (name, location, created_at) VALUES (?, ?, ?)",
            (name, location, created_at),
        )
        connection.commit()
    return jsonify({"id": cursor.lastrowid, "name": name, "location": location}), 201


@app.route("/users", methods=["POST"])
def create_user() -> Any:
    data = request.get_json(force=True)
    username = data.get("username")
    role = data.get("role")
    branch_id = data.get("branch_id")
    if not username or not role:
        return jsonify({"error": "username and role are required"}), 400
    created_at = now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO users (username, role, branch_id, created_at) VALUES (?, ?, ?, ?)",
            (username, role, branch_id, created_at),
        )
        connection.commit()
    return jsonify({"id": cursor.lastrowid, "username": username, "role": role}), 201


@app.route("/paths", methods=["POST"])
def create_path() -> Any:
    data = request.get_json(force=True)
    name = data.get("name")
    description = data.get("description")
    branch_id = data.get("branch_id")
    if not name:
        return jsonify({"error": "name is required"}), 400
    created_at = now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO paths (name, description, branch_id, created_at) VALUES (?, ?, ?, ?)",
            (name, description, branch_id, created_at),
        )
        connection.commit()
    return jsonify({"id": cursor.lastrowid, "name": name, "description": description}), 201


def create_visitor(payload: dict[str, Any], status: str, pre_approved: bool) -> tuple[dict[str, Any], int]:
    full_name = payload.get("full_name")
    if not full_name:
        return {"error": "full_name is required"}, 400
    government_id = payload.get("government_id")
    photo = payload.get("photo")
    id_proof = payload.get("id_proof")
    try:
        photo = validate_base64_payload(photo)
        id_proof = validate_base64_payload(id_proof)
    except ValueError as exc:
        return {"error": str(exc)}, 400
    created_at = now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO visitors (
                full_name,
                company,
                email,
                phone,
                branch_id,
                status,
                pre_approved,
                access_level,
                visit_purpose,
                scheduled_time,
                check_in_time,
                check_out_time,
                government_id,
                photo,
                id_proof,
                is_blacklisted,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                full_name,
                payload.get("company"),
                payload.get("email"),
                payload.get("phone"),
                payload.get("branch_id"),
                status,
                1 if pre_approved else 0,
                payload.get("access_level"),
                payload.get("visit_purpose"),
                payload.get("scheduled_time"),
                payload.get("check_in_time"),
                payload.get("check_out_time"),
                government_id,
                photo,
                id_proof,
                1 if payload.get("is_blacklisted") else 0,
                created_at,
                created_at,
            ),
        )
        connection.commit()
    return {"id": cursor.lastrowid, "status": status, "pre_approved": pre_approved}, 201


@app.route("/visitors/pre-enroll", methods=["POST"])
def pre_enroll() -> Any:
    payload = request.get_json(force=True)
    response, status = create_visitor(payload, status="pre_enrolled", pre_approved=False)
    return jsonify(response), status


@app.route("/visitors/pre-approved", methods=["POST"])
def pre_approved() -> Any:
    payload = request.get_json(force=True)
    response, status = create_visitor(payload, status="pre_approved", pre_approved=True)
    return jsonify(response), status


@app.route("/visitors/walk-in", methods=["POST"])
def walk_in() -> Any:
    payload = request.get_json(force=True)
    payload["check_in_time"] = payload.get("check_in_time") or now_iso()
    response, status = create_visitor(payload, status="checked_in", pre_approved=False)
    return jsonify(response), status


def update_visitor_status(visitor_id: int, status: str) -> tuple[dict[str, Any], int]:
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE visitors SET status = ?, updated_at = ? WHERE id = ?",
            (status, now_iso(), visitor_id),
        )
        connection.commit()
    if cursor.rowcount == 0:
        return {"error": "visitor not found"}, 404
    return {"id": visitor_id, "status": status}, 200


@app.route("/visitors/<int:visitor_id>/approve", methods=["POST"])
def approve(visitor_id: int) -> Any:
    response, status = update_visitor_status(visitor_id, "approved")
    return jsonify(response), status


@app.route("/visitors/<int:visitor_id>/deny", methods=["POST"])
def deny(visitor_id: int) -> Any:
    response, status = update_visitor_status(visitor_id, "denied")
    return jsonify(response), status


@app.route("/visitors/<int:visitor_id>/blacklist", methods=["POST"])
def blacklist(visitor_id: int) -> Any:
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE visitors SET is_blacklisted = 1, updated_at = ? WHERE id = ?",
            (now_iso(), visitor_id),
        )
        connection.commit()
    if cursor.rowcount == 0:
        return jsonify({"error": "visitor not found"}), 404
    return jsonify({"id": visitor_id, "is_blacklisted": True}), 200


@app.route("/visitors/<int:visitor_id>/photo", methods=["POST"])
def upload_photo(visitor_id: int) -> Any:
    payload = request.get_json(force=True)
    photo = payload.get("photo")
    try:
        photo = validate_base64_payload(photo)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE visitors SET photo = ?, updated_at = ? WHERE id = ?",
            (photo, now_iso(), visitor_id),
        )
        connection.commit()
    if cursor.rowcount == 0:
        return jsonify({"error": "visitor not found"}), 404
    return jsonify({"id": visitor_id, "photo_updated": True}), 200


@app.route("/visitors/<int:visitor_id>/id-proof", methods=["POST"])
def upload_id_proof(visitor_id: int) -> Any:
    payload = request.get_json(force=True)
    id_proof = payload.get("id_proof")
    try:
        id_proof = validate_base64_payload(id_proof)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE visitors SET id_proof = ?, updated_at = ? WHERE id = ?",
            (id_proof, now_iso(), visitor_id),
        )
        connection.commit()
    if cursor.rowcount == 0:
        return jsonify({"error": "visitor not found"}), 404
    return jsonify({"id": visitor_id, "id_proof_updated": True}), 200


@app.route("/access-control/sync", methods=["POST"])
def access_control_sync() -> Any:
    payload = request.get_json(force=True)
    visitor_id = payload.get("visitor_id")
    access_level = payload.get("access_level")
    if not visitor_id or not access_level:
        return jsonify({"error": "visitor_id and access_level are required"}), 400
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE visitors SET access_level = ?, updated_at = ? WHERE id = ?",
            (access_level, now_iso(), visitor_id),
        )
        connection.commit()
    if cursor.rowcount == 0:
        return jsonify({"error": "visitor not found"}), 404
    return jsonify({"id": visitor_id, "access_level": access_level}), 200


@app.route("/badges/print", methods=["POST"])
def print_badge() -> Any:
    payload = request.get_json(force=True)
    visitor_id = payload.get("visitor_id")
    if not visitor_id:
        return jsonify({"error": "visitor_id is required"}), 400
    visitor = fetch_one("SELECT full_name, status FROM visitors WHERE id = ?", (visitor_id,))
    if not visitor:
        return jsonify({"error": "visitor not found"}), 404
    return jsonify({"id": visitor_id, "badge": f"Badge for {visitor['full_name']}"}), 200


@app.route("/notifications/email", methods=["POST"])
def send_email() -> Any:
    payload = request.get_json(force=True)
    visitor_id = payload.get("visitor_id")
    message = payload.get("message")
    if not visitor_id or not message:
        return jsonify({"error": "visitor_id and message are required"}), 400
    created_at = now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO notifications (visitor_id, channel, payload, created_at) VALUES (?, ?, ?, ?)",
            (visitor_id, "email", json.dumps({"message": message}), created_at),
        )
        connection.commit()
    return jsonify({"id": cursor.lastrowid, "status": "queued"}), 201


@app.route("/notifications/sms", methods=["POST"])
def send_sms() -> Any:
    payload = request.get_json(force=True)
    visitor_id = payload.get("visitor_id")
    message = payload.get("message")
    if not visitor_id or not message:
        return jsonify({"error": "visitor_id and message are required"}), 400
    created_at = now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO notifications (visitor_id, channel, payload, created_at) VALUES (?, ?, ?, ?)",
            (visitor_id, "sms", json.dumps({"message": message}), created_at),
        )
        connection.commit()
    return jsonify({"id": cursor.lastrowid, "status": "queued"}), 201


@app.route("/visitors/report", methods=["GET"])
def report() -> Any:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT v.*, b.name AS branch_name
            FROM visitors v
            LEFT JOIN branches b ON v.branch_id = b.id
            ORDER BY v.created_at DESC
            """
        )
        rows = [dict(row) for row in cursor.fetchall()]
    return jsonify({"count": len(rows), "visitors": rows}), 200


@app.route("/health", methods=["GET"])
def health() -> Any:
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
