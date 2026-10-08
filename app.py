from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
from pathlib import Path
from datetime import date

app = Flask(__name__)
app.secret_key = "ess-student-demo-secret-change-before-production"
DB_PATH = Path(__file__).with_name("ess.db")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('EMPLOYEE','HR','ADMIN')),
        employee_id TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        department TEXT NOT NULL,
        designation TEXT NOT NULL,
        phone TEXT DEFAULT '',
        joining_date TEXT DEFAULT '',
        status TEXT DEFAULT 'Active'
    );

    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT NOT NULL,
        attendance_date TEXT NOT NULL,
        status TEXT NOT NULL,
        UNIQUE(employee_id, attendance_date)
    );

    CREATE TABLE IF NOT EXISTS leaves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT NOT NULL,
        leave_type TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        reason TEXT NOT NULL,
        status TEXT DEFAULT 'Pending'
    );

    CREATE TABLE IF NOT EXISTS payroll (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT NOT NULL,
        month TEXT NOT NULL,
        basic REAL NOT NULL,
        allowances REAL NOT NULL,
        deductions REAL NOT NULL,
        net_salary REAL NOT NULL
    );
    """)

    employees = [
        ("EMP-1024","Aarav Sharma","aarav@ess.com","Engineering","Software Engineer","9876500011","2025-07-10"),
        ("EMP-1025","Meera Iyer","meera@ess.com","Human Resources","HR Executive","9876500012","2024-09-02"),
        ("EMP-1026","Kabir Khan","kabir@ess.com","Finance","Payroll Analyst","9876500013","2025-01-15"),
        ("EMP-1027","Ananya Rao","ananya@ess.com","Engineering","Frontend Developer","9876500014","2025-08-21"),
        ("EMP-1028","Rohan Verma","rohan@ess.com","Operations","Operations Executive","9876500015","2024-11-11"),
    ]
    for e in employees:
        conn.execute("""INSERT OR IGNORE INTO employees
            (employee_id,name,email,department,designation,phone,joining_date)
            VALUES (?,?,?,?,?,?,?)""", e)

    users = [
        ("employee@ess.com", "employee123", "EMPLOYEE", "EMP-1024"),
        ("hr@ess.com", "hr123", "HR", "EMP-1025"),
        ("admin@ess.com", "admin123", "ADMIN", None),
    ]
    for email, password, role, employee_id in users:
        conn.execute("""INSERT OR IGNORE INTO users
            (email,password_hash,role,employee_id) VALUES (?,?,?,?)""",
            (email, generate_password_hash(password), role, employee_id))

    today = date.today().isoformat()
    for emp_id in [e[0] for e in employees]:
        conn.execute("""INSERT OR IGNORE INTO attendance
            (employee_id,attendance_date,status) VALUES (?,?,?)""",
            (emp_id, today, "Present"))

    payroll_rows = [
        ("EMP-1024","September 2026",65000,12000,4500,72500),
        ("EMP-1025","September 2026",52000,9000,3200,57800),
        ("EMP-1026","September 2026",58000,10000,3500,64500),
        ("EMP-1027","September 2026",60000,11000,4000,67000),
        ("EMP-1028","September 2026",48000,8000,2800,53200),
    ]
    for row in payroll_rows:
        conn.execute("""INSERT OR IGNORE INTO payroll
            (employee_id,month,basic,allowances,deductions,net_salary)
            VALUES (?,?,?,?,?,?)""", row)

    conn.commit()
    conn.close()


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapper
    return decorator


def current_employee_id():
    return session.get("employee_id")


@app.context_processor
def inject_user():
    return {
        "current_role": session.get("role"),
        "current_email": session.get("email"),
        "current_employee_id": session.get("employee_id")
    }


@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("dashboard")) if "user_id" in session else redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            session["role"] = user["role"]
            session["employee_id"] = user["employee_id"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = db()
    if session["role"] == "EMPLOYEE":
        emp_id = current_employee_id()
        employee = conn.execute("SELECT * FROM employees WHERE employee_id=?", (emp_id,)).fetchone()
        attendance = conn.execute("""SELECT * FROM attendance WHERE employee_id=?
                                     ORDER BY attendance_date DESC LIMIT 7""", (emp_id,)).fetchall()
        leaves = conn.execute("""SELECT * FROM leaves WHERE employee_id=?
                                 ORDER BY id DESC LIMIT 5""", (emp_id,)).fetchall()
        payroll = conn.execute("""SELECT * FROM payroll WHERE employee_id=?
                                  ORDER BY id DESC LIMIT 3""", (emp_id,)).fetchall()
        conn.close()
        return render_template("dashboard_employee.html", employee=employee,
                               attendance=attendance, leaves=leaves, payroll=payroll)

    stats = {
        "employees": conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0],
        "pending_leaves": conn.execute("SELECT COUNT(*) FROM leaves WHERE status='Pending'").fetchone()[0],
        "present_today": conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE attendance_date=? AND status='Present'",
            (date.today().isoformat(),)).fetchone()[0],
        "payroll_total": conn.execute("SELECT COALESCE(SUM(net_salary),0) FROM payroll").fetchone()[0]
    }
    recent_leaves = conn.execute("""SELECT l.*, e.name FROM leaves l
                                    JOIN employees e ON e.employee_id=l.employee_id
                                    ORDER BY l.id DESC LIMIT 5""").fetchall()
    conn.close()
    return render_template("dashboard_staff.html", stats=stats, recent_leaves=recent_leaves)


@app.route("/profile")
@login_required
def profile():
    conn = db()
    if session["role"] == "EMPLOYEE":
        employee = conn.execute("SELECT * FROM employees WHERE employee_id=?", (current_employee_id(),)).fetchone()
    else:
        employee = conn.execute("SELECT * FROM employees WHERE employee_id=?", (current_employee_id(),)).fetchone() if current_employee_id() else None
    conn.close()
    return render_template("profile.html", employee=employee)


@app.route("/employees")
@role_required("HR", "ADMIN")
def employees():
    conn = db()
    rows = conn.execute("SELECT * FROM employees ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("employees.html", employees=rows)


@app.route("/employees/add", methods=["POST"])
@role_required("HR", "ADMIN")
def add_employee():
    data = request.form
    conn = db()
    try:
        conn.execute("""INSERT INTO employees
            (employee_id,name,email,department,designation,phone,joining_date)
            VALUES (?,?,?,?,?,?,?)""",
            (data["employee_id"], data["name"], data["email"], data["department"],
             data["designation"], data.get("phone",""), data.get("joining_date","")))
        conn.commit()
        flash("Employee added successfully.", "success")
    except sqlite3.IntegrityError:
        flash("Employee ID already exists.", "danger")
    finally:
        conn.close()
    return redirect(url_for("employees"))


@app.route("/attendance")
@login_required
def attendance():
    conn = db()
    if session["role"] == "EMPLOYEE":
        rows = conn.execute("""SELECT * FROM attendance WHERE employee_id=?
                               ORDER BY attendance_date DESC""", (current_employee_id(),)).fetchall()
    else:
        rows = conn.execute("""SELECT a.*, e.name FROM attendance a
                               JOIN employees e ON e.employee_id=a.employee_id
                               ORDER BY attendance_date DESC, e.name""").fetchall()
    conn.close()
    return render_template("attendance.html", attendance=rows)


@app.route("/attendance/mark/<employee_id>/<status>", methods=["POST"])
@role_required("HR", "ADMIN")
def mark_attendance(employee_id, status):
    if status not in ("Present", "Absent"):
        return "Invalid status", 400
    conn = db()
    conn.execute("""INSERT INTO attendance(employee_id,attendance_date,status)
                    VALUES(?,?,?)
                    ON CONFLICT(employee_id,attendance_date)
                    DO UPDATE SET status=excluded.status""",
                 (employee_id, date.today().isoformat(), status))
    conn.commit()
    conn.close()
    return redirect(url_for("attendance"))


@app.route("/leave", methods=["GET", "POST"])
@login_required
def leave():
    conn = db()
    if request.method == "POST":
        if session["role"] != "EMPLOYEE":
            flash("Only employees submit their own leave requests.", "danger")
            conn.close()
            return redirect(url_for("leave"))
        f = request.form
        conn.execute("""INSERT INTO leaves
            (employee_id,leave_type,start_date,end_date,reason)
            VALUES (?,?,?,?,?)""",
            (current_employee_id(), f["leave_type"], f["start_date"], f["end_date"], f["reason"]))
        conn.commit()
        flash("Leave request submitted.", "success")

    if session["role"] == "EMPLOYEE":
        rows = conn.execute("""SELECT * FROM leaves WHERE employee_id=?
                               ORDER BY id DESC""", (current_employee_id(),)).fetchall()
    else:
        rows = conn.execute("""SELECT l.*, e.name FROM leaves l
                               JOIN employees e ON e.employee_id=l.employee_id
                               ORDER BY l.id DESC""").fetchall()
    conn.close()
    return render_template("leave.html", leaves=rows)


@app.route("/leave/<int:leave_id>/<action>", methods=["POST"])
@role_required("HR", "ADMIN")
def leave_action(leave_id, action):
    if action not in ("approve", "reject"):
        return "Invalid action", 400
    status = "Approved" if action == "approve" else "Rejected"
    conn = db()
    conn.execute("UPDATE leaves SET status=? WHERE id=?", (status, leave_id))
    conn.commit()
    conn.close()
    flash(f"Leave request {status.lower()}.", "success")
    return redirect(url_for("leave"))


@app.route("/payroll")
@login_required
def payroll():
    conn = db()
    if session["role"] == "EMPLOYEE":
        rows = conn.execute("""SELECT p.*, e.name FROM payroll p
                               JOIN employees e ON e.employee_id=p.employee_id
                               WHERE p.employee_id=? ORDER BY p.id DESC""",
                            (current_employee_id(),)).fetchall()
    else:
        rows = conn.execute("""SELECT p.*, e.name FROM payroll p
                               JOIN employees e ON e.employee_id=p.employee_id
                               ORDER BY p.id DESC""").fetchall()
    total = sum(row["net_salary"] for row in rows)
    conn.close()
    return render_template("payroll.html", payroll=rows, total=total)


@app.route("/admin/users")
@role_required("ADMIN")
def user_management():
    conn = db()
    users = conn.execute("""SELECT u.id,u.email,u.role,u.employee_id,e.name
                            FROM users u LEFT JOIN employees e
                            ON e.employee_id=u.employee_id ORDER BY u.id""").fetchall()
    conn.close()
    return render_template("users.html", users=users)


@app.route("/admin/users/add", methods=["POST"])
@role_required("ADMIN")
def add_user():
    f = request.form
    password_hash = generate_password_hash(f["password"])
    conn = db()
    try:
        conn.execute("""INSERT INTO users(email,password_hash,role,employee_id)
                        VALUES(?,?,?,?)""",
                     (f["email"].strip().lower(), password_hash, f["role"], f.get("employee_id") or None))
        conn.commit()
        flash("User account created.", "success")
    except sqlite3.IntegrityError:
        flash("Email already exists.", "danger")
    finally:
        conn.close()
    return redirect(url_for("user_management"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@role_required("ADMIN")
def delete_user(user_id):
    if user_id == session["user_id"]:
        flash("You cannot delete your own active account.", "danger")
        return redirect(url_for("user_management"))
    conn = db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash("User account deleted.", "success")
    return redirect(url_for("user_management"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
