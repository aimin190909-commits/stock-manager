from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify, send_file
import csv, os, io
from datetime import datetime
from functools import wraps
from openpyxl import Workbook

# ------------------ Configuration ------------------
app = Flask(__name__)
app.secret_key = "change_this_secret_in_production"

ADMIN_ID = "sekwang84"
ADMIN_PW = "989893"

CSV_FILE = "inventory.csv"
LOG_FILE = "log.csv"

inventory = {}
log_data = []

# ------------------ Helpers ------------------
def load_inventory():
    inventory.clear()
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                name = row[0]
                qty = int(row[1]) if len(row) > 1 and row[1].isdigit() else 0
                date = row[2] if len(row) > 2 else ""
                inventory[name] = {"quantity": qty, "date": date}

def save_inventory():
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for name, data in inventory.items():
            writer.writerow([name, data["quantity"], data["date"]])

def load_log():
    log_data.clear()
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                log_data.append(row)

def save_log(action, name, change, prev=""):
    entry = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), action, name, str(change), str(prev)]
    log_data.append(entry)
    with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(log_data)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated

load_inventory()
load_log()

# ------------------ Templates ------------------
BASE_TEMPLATE = """
<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
  <title>재고 관리</title>
  <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
  <style>
    body { background:#fafafa; font-family:-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, Arial; }
    .card { border:none; border-radius:18px; background:white; box-shadow:0 6px 20px rgba(0,0,0,0.06); }
    .brand { font-weight:600; color:#111; }
    .btn-primary { background:#007aff; border:none; }
    .btn-primary:hover { background:#005fdb; }
    .btn-danger { background:#ff3b30; border:none; }
    .btn-danger:hover { background:#d92a22; }
    .table thead th { background:#f2f2f7; border-bottom:1px solid #e0e0e0; color:#333; }
    .table tbody td { vertical-align:middle; }
    input, button { border-radius:10px !important; }
  </style>
</head>
<body>
<div class=\"container py-4\">
  <div class=\"d-flex justify-content-between align-items-center mb-4\">
    <h1 class=\"h4 brand\">📦 재고 관리</h1>
    {% if session.admin %}
      <a class=\"btn btn-outline-secondary btn-sm\" href=\"{{ url_for('logout') }}\">로그아웃</a>
    {% else %}
      <a class=\"btn btn-primary btn-sm\" href=\"{{ url_for('login') }}\">관리자 로그인</a>
    {% endif %}
  </div>

  <div class=\"card p-4 mb-4\">
    <form method=\"post\" action=\"{{ url_for('change') }}\">
      <div class=\"row g-2\">
        <div class=\"col-12 col-md-4\"><input name=\"name\" class=\"form-control\" placeholder=\"상품명\" required></div>
        <div class=\"col-6 col-md-3\"><input name=\"quantity\" type=\"number\" class=\"form-control\" value=\"1\" min=\"1\" required></div>
        <div class=\"col-6 col-md-3\"><input name=\"date\" type=\"date\" class=\"form-control\" required></div>
        <div class=\"col-6 col-md-1 d-grid\"><button name=\"action\" value=\"in\" class=\"btn btn-primary\">입고</button></div>
        <div class=\"col-6 col-md-1 d-grid\"><button name=\"action\" value=\"out\" class=\"btn btn-danger\">출고</button></div>
      </div>
    </form>
  </div>

  <div class=\"card p-3\">
    <table class=\"table table-hover text-center\">
      <thead><tr><th>상품명</th><th>수량</th><th>입고날짜</th><th>조정</th><th>삭제</th></tr></thead>
      <tbody>
        {% for name, data in inventory.items() %}
        <tr>
          <td>{{ name }}</td>
          <td>{{ data.quantity }}</td>
          <td>{{ data.date }}</td>
          <td>
            <a href=\"#\" class=\"btn btn-primary btn-sm\" onclick=\"location.href='{{ url_for('api_update') }}?name={{ name }}&action=plus'\">＋</a>
            <a href=\"#\" class=\"btn btn-danger btn-sm\" onclick=\"location.href='{{ url_for('api_update') }}?name={{ name }}&action=minus'\">－</a>
          </td>
          <td><a href=\"{{ url_for('api_delete') }}?name={{ name }}\" class=\"text-danger\">삭제</a></td>
        </tr>
        {% endfor %}
        {% if inventory|length == 0 %}
          <tr><td colspan=\"5\" class=\"text-muted\">등록된 상품이 없습니다.</td></tr>
        {% endif %}
      </tbody>
    </table>
  </div>

</div>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>로그인</title>
<link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css' rel='stylesheet'>
<style>
 body{background:#fafafa; font-family:-apple-system, BlinkMacSystemFont;}
 .card{border:none; border-radius:18px; box-shadow:0 6px 20px rgba(0,0,0,0.06);}
 .btn-primary{ background:#007aff; border:none; }
</style></head>
<body class='d-flex justify-content-center align-items-center' style='min-height:100vh;'>
<div class='card p-4' style='width:320px;'>
<h5 class='mb-3'>관리자 로그인</h5>
{% if error %}<div class='alert alert-danger'>{{ error }}</div>{% endif %}
<form method='post'>
<input name='id' class='form-control mb-2' placeholder='아이디' required>
<input name='pw' class='form-control mb-3' type='password' placeholder='비밀번호' required>
<button class='btn btn-primary w-100'>로그인</button>
</form>
</div></body></html>
"""

# ------------------ Routes ------------------
@app.route("/")
def index():
    return render_template_string(BASE_TEMPLATE, inventory=inventory)

@app.route("/login", methods=["GET","POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form.get("id") == ADMIN_ID and request.form.get("pw") == ADMIN_PW:
            session["admin"] = ADMIN_ID
            return redirect(url_for("index"))
        else:
            error="아이디 또는 비밀번호 오류"
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route("/logout")
def logout():
    session.pop("admin",None)
    return redirect(url_for("index"))

@app.route("/change", methods=["POST"])
