from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify, send_file
import csv, os, io
from datetime import datetime
from functools import wraps
from openpyxl import Workbook

# ------------------ Configuration ------------------
app = Flask(__name__)
app.secret_key = "change_this_secret_in_production"  # change to a random secret in production

# ADMIN CREDENTIALS (from user)
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
                # row may be: timestamp, action, name, change, prev (prev optional)
                log_data.append(row)

def save_log(action, name, change, prev=""):
    # write a 5-column log: timestamp,action,name,change,prev
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

# initial load
load_inventory()
load_log()

# ------------------ Templates ------------------
BASE_TEMPLATE = """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>재고 관리 (Mint Pro)</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <!-- ZXing for barcode scanning -->
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
    /* mobile adjustments */
    @media (max-width:576px){
      .desktop-hide{display:none}
      .mobile-block{display:block}
      .card{padding:12px}
      .table {font-size:13px}
    }
    /* scanner modal */
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
    <!-- Left: Actions -->
    <div class="col-12 col-md-4">
      <div class="card p-3">
        <form id="searchForm" method="get" action="{{ url_for('index') }}" class="d-flex mb-2">
          <input name="search" class="form-control me-2" placeholder="상품 검색" value="{{ search|default('') }}">
          <button class="btn btn-outline-secondary">검색</button>
        </form>

        <hr>

        <h6>바코드 스캔 / 상품 등록</h6>
        <div class="mb-2">
          <button id="openScanner" class="btn btn-outline-primary btn-sm w-100">📷 카메라로 바코드 스캔</button>
        </div>

        <form id="addForm" method="post" action="{{ url_for('change') }}">
          <div class="mb-2">
            <input id="p_name" name="name" class="form-control" placeholder="상품명" required>
          </div>
          <div class="mb-2 row gx-2">
            <div class="col-6">
              <input id="p_qty" name="quantity" type="number" min="1" class="form-control" placeholder="수량" value="1" required>
            </div>
            <div class="col-6">
              <input name="date" type="date" class="form-control" required>
            </div>
          </div>

          <div class="d-grid gap-2">
            <!-- Big In / Out Buttons -->
            <button name="action" value="in" class="btn big-action in-btn" {% if not session.admin %}disabled title="관리자 로그인 필요"{% endif %}>➕ 입고</button>
            <button name="action" value="out" class="btn big-action out-btn" {% if not session.admin %}disabled title="관리자 로그인 필요"{% endif %}>➖ 출고</button>
          </div>
        </form>

        <hr>
        <div class="d-flex gap-2 mb-2">
          <a class="btn btn-outline-primary btn-sm" href="{{ url_for('download') }}">CSV 다운로드</a>
          <a class="btn btn-outline-success btn-sm" href="{{ url_for('export_xlsx') }}">엑셀(.xlsx) 다운로드</a>
          <a class="btn btn-outline-secondary btn-sm" href="{{ url_for('show_log') }}">기록 보기</a>
        </div>

        <hr>
        <h6>최근 변경 (빠른 되돌리기)</h6>
        <div id="recentList" style="max-height:200px; overflow:auto;">
          {% for row in recent %}
            <div class="d-flex justify-content-between small py-1 border-bottom">
              <div>
                <div><strong>{{ row[2] }}</strong> · {{ row[1] }}</div>
                <div class="text-muted">{{ row[0] }} / 변경: {{ row[3] }} {% if row|length>4 and row[4] %} (prev: {{ row[4] }}){% endif %}</div>
              </div>
              <div>
                <button class="btn btn-sm btn-outline-danger undo-btn" data-idx="{{ loop.index0 }}">되돌리기</button>
              </div>
            </div>
          {% endfor %}
          {% if recent|length==0 %}
            <div class="text-muted small">최근 변경이 없습니다.</div>
          {% endif %}
        </div>

      </div>
    </div>

    <!-- Right: Inventory Table -->
    <div class="col-12 col-md-8">
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

<!-- Scanner Modal -->
<div id="scannerModal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6); align-items:center; justify-content:center; z-index:9999;">
  <div style="width:95%; max-width:520px; background:white; padding:12px; border-radius:10px;">
    <div class="d-flex justify-content-between mb-2">
      <h6 class="mb-0">바코드 스캔</h6>
      <button id="closeScanner" class="btn btn-sm btn-outline-secondary">닫기</button>
    </div>
    <video id="video"></video>
    <div class="mt-2 small text-muted">카메라에 바코드를 비추면 자동으로 상품명 입력란에 코드가 들어갑니다.</div>
  </div>
</div>

<script>
/* AJAX helper */
async function jsonReq(url, method='POST', body=null){
  const opts = {method, headers:{}};
  if (body){ opts.headers['Content-Type']='application/json'; opts.body=JSON.stringify(body); }
  const r = await fetch(url, opts);
  return r.json();
}

/* Update row quantity in table */
function updateRow(name, qty){
  const row = document.querySelector('tr[data-name="'+CSS.escape(name)+'"]');
  if (row) row.querySelector('.qty').textContent = qty;
  else location.reload();
}

/* buttons */
document.addEventListener('click', function(e){
  if (e.target.matches('.btn-plus')){
    const name = e.target.dataset.name;
    jsonReq('/api/update','POST',{name,action:'plus'}).then(res=>{ if(res.ok) updateRow(name,res.quantity); else alert(res.error || '오류'); });
  }
  if (e.target.matches('.btn-minus')){
    const name = e.target.dataset.name;
    jsonReq('/api/update','POST',{name,action:'minus'}).then(res=>{ if(res.ok) updateRow(name,res.quantity); else alert(res.error || '오류'); });
  }
  if (e.target.matches('.btn-del')){
    const name = e.target.dataset.name;
    if(!confirm(name+' 을(를) 삭제하시겠습니까?')) return;
    jsonReq('/api/delete','POST',{name}).then(res=>{ if(res.ok){ const r = document.querySelector('tr[data-name="'+CSS.escape(name)+'"]'); if(r) r.remove(); } else alert(res.error || '오류'); });
  }
  if (e.target.matches('.undo-btn')){
    const idx = parseInt(e.target.dataset.idx);
    if(!confirm('이 변경을 되돌리시겠습니까?')) return;
    jsonReq('/api/undo','POST',{index: idx}).then(res=>{ if(res.ok){ location.reload(); } else alert(res.error || '오류'); });
  }
});

/* Scanner using ZXing */
let codeReader = null;
let selectedDeviceId = null;
document.getElementById('openScanner').addEventListener('click', async function(){
  document.getElementById('scannerModal').style.display = 'flex';
  if(!codeReader){
    codeReader = new ZXing.BrowserMultiFormatReader();
    try {
      const devices = await codeReader.listVideoInputDevices();
      if(devices.length>0) selectedDeviceId = devices[0].deviceId;
      await codeReader.decodeFromVideoDevice(selectedDeviceId, 'video', (result, err) => {
        if (result) {
          // put barcode into product name (you can change behavior)
          document.getElementById('p_name').value = result.text;
          // auto close scanner
          codeReader.reset();
          document.getElementById('scannerModal').style.display = 'none';
        }
      });
    } catch (e) {
      alert('카메라 접근 또는 스캔 중 오류: ' + e);
      document.getElementById('scannerModal').style.display = 'none';
    }
  }
});
document.getElementById('closeScanner').addEventListener('click', function(){
  if(codeReader) codeReader.reset();
  document.getElementById('scannerModal').style.display = 'none';
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
    # pass recent 10 logs (reverse chronological)
    recent = list(reversed(log_data))[:10]
    return render_template_string(BASE_TEMPLATE, inventory=filtered, search=search, recent=recent)

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

# change endpoint handles both in/out actions from big buttons
@app.route("/change", methods=["POST"])
@login_required
def change():
    name = request.form.get("name","").strip()
    try:
        qty = int(request.form.get("quantity","0"))
    except:
        qty = 0
    date = request.form.get("date","")
    action = request.form.get("action","in")
    if not name:
        return redirect(url_for("index"))
    prev = inventory[name]["quantity"] if name in inventory else 0
    if action == "in":
        inventory[name] = {"quantity": inventory.get(name, {}).get("quantity", 0) + qty, "date": date}
        save_log("입고", name, f"+{qty}", prev)
    else:
        # out
        current = inventory.get(name, {}).get("quantity", 0)
        new = max(0, current - qty)
        inventory[name] = {"quantity": new, "date": date}
        save_log("출고", name, f"-{qty}", current)
    save_inventory()
    return redirect(url_for("index"))

@app.route("/api/update", methods=["POST"])
@login_required
def api_update():
    data = request.get_json() or {}
    name = data.get("name","")
    action = data.get("action","")
    if name not in inventory:
        return jsonify({"ok":False,"error":"상품 없음"}),400
    prev = inventory[name]["quantity"]
    if action=="plus":
        inventory[name]["quantity"] += 1
        save_log("수량 증가", name, "+1", prev)
    elif action=="minus":
        if inventory[name]["quantity"]<=0:
            return jsonify({"ok":False,"error":"재고 부족"}),400
        inventory[name]["quantity"] -= 1
        save_log("수량 감소", name, "-1", prev)
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
        prev = inventory[name]["quantity"]
        inventory.pop(name,None)
        save_log("삭제", name, "-모두", prev)
        save_inventory()
        return jsonify({"ok":True})
    return jsonify({"ok":False,"error":"상품 없음"}),400

# undo last change by index (index from recent list)
@app.route("/api/undo", methods=["POST"])
@login_required
def api_undo():
    data = request.get_json() or {}
    idx = data.get("index")
    try:
        idx = int(idx)
    except:
        return jsonify({"ok":False,"error":"잘못된 인덱스"}),400
    # recent is reversed(log_data), so index 0 means last entry in log_data
    if idx < 0 or idx >= len(list(reversed(log_data))):
        return jsonify({"ok":False,"error":"인덱스 범위 외"}),400
    # convert to original index
    orig_idx = len(log_data) - 1 - idx
    entry = log_data[orig_idx]  # [time, action, name, change, prev?]
    _, action, name, change = entry[0:4]
    prev = entry[4] if len(entry) > 4 and entry[4] != "" else None

    # perform reverse
    if action in ("수량 증가","수량 감소","입고","출고"):
        # we saved prev for these actions; if prev present, restore
        if prev is not None and prev != "":
            try:
                prev_int = int(prev)
                inventory[name] = {"quantity": prev_int, "date": inventory.get(name, {}).get("date","")}
                save_log("되돌리기", name, f"undo {action}", inventory[name]["quantity"])
                # remove the original log entry to avoid double undo chaos
                log_data.pop(orig_idx)
                with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(log_data)
                save_inventory()
                return jsonify({"ok":True})
            except:
                return jsonify({"ok":False,"error":"이전값 복원 실패"}),500
        else:
            return jsonify({"ok":False,"error":"이 항목은 이전값(prev)이 없어 되돌릴 수 없습니다."}),400
    elif action == "삭제":
        # cannot restore deleted details unless prev exists
        if prev is not None and prev != "":
            try:
                prev_int = int(prev)
                inventory[name] = {"quantity": prev_int, "date": ""}
                save_log("되돌리기", name, "undo 삭제", prev_int)
                log_data.pop(orig_idx)
                with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(log_data)
                save_inventory()
                return jsonify({"ok":True})
            except:
                return jsonify({"ok":False,"error":"복원 실패"}),500
        else:
            return jsonify({"ok":False,"error":"삭제 로그에 prev가 없어 복원 불가"}),400
    else:
        return jsonify({"ok":False,"error":"되돌리기 불가능한 작업"}),400

@app.route("/download")
@login_required
def download():
    save_inventory()
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE,'w',newline='',encoding='utf-8') as f:
            pass
    return send_file(CSV_FILE, as_attachment=True, download_name="inventory.csv", mimetype="text/csv")

@app.route("/export_xlsx")
@login_required
def export_xlsx():
    # create an in-memory xlsx workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventory"
    ws.append(["상품명","수량","입고날짜"])
    for name, data in inventory.items():
        ws.append([name, data["quantity"], data["date"]])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return send_file(stream, as_attachment=True, download_name="inventory.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

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
