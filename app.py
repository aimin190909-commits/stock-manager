from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify, send_file
import csv, os, io
from datetime import datetime
from functools import wraps
from openpyxl import Workbook

# ------------------ Configuration ------------------
app = Flask(__name__)
app.secret_key = "change_this_secret_in_production"  # 변경 권장

ADMIN_ID = "sekwang84"
ADMIN_PW = "989893"

CSV_FILE = "inventory.csv"

# ------------------ In-memory storage ------------------
inventory = {}

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
                try:
                    qty = int(row[1])
                except:
                    qty = 0
                date = row[2] if len(row) > 2 else ""
                inventory[name] = {"quantity": qty, "date": date}

def save_inventory():
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for name, data in inventory.items():
            writer.writerow([name, data["quantity"], data["date"]])

load_inventory()

# ------------------ Login Required Decorator ------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated

# ------------------ Templates ------------------
BASE_TEMPLATE = """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>재고 관리 (Mint Pro)</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <script src="https://unpkg.com/@zxing/library@0.18.6"></script>
  <style>
    :root{--mint:#17c3a3;--mint-dark:#009e7f;}
    body{background:#f6fffb;font-family:Inter,system-ui,Segoe UI,Roboto,Arial;}
    .card{border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,0.06)}
    .brand{color:var(--mint-dark);font-weight:700}
    .btn-mint{background:var(--mint);color:#fff;border:none}
    .btn-mint:hover{background:var(--mint-dark);color:#fff}
    .table thead th{background:var(--mint-dark);color:#fff;border:none}
    .table td, .table th{vertical-align:middle}
    .big-action { font-size:18px; padding:14px 20px; border-radius:10px; }
    .in-btn { background:#17c3a3; color:white }
    .out-btn { background:#ff6b6b; color:white }
    @media (max-width:576px){
      .card{padding:12px}
      .table {font-size:13px}
    }
    #video { width:100%; height:auto; border-radius:8px; }
  </style>
</head>
<body>
<div class="container py-3">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h1 class="h4 brand">📦 재고 관리 Pro</h1>
    <div>
      {% if session.admin %}
        <span class="me-2 small text-success">관리자: {{ session.admin }}</span>
        <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('logout') }}">로그아웃</a>
      {% else %}
        <a class="btn btn-sm btn-mint" href="{{ url_for('login') }}">관리자 로그인</a>
      {% endif %}
    </div>
  </div>

  <div class="row g-3">

    <div class="col-12 col-md-4">
      <div class="card p-3">
        <form method="get" action="{{ url_for('index') }}" class="d-flex mb-2">
          <input name="search" class="form-control me-2" placeholder="상품 검색" value="{{ search|default('') }}">
          <button class="btn btn-outline-secondary">검색</button>
        </form>

        <hr>

        <h6>바코드 스캔 / 상품 등록</h6>

        <button id="openScanner" class="btn btn-outline-primary btn-sm w-100 mb-2">📷 바코드 스캔</button>

        <form method="post" action="{{ url_for('change') }}">
          <input name="name" id="p_name" class="form-control mb-2" placeholder="상품명" required>
          <div class="row mb-2 gx-2">
            <div class="col-6">
              <input name="quantity" id="p_qty" type="number" min="1" class="form-control" value="1" required>
            </div>
            <div class="col-6">
              <input name="date" type="date" class="form-control" required>
            </div>
          </div>
          <div class="d-grid gap-2">
            <button name="action" value="in" class="btn big-action in-btn" {% if not session.admin %}disabled{% endif %}>➕ 입고</button>
            <button name="action" value="out" class="btn big-action out-btn" {% if not session.admin %}disabled{% endif %}>➖ 출고</button>
          </div>
        </form>

        <hr>
        <a class="btn btn-outline-primary btn-sm w-100 mb-1" href="{{ url_for('download') }}">CSV 다운로드</a>
        <a class="btn btn-outline-success btn-sm w-100" href="{{ url_for('export_xlsx') }}">엑셀 다운로드</a>
      </div>
    </div>

    <div class="col-12 col-md-8">
      <div class="card p-0">
        <div class="p-3 d-flex justify-content-between">
          <h6 class="mb-0">전체 재고</h6>
        </div>

        <div class="table-responsive">
          <table class="table table-hover mb-0">
            <thead>
              <tr><th>상품명</th><th class="text-end">수량</th><th class="text-center">입고날짜</th><th class="text-center">조정</th><th class="text-center">삭제</th></tr>
            </thead>
            <tbody>
              {% for name, data in inventory.items() %}
              <tr data-name="{{ name|e }}">
                <td>{{ name }}</td>
                <td class="text-end qty">{{ data.quantity }}</td>
                <td class="text-center">{{ data.date }}</td>
                <td class="text-center">
                  <button class="btn btn-sm btn-outline-success btn-plus" data-name="{{ name }}">＋</button>
                  <button class="btn btn-sm btn-outline-danger btn-minus" data-name="{{ name }}">－</button>
                </td>
                <td class="text-center">
                  <button class="btn btn-sm btn-link text-danger btn-del" data-name="{{ name }}">삭제</button>
                </td>
              </tr>
              {% endfor %}

              {% if inventory|length == 0 %}
              <tr><td colspan="5" class="text-center text-muted">재고 없음</td></tr>
              {% endif %}
            </tbody>
          </table>
        </div>
      </div>
    </div>

  </div>

</div>

<div id="scannerModal" style="display:none; position:fixed; inset:0; background:#0008; align-items:center; justify-content:center;">
  <div style="background:white; padding:12px; border-radius:10px; width:95%; max-width:520px;">
    <div class="d-flex justify-content-between mb-2">
      <h6>바코드 스캔</h6>
      <button id="closeScanner" class="btn btn-sm btn-outline-secondary">닫기</button>
    </div>
    <video id="video"></video>
  </div>
</div>

<script>
async function jsonReq(url, body){
  return (await fetch(url,{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
}

function updateRow(name, qty){
  const row=document.querySelector('tr[data-name="'+name+'"]');
  if(row) row.querySelector('.qty').textContent=qty;
}

document.addEventListener('click', e=>{
  if(e.target.classList.contains('btn-plus')){
    jsonReq('/api/update',{name:e.target.dataset.name,action:'plus'}).then(r=>r.ok&&updateRow(e.target.dataset.name,r.quantity));
  }
  if(e.target.classList.contains('btn-minus')){
    jsonReq('/api/update',{name:e.target.dataset.name,action:'minus'}).then(r=>r.ok&&updateRow(e.target.dataset.name,r.quantity));
  }
  if(e.target.classList.contains('btn-del')){
    if(!confirm("삭제하시겠습니까?")) return;
    jsonReq('/api/delete',{name:e.target.dataset.name}).then(r=>{ if(r.ok) location.reload(); });
  }
});

let codeReader=null;
document.getElementById('openScanner').onclick=async()=>{
  document.getElementById('scannerModal').style.display='flex';
  if(!codeReader) codeReader=new ZXing.BrowserMultiFormatReader();
  const devices = await codeReader.listVideoInputDevices();
  codeReader.decodeFromVideoDevice(devices[0].deviceId,'video',(res)=>{
    if(res){
      document.getElementById('p_name').value=res.text;
      codeReader.reset();
      document.getElementById('scannerModal').style.display='none';
    }
  });
};
document.getElementById('closeScanner').onclick=()=>{ codeReader.reset(); document.getElementById('scannerModal').style.display='none'; };
</script>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>로그인</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light d-flex justify-content-center align-items-center" style="min-height:80vh">
<div class="card p-4" style="width:320px">
  <h5 class="mb-3 text-center">관리자 로그인</h5>
  {% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
  <form method="post">
    <input name="id" class="form-control mb-2" placeholder="아이디" required>
    <input name="pw" class="form-control mb-3" type="password" placeholder="비밀번호" required>
    <button class="btn btn-primary w-100">로그인</button>
  </form>
</div>
</body>
</html>
"""

