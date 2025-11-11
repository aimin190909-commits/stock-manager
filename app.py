from flask import Flask
app = Flask(__name__)

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
    {% if session.admin %}
      <a class="btn btn-outline-secondary btn-sm" href="{{ url_for('logout') }}">로그아웃</a>
    {% else %}
      <a class="btn btn-primary btn-sm" href="{{ url_for('login') }}">관리자 로그인</a>
    {% endif %}
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
