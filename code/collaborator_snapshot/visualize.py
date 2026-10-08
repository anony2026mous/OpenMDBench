"""
OpenMDBench — Trajectory Replay Visualizer

Loads a trajectory JSON (produced by run_tournament.py via CSS
TrajectoryRecorder) and generates a self-contained HTML replay page:
  - 20x20 grid with port, obstacles, entities
  - Play / pause / step / speed controls, episode selector
  - Per-step actions, rewards, event log, mission status
  - Final metrics panel

Usage:
    python visualize.py --input results/trajectories/all_trajectories.json
    python visualize.py --input results/trajectories/all_trajectories.json \
        --episode 5 --output replay.html --serve 8899
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import socketserver
import sys
import threading

# Action names matching grid_env.Direction
ACTION_NAMES = ["UP", "DOWN", "LEFT", "RIGHT", "STAY", "INTERCEPT"]


def compress_episode(ep: dict) -> dict:
    """Compress one episode trajectory into render-friendly frames."""
    frames = []
    for ts in ep.get("timesteps", []):
        obs = ts.get("observation", {})
        sit = obs.get("situational_data", {})

        blue = [
            [a["position"][0], a["position"][1], a.get("ammo", 0),
             bool(a.get("alive", True)), a.get("disabled_steps", 0)]
            for a in sit.get("friendly_assets", [])
        ]
        red = []
        for c in sit.get("detected_contacts", []):
            red.append([c["position"][0], c["position"][1], c.get("type", "unknown")])
        civ = [
            [c["position"][0], c["position"][1]]
            for c in sit.get("civilian_positions", [])
        ]
        unk = [
            [c["position"][0], c["position"][1]]
            for c in sit.get("unknown_contacts", [])
        ]

        # action: {uid: int-or-name}
        raw_act = ts.get("action", {}) or {}
        act = {}
        for uid, a in raw_act.items():
            if isinstance(a, int):
                act[uid] = ACTION_NAMES[a] if 0 <= a < len(ACTION_NAMES) else str(a)
            else:
                act[uid] = str(a)

        frames.append({
            "t": ts.get("t", 0),
            "r": round(float(ts.get("reward", 0.0) or 0.0), 3),
            "blue": blue,
            "red": red,
            "civ": civ,
            "unk": unk,
            "act": act,
            "events": obs.get("event_log", []) or [],
            "status": obs.get("mission_status", ""),
        })

    fm = ep.get("final_metrics", {})
    return {
        "agent": ep.get("agent_name", "?"),
        "difficulty": ep.get("difficulty", "?"),
        "seed": ep.get("seed", -1),
        "winner": ep.get("winner"),
        "frames": frames,
        "metrics": {
            "mission_success": fm.get("mission_success"),
            "composite_score": fm.get("composite_score"),
            "planning_score": fm.get("planning_score"),
            "execution_score": fm.get("execution_score"),
            "threats_intercepted": fm.get("red_intercepted"),
            "civilians_lost": fm.get("civilian_casualties"),
        },
        "briefing": (ep.get("timesteps") or [{}])[0]
        .get("observation", {}).get("mission_briefing", "") if ep.get("timesteps") else "",
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>OpenMDBench Replay</title>
<style>
  :root { --bg:#0d1117; --panel:#161b22; --border:#30363d; --txt:#c9d1d9; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--txt);
         font-family:'Segoe UI',system-ui,sans-serif; display:flex; height:100vh; }
  #left { padding:14px; }
  canvas { background:#0a0e14; border:1px solid var(--border); border-radius:6px; }
  #right { flex:1; padding:14px; overflow-y:auto; background:var(--panel);
           border-left:1px solid var(--border); min-width:340px; }
  h2 { font-size:15px; margin:10px 0 6px; color:#58a6ff; }
  select, button, input[type=range] { background:#21262d; color:var(--txt);
           border:1px solid var(--border); border-radius:5px; padding:4px 8px; }
  button { cursor:pointer; } button:hover { background:#30363d; }
  .ctl { display:flex; gap:8px; align-items:center; margin:10px 0; flex-wrap:wrap; }
  table { border-collapse:collapse; width:100%; font-size:13px; }
  td, th { border:1px solid var(--border); padding:3px 8px; text-align:left; }
  .mono { font-family:ui-monospace,monospace; font-size:12px; }
  .win { color:#3fb950; font-weight:bold; } .loss { color:#f85149; font-weight:bold; }
  .ev { background:#3d2e00; border-left:3px solid #d29922; padding:4px 8px;
        margin:3px 0; font-size:12px; border-radius:3px; }
  .legend { display:flex; gap:12px; flex-wrap:wrap; font-size:12px; margin-top:8px; }
  .legend span::before { content:''; display:inline-block; width:10px; height:10px;
        border-radius:50%; margin-right:4px; vertical-align:-1px; }
  .l-blue::before { background:#4a9eff; } .l-red::before { background:#f85149; }
  .l-trans::before { background:#f0883e; } .l-scout::before { background:#bc8cff; }
  .l-civ::before { background:#3fb950; } .l-unk::before { background:#d29922; }
  .l-port::before { background:#1f6feb; border-radius:2px; }
  .l-obs::before { background:#484f58; border-radius:2px; }
  #brief { font-size:12px; color:#8b949e; margin-top:6px; }
</style>
</head>
<body>
<div id="left">
  <div class="ctl">
    <label>Episode <select id="epSel"></select></label>
    <button id="playBtn">&#9654; Play</button>
    <button id="prevBtn">&#9664;</button>
    <button id="nextBtn">&#9654;</button>
    <label>Speed <input type="range" id="speed" min="1" max="10" value="4"></label>
  </div>
  <div class="ctl">
    <input type="range" id="stepSlider" min="0" value="0" style="width:480px">
    <span id="stepLbl" class="mono">t=0</span>
  </div>
  <canvas id="cv" width="600" height="600"></canvas>
  <div class="legend">
    <span class="l-blue">Blue defender</span><span class="l-red">Red combatant</span>
    <span class="l-trans">Red transport</span><span class="l-scout">Red scout</span>
    <span class="l-civ">Civilian</span><span class="l-unk">Unknown</span>
    <span class="l-port">Port (protect)</span><span class="l-obs">Obstacle</span>
  </div>
</div>
<div id="right">
  <h2 id="epTitle">Episode</h2>
  <div id="brief"></div>
  <h2>Status</h2>
  <div id="statusBox" class="mono"></div>
  <h2>Actions (this step)</h2>
  <table id="actTbl"><tr><th>Unit</th><th>Action</th><th>Ammo</th></tr></table>
  <h2>Events</h2>
  <div id="evBox"></div>
  <h2>Final Metrics</h2>
  <table id="metTbl"></table>
</div>
<script>
const DATA = __DATA__;
const PORT = [[0,17],[1,17],[2,17],[0,18],[1,18],[2,18],[0,19],[1,19],[2,19]];
const OBS = __OBS__;
const cv = document.getElementById('cv'), ctx = cv.getContext('2d');
const CELL = cv.width / 20;
let cur = 0, frame = 0, playing = false, timer = null;

const epSel = document.getElementById('epSel');
DATA.episodes.forEach((ep, i) => {
  const o = document.createElement('option');
  o.value = i;
  o.textContent = `#${i} ${ep.agent} @ ${ep.difficulty} seed=${ep.seed} `
    + (ep.metrics.mission_success ? 'WIN' : 'LOSS');
  epSel.appendChild(o);
});

function drawGrid() {
  ctx.clearRect(0, 0, cv.width, cv.height);
  ctx.strokeStyle = '#161b22';
  for (let i = 0; i <= 20; i++) {
    ctx.beginPath(); ctx.moveTo(i*CELL, 0); ctx.lineTo(i*CELL, cv.height); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, i*CELL); ctx.lineTo(cv.width, i*CELL); ctx.stroke();
  }
  // port
  ctx.fillStyle = 'rgba(31,111,235,0.28)';
  PORT.forEach(([x,y]) => ctx.fillRect(x*CELL, cv.height-(y+1)*CELL, CELL, CELL));
  ctx.strokeStyle = '#1f6feb'; ctx.strokeRect(0, cv.height-3*CELL, 3*CELL, 3*CELL);
  ctx.fillStyle = '#58a6ff'; ctx.font = '11px sans-serif';
  ctx.fillText('PORT', 6, cv.height-3*CELL+14);
  // obstacles
  ctx.fillStyle = '#484f58';
  OBS.forEach(([x,y]) => ctx.fillRect(x*CELL+1, cv.height-(y+1)*CELL+1, CELL-2, CELL-2));
}

function dot(x, y, color, r=7, label='') {
  const px = x*CELL + CELL/2, py = cv.height - (y*CELL + CELL/2);
  ctx.beginPath(); ctx.arc(px, py, r, 0, 2*Math.PI);
  ctx.fillStyle = color; ctx.fill();
  ctx.strokeStyle = '#0d1117'; ctx.stroke();
  if (label) { ctx.fillStyle = '#fff'; ctx.font = '9px sans-serif';
               ctx.fillText(label, px+r+2, py+3); }
}

function render() {
  const ep = DATA.episodes[cur];
  const f = ep.frames[frame];
  if (!f) return;
  drawGrid();
  f.civ.forEach(([x,y]) => dot(x, y, '#3fb950', 6));
  f.unk.forEach(([x,y]) => dot(x, y, '#d29922', 6, '?'));
  f.red.forEach(([x,y,t]) => {
    const c = t==='red_transport' ? '#f0883e' : t==='red_scout' ? '#bc8cff' : '#f85149';
    dot(x, y, c, 7);
  });
  f.blue.forEach(([x,y,ammo,alive,dis]) => {
    if (!alive) return;
    dot(x, y, dis > 0 ? '#6e7681' : '#4a9eff', 8, `${ammo}`);
  });
  // step label
  document.getElementById('stepLbl').textContent =
    `t=${f.t}  reward=${f.r}  ${f.status || ''}`;
  // status box
  document.getElementById('statusBox').innerHTML =
    `step <b>${f.t}</b> / ${ep.frames.length-1} &nbsp; reward=<b>${f.r}</b>`
    + ` &nbsp; status=<b>${f.status || '-'}</b>`;
  // action table
  let rows = '<tr><th>Unit</th><th>Action</th><th>Ammo</th></tr>';
  f.blue.forEach((b, i) => {
    const uid = `blue_${i}`;
    rows += `<tr><td>${uid}${b[4]>0?' (disabled)':''}</td>`
          + `<td>${f.act[uid] ?? '-'}</td><td>${b[2]}</td></tr>`;
  });
  document.getElementById('actTbl').innerHTML = rows;
  // events
  const evBox = document.getElementById('evBox');
  if (f.events && f.events.length) {
    evBox.innerHTML = f.events.map(e =>
      `<div class="ev">${typeof e === 'string' ? e : JSON.stringify(e)}</div>`).join('');
  } else { evBox.innerHTML = '<span style="color:#484f58">no events</span>'; }
  document.getElementById('stepSlider').value = frame;
}

function loadEpisode(i) {
  cur = i; frame = 0; stop();
  const ep = DATA.episodes[i];
  document.getElementById('stepSlider').max = ep.frames.length - 1;
  document.getElementById('epTitle').textContent =
    `Episode #${i}: ${ep.agent} @ ${ep.difficulty} (seed ${ep.seed})`;
  const w = ep.metrics.mission_success;
  document.getElementById('epTitle').innerHTML +=
    w ? ' <span class="win">WIN</span>' : ' <span class="loss">LOSS</span>';
  document.getElementById('brief').textContent = ep.briefing || '';
  const m = ep.metrics;
  document.getElementById('metTbl').innerHTML =
    `<tr><td>Mission success</td><td>${m.mission_success}</td></tr>` +
    `<tr><td>Composite score</td><td>${fmt(m.composite_score)}</td></tr>` +
    `<tr><td>Planning score</td><td>${fmt(m.planning_score)}</td></tr>` +
    `<tr><td>Execution score</td><td>${fmt(m.execution_score)}</td></tr>` +
    `<tr><td>Winner</td><td>${ep.winner ?? '-'}</td></tr>`;
  render();
}
function fmt(v) { return (v === null || v === undefined) ? '-' : Number(v).toFixed(3); }

function tick() {
  const ep = DATA.episodes[cur];
  if (frame >= ep.frames.length - 1) { stop(); return; }
  frame++; render();
}
function play() {
  if (playing) return; playing = true;
  document.getElementById('playBtn').innerHTML = '&#10074;&#10074; Pause';
  const sp = Number(document.getElementById('speed').value);
  timer = setInterval(tick, 600 / sp);
}
function stop() {
  playing = false; clearInterval(timer);
  document.getElementById('playBtn').innerHTML = '&#9654; Play';
}
document.getElementById('playBtn').onclick = () => playing ? stop() : play();
document.getElementById('prevBtn').onclick = () => { stop(); if (frame>0){frame--;render();} };
document.getElementById('nextBtn').onclick = () => {
  stop(); const ep=DATA.episodes[cur];
  if (frame<ep.frames.length-1){frame++;render();} };
document.getElementById('stepSlider').oninput = e => {
  stop(); frame = Number(e.target.value); render(); };
document.getElementById('speed').oninput = () => { if (playing){stop();play();} };
epSel.onchange = e => loadEpisode(Number(e.target.value));

loadEpisode(__START_EP__);
</script>
</body>
</html>
"""


