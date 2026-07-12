import os
from pathlib import Path
import sqlite3

from flask import Flask, jsonify, render_template, request


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "challenge.db"
MAX_ROWS = 30
DEFAULT_FLAG = "UITCTF{local_flag_placeholder}"
CHALLENGE_FLAG = os.environ.get("FLAG", DEFAULT_FLAG)

app = Flask(__name__)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(
            """
            DROP TABLE IF EXISTS comments;
            DROP TABLE IF EXISTS public_directory;
            DROP TABLE IF EXISTS archive_7d2e;

            CREATE TABLE comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT NOT NULL,
                message TEXT NOT NULL
            );

            CREATE TABLE public_directory (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL
            );

            CREATE TABLE archive_7d2e (
                id INTEGER PRIMARY KEY,
                note TEXT NOT NULL,
                flag_9a61 TEXT NOT NULL
            );

            INSERT INTO comments (author, message) VALUES
                ('mina', 'The archive index was rebuilt.'),
                ('dawson', 'Comment review is still pending.'),
                ('guest', 'Sel...');

            INSERT INTO public_directory (id, title, status) VALUES
                (1, 'welcome-note', 'public'),
                (2, 'maintenance-log', 'public'),
                (3, 'archive-map', 'internal');

            """
        )
        conn.execute(
            "INSERT INTO archive_7d2e (id, note, flag_9a61) VALUES (?, ?, ?)",
            (1, "final record", CHALLENGE_FLAG),
        )
        conn.commit()
    finally:
        conn.close()


def reject(message, status=400):
    return jsonify({"ok": False, "error": message}), status


def validate_raw_body():
    raw = request.get_data(as_text=True) or ""
    lowered = raw.lower()
    for token in ("%0a", "%0d", "%09"):
        if token in lowered:
            return f"{token} is blocked."
    return None


def bad_flag_keyword(query):
    for index in range(max(0, len(query) - 3)):
        keyword = query[index : index + 4]
        if keyword.lower() == "flag" and keyword != "FLAG":
            return keyword
    return None


def build_statement(query):
    if not isinstance(query, str):
        return None, "Missing statement."

    if len(query) > 1500:
        return None, "Statement is too long."

    blocked_flag = bad_flag_keyword(query)
    if blocked_flag:
        return None, f'"{blocked_flag}" keyword is blocked.'

    checks = [
        ("%", "% is blocked."),
        ("--", "Comment markers are blocked."),
        ("/*", "Comment markers are blocked."),
        ("*/", "Comment markers are blocked."),
        ("#", "Comment markers are blocked."),
        ("*", "* is blocked."),
        (";", "Multiple statements are blocked."),
        ("\t", "Tabs are blocked."),
        (" ", "Spaces are blocked."),
    ]
    for token, message in checks:
        if token in query:
            return None, message

    lines = [line.strip() for line in query.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    lines = [line for line in lines if line]

    if len(lines) < 2:
        return None, "Statement format is blocked."

    first = lines[0].lower()
    if first not in {"select", "pragma"}:
        return None, "Only read statements are allowed."

    statement = " ".join(lines)
    lowered = statement.lower()

    if not (lowered.startswith("select ") or lowered.startswith("pragma ")):
        return None, "Only read statements are allowed."

    collapsed = " ".join(lowered.split())
    blocked_structures = {
        "pragma database_list",
        "select sql from sqlite_schema",
        "select sql from sqlite_master",
    }
    if collapsed in blocked_structures:
        return None, "Database structure is blocked."

    blocked_words = ("insert", "update", "delete", "drop", "alter", "attach", "detach", "vacuum", "replace")
    if any(word in lowered for word in blocked_words):
        return None, "Only read statements are allowed."

    return statement, None


def run_statement(statement):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(statement)
        if cursor.description is None:
            return {"columns": [], "rows": [], "truncated": False}

        columns = [item[0] for item in cursor.description]
        rows = cursor.fetchmany(MAX_ROWS + 1)
        return {
            "columns": columns,
            "rows": [[row[column] for column in columns] for row in rows[:MAX_ROWS]],
            "truncated": len(rows) > MAX_ROWS,
        }
    finally:
        conn.close()


@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/", methods=["POST"])
def execute_page():
    query = request.form.get("query", "")
    raw_error = validate_raw_body()
    if raw_error:
        return render_template("index.html", query=query, status="Command Rejected.", error=raw_error), 400

    statement, error = build_statement(query)
    if error:
        return render_template("index.html", query=query, status="Command Rejected.", error=error), 400

    try:
        result = run_statement(statement)
    except sqlite3.Error as exc:
        return render_template("index.html", query=query, status="Command Rejected.", error=str(exc)), 400

    return render_template("index.html", query=query, status="Executed.", statement=statement, result=result)


@app.route("/execute", methods=["POST"])
def execute():
    raw_error = validate_raw_body()
    if raw_error:
        return reject(raw_error)

    data = request.get_json(silent=True) or {}
    statement, error = build_statement(data.get("query", ""))
    if error:
        return reject(error)

    try:
        result = run_statement(statement)
    except sqlite3.Error as exc:
        return reject(str(exc))

    return jsonify({"ok": True, "statement": statement, **result})


init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)
