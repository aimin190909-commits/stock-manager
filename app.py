from flask import Flask, request, render_template_string, redirect
from datetime import datetime
import csv, os

app = Flask(__name__)
inventory = {}

log_file = "log.csv"

if not os.path.exists(log_file):
    with open(log_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["시간", "작업", "상품명", "수량", "입고날짜"])


def log(action, name, quantity, date):
    with open(log_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), action, name, quantity, date])


html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>재고 관리 시스템</title>

<style>
    body { 
        font-family: 'Pretendard', sans-serif;
        margin: 40px;
        background: #f6fffb;
    }
    h1 {
        color: #009e7f;
        margin-bottom: 20px;
    }
    .box {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        width: 500px;
    }
    input, button {
        padding: 8px;
        border: 1px solid #ccc;
        border-radius: 6px;
        margin: 4px;
    }
    button {
        background: #17c3a3;
        border: none;
        color: white;
        cursor: pointer;
        transition: 0.2s;
    }
    button:hover {
        background: #009e7f;
    }
    table {
        margin-top: 25px;
        border-collapse: collapse;
        width: 600px;
        background: white;
        border-radius: 10px;
        overflow: hidden;
    }
    th {
        background: #009e7f;
        color: white;
        padding: 12px;
    }
    td {
        border-bottom: 1px solid #ddd;
        padding: 10px;
        text-align: center;
    }
    a {
        color: red;
        text-decoration: none;
        font-weight: bold;
    }
</style>

</head>
<body>

<h1>📦 재고 관리 시스템</h1>

<div class="box">
<form method="POST" action="/add">
    <input type="text" name="name" placeholder="상품명" required>
    <input type="number" name="quantity" placeholder="수량" required>
    <input type="date" name="date" required>
    <button type="submit">등록 / 수정</button>
</form>
</div>

<table>
    <tr>
        <th>상품명</th>
        <th>수량</th>
        <th>입고 날짜</th>
        <th>삭제</th>
    </tr>
    {% for name, data in inventory.items() %}
    <tr>
        <td>{{ name }}</td>
        <td>{{ data["quantity"] }}</td>
        <td>{{ data["date"] }}</td>
        <td><a href="/delete/{{ name }}">X</a></td>
    </tr>
    {% endfor %}
</table>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(html, inventory=inventory)

@app.route("/add", methods=["POST"])
def add():
    name = request.form["name"]
    quantity = request.form["quantity"]
    date = request.form["date"]
    action = "등록/수정" if name in inventory else "신규등록"
    inventory[name] = {"quantity": quantity, "date": date}
    log(action, name, quantity, date)
    return redirect("/")

@app.route("/delete/<name>")
def delete(name):
    if name in inventory:
        log("삭제", name, inventory[name]["quantity"], inventory[name]["date"])
        inventory.pop(name)
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
