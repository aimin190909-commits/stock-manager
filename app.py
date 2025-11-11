from flask import Flask, request, redirect, url_for, session, render_template_string

app = Flask(__name__)
app.secret_key = "secure-key"  # 아무 문자열 가능


# ====== 재고 관리 클래스 ======
class Item:
    def __init__(self, quantity, date):
        self.quantity = quantity
        self.date = date


# ====== 재고 저장소 ======
inventory = {}


# ====== HTML 템플릿 ======
BASE_TEMPLATE = """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>재고 관리</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">

  <style>
    body {
      background:#f5f5f7;
      font-family:-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, Arial;
      color:#222;
    }
    .wrapper { max-width:900px; margin:auto; }

    .card {
      background:white;
      border:none;
      border-radius:20px;
      padding:24px;
      box-shadow:0 8px 28px rgba(0,0,0,0.06);
    }

    .brand {
      font-weight:600;
      font-size:22px;
      letter-spacing:-0.3px;
    }

    .table {
      border-collapse:separate;
      border-spacing:0 6px;
    }
    .table thead th {
      border:none;
      font-weight:500;
      color:#555;
      background:none;
    }
    .table tbody tr {
      background:white;
      border-radius:14px;
      box-shadow:0 2px 8px rgba(0,0,0,0.04);
    }
    .table tbody td {
      vertical-align:middle;
      border:none;
      padding:14px 10px;
    }

    .btn-primary {
      background:#007aff;
      border:none;
      border-radius:12px;
    }

    .btn-danger {
      background:#ff3b30;
      border:none;
      border-radius:12px;
    }

    .btn-primary:hover { background:#005fdb; }
    .btn-danger:hover { background:#d92a22; }

    .form-control {
      border-radius:12px;
      border:1px solid #ddd;
    }
  </style>
</head>

<body>
<div class="wrapper py-4">

  <div class="d-flex justify-content-between mb-4">
    <div class="brand">📦 재고 관리</div>
  </div>

  <div class="card mb-4">
    <form method="post" action="{{ url_for('change') }}">
      <div class="row g-2">
        <div class="col-md-5"><input name="name" class="form-control" placeholder="상품명" required></div>
        <div class="col-md-3"><input name="quantity" type="number" class="form-control" value="1" min="1" required></div>
        <div class="col-md-3"><input name="date" type="date" class="form-control" required></div>
        <div class="col-md-1 d-grid"><button name="action" value="in" class="btn btn-primary">입고</button></div>
      </div>
      <div class="row mt-2 g-2">
        <div class="col-md-12 d-grid"><button name="action" value="out" class="btn btn-danger">출고</button></div>
      </div>
    </form>
  </div>

  <div>
    <table class="table text-center">
      <thead><tr><th>상품명</th><th>수량</th><th>입고날짜</th><th>조정</th><th>삭제</th></tr></thead>
      <tbody>
        {% for name, data in inventory.items() %}
        <tr>
          <td>{{ name }}</td>
          <td>{{ data.quantity }}</td>
          <td>{{ data.date }}</td>
          <td>
            <a class="btn btn-primary btn-sm" href="{{ url_for('api_update') }}?name={{ name }}&action=plus">＋</a>
            <a class="btn btn-danger btn-sm" href="{{ url_for('api_update') }}?name={{ name }}&action=minus">－</a>
          </td>
          <td><a class="text-danger fw-bold" href="{{ url_for('api_delete') }}?name={{ name }}">삭제</a></td>
        </tr>
        {% endfor %}
        {% if inventory|length == 0 %}
          <tr><td colspan="5" class="text-muted py-4">등록된 상품이 없습니다.</td></tr>
        {% endif %}
      </tbody>
    </table>
  </div>

</div>
</body>
</html>
"""


# ====== 라우트 ======

@app.route("/")
def home():
    return render_template_string(BASE_TEMPLATE, inventory=inventory)


@app.route("/change", methods=["POST"])
def change():
    name = request.form["name"]
    qty = int(request.form["quantity"])
    date = request.form["date"]
    action = request.form["action"]

    if name not in inventory:
        inventory[name] = Item(0, date)

    if action == "in":  # 입고
        inventory[name].quantity += qty
        inventory[name].date = date
    elif action == "out":  # 출고
        inventory[name].quantity = max(0, inventory[name].quantity - qty)

    return redirect(url_for("home"))


@app.route("/update")
def api_update():
    name = request.args.get("name")
    action = request.args.get("action")

    if name in inventory:
        if action == "plus":
            inventory[name].quantity += 1
        elif action == "minus":
            inventory[name].quantity = max(0, inventory[name].quantity - 1)

    return redirect(url_for("home"))


@app.route("/delete")
def api_delete():
    name = request.args.get("name")
    if name in inventory:
        del inventory[name]
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
