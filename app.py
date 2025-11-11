from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify, send_file, flash
import csv, os
from datetime import datetime
from functools import wraps

# ------------------ Configuration ------------------
app = Flask(__name__)
app.secret_key = "change_this_secret_in_production"  # change to a random secret in production

# ADMIN CREDENTIALS (replace if you want)
# NOTE: These are set from the values you provided. For better security change them later.
ADMIN_ID = "sekwang84"
ADMIN_PW = "989893"

CSV_FILE = "inventory.csv"
LOG_FILE = "log.csv"

# ------------------ In-memory storage ------------------
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

def load_log():
    log_data.clear()
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                log_data.append(row)

def save_log(action, name, change):
    entry = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), action, name, str(change)]
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

# initial load
load_inventory()
load_log()

# ------------------ Templates ------------------
TEMPLATE = """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>재고 관리 (Mint)</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    :root{--mint:#17c3a3;--mint-dark:#009e7f;}
    body{background:#f6fffb;font-family:Inter,system-ui,Segoe UI,Roboto,"Helvetica Neue",Arial;}
    .card{border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,0.06)}
    .brand{color:var(--mint-dark);font-weight:700}
    .btn-mint{background:var(--mint);color:#fff;border:none}
    .btn-mint:hover{background:var(--mint-dark);color:#fff}
    .table thead th{background:var(--mint-dark);color:#fff;border:none}
    .table td, .table th{vertical-align:middle}
    /* mobile adjustments */
    @media (max-width:576px){
      .desktop-hide{display:none}
      .mobile-block{display:block}
      .card{padding:12px}
      .table {font-size:13px}
    }
  </style>
</head>
<body>
<div class="container py-3">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h1 class="h4 brand">📦 재고 관리 시스템</h1>
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
    <div class="col-12 col-md-5">
      <div class="card p-3">
        <form id="searchForm" method="get" action="{{ url_for('index') }}" class="d-flex mb-2">
          <input name="search" class="form-control me-2" placeholder="상품 검색" value="{{ search|default('') }}">
          <button class="btn btn-outline-secondary">검색</button>
        </form>

        <hr>

        <h6>상품 등록 / 수정</h6>
        <form id="addForm" method="post" action="{{ url_for('add') }}" class="row g-2">
          <div class="col-12">
            <input name="name" class="form-control" placeholder="상품명" required>
          </div>
          <div class="col-6">
            <input name="quantity" type="number" min="0" class="form-control" placeholder="수량" required>
          </div>
          <div class="col-6">
            <input name="date" type="date" class="form-control" required>
          </div>
          <div class="col-12">
            <button class="btn btn-mint w-100" {% if not session.admin %}disabled title="관리자 로그인 필요"{% endif %}>등록 / 수정</button>
          </div>
        </form>

        <hr>
        <div class="d-flex gap-2">
          <a class="btn btn-outline-primary btn-sm" href="{{ url_for('download') }}">CSV 다운로드</a>
          <a class="btn btn-outline-secondary btn-sm" href="{{ url_for('show_log') }}">기록 보기</a>
        </div>
      </div>
    </div>

    <div class="col-12 col-md-7">
      <div class="card p-0">
        <div class="p-3 d-flex justify-content-between align-items-center">
          <h6 class="mb-0">전체 재고</h6>
          <div class="small text-muted desktop-hide">터치로 조작</div>
        </div>

        <div class="table-responsive">
          <table class="table table-hover mb-0 align-middle">
            <thead>
              <tr><th>상품명</th><th class="text-end">수량</th><th class="text-center">입고날짜</th><th class="text-center">조정</th><th class="text-center">삭제</th></tr>
            </thead>
            <tbody id="invTable">
              {% for name, data in inventory.items() %}
              <tr data-name="{{ name|e }}">
                <td style="max-width:240px;word-break:break-word">{{ name }}</td>
                <td class="text-end qty">{{ data["quantity"] }}</td>
                <td class="text-center">{{ data["date"] }}</td>
                <td class="text-center">
                  <button class="btn btn-sm btn-outline-success btn-plus" data-name="{{ name|e }}">＋</button>
                  <button class="btn btn-sm btn-outline-danger btn-minus" data-name="{{ name|e }}">－</button>
                </td>
                <td class="text-center">
                  <button class="btn btn-sm btn-link text-danger btn-del" data-name="{{ name|e }}">삭제</button>
                </td>
              </tr>
              {% endfor %}
              {% if inventory|length == 0 %}
              <tr><td colspan="5" class="text-center text-muted">등록된 상품이 없습니다.</td></tr>
              {% endif %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

</div>

<script>
async function jsonReq(url, method='POST', body=null){
  const opts = {method, headers:{}};
  if (body){ opts.headers['Content-Type']='application/json'; opts.body=JSON.stringify(body); }
  const r = await fetch(url, opts);
  return r.json();
}

function updateRow(name, qty){
  const row = document.querySelector('tr[data-name="'+CSS.escape(name)+'"]');
  if (row) row.querySelector('.qty').textContent = qty;
  else location.reload();
}

document.addEventListener('click', function(e){
  if (e.target.matches('.btn-plus')){
    const name = e.target.dataset.name;
    jsonReq('/api/update','POST',{name,action:'plus'}).then(res=>{ if(res.ok) updateRow(name,res.quantity); else alert(res.error); });
  }
  if (e.target.matches('.btn-minus')){
    const name = e.target.dataset.name;
    jsonReq('/api/update','POST',{name,action:'minus'}).then(res=>{ if(res.ok) updateRow(name,res.quantity); else alert(res.error); });
  }
  if (e.target.matches('.btn-del')){
    const name = e.target.dataset.name;
    if(!confirm(name+' 을(를) 삭제하시겠습니까?')) return;
    jsonReq('/api/delete','POST',{name}).then(res=>{ if(res.ok){ const r = document.querySelector('tr[data-name="'+CSS.escape(name)+'"]'); if(r) r.remove(); } else alert(res.error); });
  }
});
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
<style>
  body{background:#f6fffb;font-family:Inter,system-ui,Segoe UI,Roboto,Arial}
  .card{border-radius:12px;box-shadow:0 8px 20px rgba(0,0,0,0.06)}
  .btn-mint{background:#17c3a3;color:#fff;border:none}
</style>
</head>
<body>
<div class="container d-flex justify-content-center align-items-center" style="min-height:70vh">
  <div class="card p-4" style="width:340px">
    <h5 class="mb-3 brand">관리자 로그인</h5>
    {% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
    <form method="post">
      <input name="id" class="form-control mb-2" placeholder="아이디" required>
      <input name="pw" class="form-control mb-2" type="password" placeholder="비밀번호" required>
      <div class="d-grid">
        <button class="btn btn-mint">로그인</button>
      </div>
    </form>
    <div class="mt-2 small text-muted">관리자 계정으로만 수정/삭제 가능합니다.</div>
  </div>
</div>
</body>
</html>
"""