def build_html(traj: dict, start_episode: int = 0) -> str:
    episodes = [compress_episode(ep) for ep in traj.get("episodes", [])]
    obstacles = [[x, y] for x in range(20) for y in range(20)]  # placeholder
    # Actual obstacle cells (must match grid_env.OBSTACLES)
    obstacles = (
        [[x, y] for x in range(5, 8) for y in range(5, 7)]
        + [[x, y] for x in range(10, 13) for y in range(10, 12)]
        + [[x, y] for x in range(14, 16) for y in range(3, 6)]
    )
    data_json = json.dumps({"episodes": episodes}, default=str)
    obs_json = json.dumps(obstacles)
    html = HTML_TEMPLATE.replace("__DATA__", data_json)
    html = html.replace("__OBS__", obs_json)
    html = html.replace("__START_EP__", str(min(start_episode, max(len(episodes) - 1, 0))))
    return html


def main():
    parser = argparse.ArgumentParser(description="OpenMDBench trajectory replay visualizer")
    parser.add_argument("--input", required=True, help="Trajectory JSON file")
    parser.add_argument("--output", default="replay.html", help="Output HTML path")
    parser.add_argument("--episode", type=int, default=0, help="Episode to show first")
    parser.add_argument("--serve", type=int, default=None,
                        help="Serve output dir on this port (blocking)")
    args = parser.parse_args()

    with open(args.input) as f:
        traj = json.load(f)

    n = len(traj.get("episodes", []))
    print(f"Loaded {n} episodes from {args.input}")

    html = build_html(traj, start_episode=args.episode)
    with open(args.output, "w") as f:
        f.write(html)
    print(f"Replay page written to: {os.path.abspath(args.output)}")
    print(f"Size: {os.path.getsize(args.output) / 1e6:.1f} MB")

    if args.serve:
        out_dir = os.path.dirname(os.path.abspath(args.output)) or "."
        out_name = os.path.basename(args.output)
        print(f"Serving http://localhost:{args.serve}/{out_name} ...")
        os.chdir(out_dir)
        with socketserver.TCPServer(("", args.serve),
                                    http.server.SimpleHTTPRequestHandler) as httpd:
            httpd.serve_forever()


if __name__ == "__main__":
    main()
