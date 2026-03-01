"""
たぬき謎 レビューWebUI

目的:
    candidates.json の候補をブラウザで快適にレビューする。
    承認(a) / 却下(r) / 保留(s) をクリックで操作。

使い方:
    uv run webui.py
    ブラウザで http://localhost:5000 を開く
"""

import json
from pathlib import Path
from flask import Flask, jsonify, request, render_template_string

CANDIDATES_PATH = "candidates.json"

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>たぬき謎 レビュー</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Hiragino Kaku Gothic ProN', sans-serif; background: #f5f5f5; color: #333; }

  header { background: #2c3e50; color: white; padding: 16px 24px; display: flex; align-items: center; gap: 16px; }
  header h1 { font-size: 20px; }
  .stats { margin-left: auto; display: flex; gap: 16px; font-size: 14px; }
  .stat { background: rgba(255,255,255,0.15); padding: 4px 12px; border-radius: 12px; }

  .filter-bar { background: white; padding: 12px 24px; border-bottom: 1px solid #ddd; display: flex; gap: 8px; align-items: center; }
  .filter-btn { padding: 6px 16px; border: 1px solid #ccc; border-radius: 20px; background: white; cursor: pointer; font-size: 13px; }
  .filter-btn.active { background: #2c3e50; color: white; border-color: #2c3e50; }

  .container { max-width: 800px; margin: 24px auto; padding: 0 16px; }

  .card { background: white; border-radius: 12px; padding: 28px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  .card-meta { font-size: 12px; color: #999; margin-bottom: 12px; display: flex; gap: 12px; }
  .badge { padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: bold; }
  .badge-replace { background: #e8f4fd; color: #1a73e8; }
  .badge-delete  { background: #fef3e2; color: #e67e22; }
  .badge-multi   { background: #f0e8fd; color: #8e44ad; }

  .riddle { text-align: center; padding: 20px 0; }
  .question { font-size: 28px; font-weight: bold; letter-spacing: 4px; color: #1a1a1a; }
  .rule-label { font-size: 14px; color: #666; margin: 10px 0 6px; }
  .rule-name { font-size: 20px; font-weight: bold; color: #2c3e50; letter-spacing: 2px; }
  .arrow { font-size: 24px; color: #ccc; margin: 12px 0; }
  .answer { font-size: 26px; font-weight: bold; color: #27ae60; letter-spacing: 3px; }

  .actions { display: flex; gap: 12px; margin-top: 24px; justify-content: center; }
  .btn { padding: 12px 32px; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: all 0.15s; min-width: 100px; }
  .btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
  .btn:active { transform: translateY(0); }
  .btn-approve { background: #27ae60; color: white; }
  .btn-reject  { background: #e74c3c; color: white; }
  .btn-skip    { background: #95a5a6; color: white; }

  .status-bar { text-align: center; font-size: 13px; color: #999; margin-top: 12px; }
  .status-approved { color: #27ae60; font-weight: bold; }
  .status-rejected { color: #e74c3c; font-weight: bold; }
  .status-pending  { color: #f39c12; font-weight: bold; }

  .done-msg { text-align: center; padding: 60px; color: #999; font-size: 18px; }
  .progress-bar { height: 4px; background: #eee; border-radius: 2px; margin-top: 8px; }
  .progress-fill { height: 100%; background: #27ae60; border-radius: 2px; transition: width 0.3s; }
</style>
</head>
<body>

<header>
  <h1>🦝 たぬき謎 レビュー</h1>
  <div class="stats">
    <span class="stat" id="stat-pending">pending: -</span>
    <span class="stat" id="stat-approved">承認: -</span>
    <span class="stat" id="stat-rejected">却下: -</span>
  </div>
</header>

<div class="filter-bar">
  <span style="font-size:13px;color:#666;">絞り込み:</span>
  <button class="filter-btn active" onclick="setFilter('all')">すべて</button>
  <button class="filter-btn" onclick="setFilter('置き換え系')">置き換え系</button>
  <button class="filter-btn" onclick="setFilter('削除系')">削除系</button>
  <button class="filter-btn" onclick="setFilter('複数ルール')">複数ルール</button>
  <button class="filter-btn" onclick="setFilter('pending')">未レビューのみ</button>
</div>

<div class="container" id="main"></div>

<script>
let candidates = [];
let filter = 'all';

async function load() {
  const res = await fetch('/api/candidates');
  candidates = await res.json();
  render();
  updateStats();
}

function setFilter(f) {
  filter = f;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  render();
}

function filtered() {
  return candidates.filter(c => {
    if (filter === 'all') return true;
    if (filter === 'pending') return c.status === 'pending';
    if (filter === '複数ルール') return c.type !== '置き換え系' && c.type !== '削除系';
    return c.type === filter;
  });
}

function render() {
  const list = filtered();
  const main = document.getElementById('main');
  if (list.length === 0) {
    main.innerHTML = '<div class="done-msg">レビュー対象なし</div>';
    return;
  }

  const reviewed = candidates.filter(c => c.status !== 'pending').length;
  const pct = Math.round(reviewed / candidates.length * 100);

  main.innerHTML = `
    <div style="margin-bottom:8px;font-size:13px;color:#999;">
      ${list.length}件表示 / 全${candidates.length}件
      <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
    </div>
    ${list.map((c, i) => cardHTML(c, i)).join('')}
  `;
}

function cardHTML(c, i) {
  const badgeClass = c.type === '置き換え系' ? 'badge-replace' : c.type === '削除系' ? 'badge-delete' : 'badge-multi';
  const statusLabel = {pending:'未レビュー', approved:'✅ 承認済み', rejected:'❌ 却下済み'}[c.status] || c.status;
  const statusClass = {pending:'status-pending', approved:'status-approved', rejected:'status-rejected'}[c.status] || '';

  return `
  <div class="card" id="card-${i}">
    <div class="card-meta">
      <span class="badge ${badgeClass}">${c.type}</span>
      <span class="${statusClass}">${statusLabel}</span>
    </div>
    <div class="riddle">
      <div class="question">「${c.question}」</div>
      <div class="rule-label">ルール</div>
      <div class="rule-name">【${c.rule}】</div>
      <div class="arrow">↓</div>
      <div class="answer">「${c.answer}」</div>
    </div>
    <div class="actions">
      <button class="btn btn-approve" onclick="judge(${i}, 'approved')">✅ 承認</button>
      <button class="btn btn-skip"    onclick="judge(${i}, 'pending')">⏭ 保留</button>
      <button class="btn btn-reject"  onclick="judge(${i}, 'rejected')">❌ 却下</button>
    </div>
  </div>`;
}

async function judge(i, status) {
  const c = filtered()[i];
  const idx = candidates.indexOf(c);
  candidates[idx].status = status;

  await fetch('/api/judge', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({index: idx, status})
  });

  updateStats();
  render();
}

function updateStats() {
  const pending  = candidates.filter(c => c.status === 'pending').length;
  const approved = candidates.filter(c => c.status === 'approved').length;
  const rejected = candidates.filter(c => c.status === 'rejected').length;
  document.getElementById('stat-pending').textContent  = `未レビュー: ${pending}`;
  document.getElementById('stat-approved').textContent = `承認: ${approved}`;
  document.getElementById('stat-rejected').textContent = `却下: ${rejected}`;
}

load();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/candidates")
def get_candidates():
    candidates = json.loads(Path(CANDIDATES_PATH).read_text(encoding="utf-8"))
    return jsonify(candidates)


@app.route("/api/judge", methods=["POST"])
def judge():
    data = request.json
    idx = data["index"]
    status = data["status"]

    candidates = json.loads(Path(CANDIDATES_PATH).read_text(encoding="utf-8"))
    candidates[idx]["status"] = status
    Path(CANDIDATES_PATH).write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("ブラウザで http://localhost:5001 を開いてください")
    app.run(debug=False, port=5001)