# ------------------ Routes ------------------
@app.route("/")
def index():
    search = request.args.get("search", "")
    filtered = {k:v for k,v in inventory.items() if search.lower() in k.lower()}
    return render_template_string(TEMPLATE, inventory=filtered, search=search)

@app.route("/login", methods=["GET","POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form.get("id")==ADMIN_ID and request.form.get("pw")==ADMIN_PW:
            session["admin"] = ADMIN_ID
            return redirect(url_for("index"))
        else:
            error = "아이디 또는 비밀번호가 잘못되었습니다."
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("index"))

@app.route("/add", methods=["POST"])
@login_required
def add():
    name = request.form.get("name","").strip()
    try:
        quantity = int(request.form.get("quantity","0"))
    except:
        quantity = 0
    date = request.form.get("date","")
    if not name:
        return redirect(url_for("index"))
    inventory[name] = {"quantity": quantity, "date": date}
    save_inventory()
    save_log("등록/수정", name, quantity)
    return redirect(url_for("index"))

@app.route("/api/update", methods=["POST"])
@login_required
def api_update():
    data = request.get_json() or {}
    name = data.get("name","")
    action = data.get("action","")
    if name not in inventory:
        return jsonify({"ok":False,"error":"상품 없음"}),400
    if action=="plus":
        inventory[name]["quantity"] += 1
        save_log("수량 증가", name, "+1")
    elif action=="minus":
        if inventory[name]["quantity"]<=0:
            return jsonify({"ok":False,"error":"재고 부족"}),400
        inventory[name]["quantity"] -= 1
        save_log("수량 감소", name, "-1")
    else:
        return jsonify({"ok":False,"error":"알 수 없는 동작"}),400
    save_inventory()
    return jsonify({"ok":True,"quantity":inventory[name]["quantity"]})

@app.route("/api/delete", methods=["POST"])
@login_required
def api_delete():
    data = request.get_json() or {}
    name = data.get("name","")
    if name in inventory:
        inventory.pop(name,None)
        save_log("삭제", name, "-모두")
        save_inventory()
        return jsonify({"ok":True})
    return jsonify({"ok":False,"error":"상품 없음"}),400

@app.route("/download")
@login_required
def download():
    save_inventory()
    if not os.path.exists(CSV_FILE):
        # create empty CSV
        with open(CSV_FILE,'w',newline='',encoding='utf-8') as f:
            pass
    return send_file(CSV_FILE, as_attachment=True, download_name="inventory.csv", mimetype="text/csv")

@app.route("/log")
@login_required
def show_log():
    lines = ["\t".join(row) for row in log_data]
    page = "<h3>입출고 기록</h3><pre>{}</pre><a href='/'>뒤로</a>".format("\n".join(lines))
    return page

# ------------------ Start ------------------
if __name__ == "__main__":
    # bind to 0.0.0.0 for Render; local dev is fine too
    app.run(host="0.0.0.0", port=5000, debug=True)
