# ESS Student Project — Role Based Access

A Flask + SQLite Employee Self Service project designed to be easy to explain in a college SDE interview.

## Roles

### Employee
- Own profile
- Own attendance
- Submit and view own leave
- View own payroll
- Cannot access HR/Admin routes

### HR
- Employee directory
- Attendance management
- Leave approval/rejection
- Workforce payroll
- Own profile

### Admin
- Everything HR can access
- User & role management
- Create/delete login accounts

## Demo accounts

- Employee: employee@ess.com / employee123
- HR: hr@ess.com / hr123
- Admin: admin@ess.com / admin123

## Run in VS Code PowerShell

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

The SQLite database is created automatically on first run.

## Interview point

Authorization is enforced on the Flask server with `login_required` and `role_required`. Hiding a menu item is not the security mechanism; unauthorized users are rejected even if they manually type a protected URL.