# ------------------ Routes ------------------
@app.route("/")
def index():
    search = request.args.get("search", "")
    filtered = {k:v for k,v in inventory.items() if search.lower() in k.lower()}
    return render_template_string(BASE_TEMPLATE, inventory=filtered, search=search)

@app.route("/login", methods=["GET","POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form["id"]==ADMIN_ID and request.form["pw"]==ADMIN_PW:
            session["admin"] = ADMIN_ID
            return redirect(url_for("index"))
        error = "로그인 실패"
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("index"))

@app.route("/change", methods=["POST"])
@login_required
def change():
    name = request.form.get("name", "").strip()
    qty = int(request.form.get("quantity", "1"))
    date = request.form.get("date", "")
    action = request.form.get("action", "in")
    if not name:
        return redirect(url_for("index"))
    if action == "in":
        if name in inventory:
            inventory[name]["quantity"] += qty
        else:
            inventory[name] = {"quantity": qty, "date": date}
    else:
        if name in inventory:
            inventory[name]["quantity"] = max(0, inventory[name]["quantity"] - qty)
    inventory[name]["date"] = date
    save_inventory()
    return redirect(url_for("index"))

@app.route("/api/update", methods=["POST"])
@login_required
def api_update():
    data = request.get_json()
    name = data["name"]
    if name not in inventory:
        return jsonify({"ok":False}),400
    if data["action"]=="plus":
        inventory[name]["quantity"] += 1
    else:
        inventory[name]["quantity"] = max(0, inventory[name]["quantity"] - 1)
    save_inventory()
    return jsonify({"ok":True, "quantity":inventory[name]["quantity"]})

@app.route("/api/delete", methods=["POST"])
@login_required
def api_delete():
    data = request.get_json()
    inventory.pop(data["name"], None)
    save_inventory()
    return jsonify({"ok":True})

@app.route("/download")
@login_required
def download():
    save_inventory()
    return send_file(CSV_FILE, as_attachment=True, download_name="inventory.csv")

@app.route("/export_xlsx")
@login_required
def export_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventory"
    ws.append(["상품명","수량","입고날짜"])
    for name, data in inventory.items():
        ws.append([name, data["quantity"], data["date"]])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return send_file(stream, as_attachment=True, download_name="inventory.xlsx")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
