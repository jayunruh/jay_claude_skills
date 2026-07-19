"""Generate a self-contained HTML viewer for an ESMFold2 prediction."""
import argparse
import json
import os

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ESMFold2 Viewer — {name}</title>
<style>
  body {{ font-family: sans-serif; background: #1a1a2e; color: #e0e0e0; margin: 0; padding: 16px; }}
  h1 {{ color: #a8d8ea; margin-bottom: 4px; }}
  .badges {{ display: flex; gap: 12px; margin: 10px 0 20px; }}
  .badge {{ background: #16213e; border: 1px solid #0f3460; border-radius: 8px;
            padding: 8px 18px; font-size: 1.1em; }}
  .badge span {{ font-weight: bold; color: #e94560; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  .panel {{ background: #16213e; border-radius: 10px; padding: 14px; }}
  .panel h2 {{ margin: 0 0 10px; font-size: 1em; color: #a8d8ea; }}
  #viewer {{ width: 100%; height: 420px; border-radius: 6px; overflow: hidden; }}
  canvas {{ display: block; }}
  .controls {{ margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap; }}
  button {{ background: #0f3460; color: #e0e0e0; border: none; border-radius: 5px;
            padding: 5px 12px; cursor: pointer; }}
  button:hover {{ background: #e94560; }}
  #plddt-canvas, #pae-canvas {{ width: 100%; }}
</style>
</head>
<body>
<h1>ESMFold2 — {name}</h1>
<div class="badges">
  <div class="badge">pTM: <span id="ptm-val">—</span></div>
  <div class="badge" id="iptm-badge">ipTM: <span id="iptm-val">—</span></div>
</div>
<div class="grid">
  <div class="panel">
    <h2>3D Structure (colour by pLDDT)</h2>
    <div id="viewer"></div>
    <div class="controls">
      <button onclick="toggleSpin()">Toggle spin</button>
      <button onclick="setStyle('cartoon')">Cartoon</button>
      <button onclick="setStyle('stick')">Stick</button>
      <button onclick="setStyle('sphere')">Sphere</button>
    </div>
  </div>
  <div class="panel">
    <h2>pLDDT per residue</h2>
    <canvas id="plddt-canvas" height="200"></canvas>
  </div>
  <div class="panel" style="grid-column:1/-1">
    <h2>PAE matrix</h2>
    <canvas id="pae-canvas"></canvas>
  </div>
</div>

<script src="https://3dmol.csb.pitt.edu/build/3Dmol-min.js"></script>
<script>
const CIF_DATA = `{cif_data}`;
const CONFIDENCE = {confidence_json};

// Confidence summary
document.getElementById('ptm-val').textContent = CONFIDENCE.ptm != null
  ? CONFIDENCE.ptm.toFixed(3) : 'N/A';
if (CONFIDENCE.iptm != null) {{
  document.getElementById('iptm-val').textContent = CONFIDENCE.iptm.toFixed(3);
}} else {{
  document.getElementById('iptm-badge').style.display = 'none';
}}

// 3Dmol viewer
let viewer = $3Dmol.createViewer('viewer', {{backgroundColor: '#0d1117'}});
viewer.addModel(CIF_DATA, 'mmcif');
const plddt = CONFIDENCE.plddt;

// Colour atoms by pLDDT using a blue-white-red scale
viewer.setStyle({{}}, {{cartoon: {{colorscheme: {{prop: 'b', gradient: 'rwb', min: 0, max: 100}}}}}});
viewer.zoomTo();
viewer.render();

let spinning = false;
function toggleSpin() {{
  spinning = !spinning;
  spinning ? viewer.spin('y') : viewer.spin(false);
}}
function setStyle(s) {{
  const scheme = {{colorscheme: {{prop: 'b', gradient: 'rwb', min: 0, max: 100}}}};
  viewer.setStyle({{}}, {{[s]: scheme}});
  viewer.render();
}}

// pLDDT plot
(function() {{
  const canvas = document.getElementById('plddt-canvas');
  const W = canvas.parentElement.clientWidth - 28;
  canvas.width = W; canvas.height = 200;
  const ctx = canvas.getContext('2d');
  const bands = [
    [90, 100, '#003F88'], [70, 90, '#65CBF3'],
    [50, 70, '#FFDB13'], [0, 50, '#FF7D45']
  ];
  // background bands
  bands.forEach(([lo, hi, col]) => {{
    ctx.fillStyle = col + '33';
    const y1 = (1 - hi/100) * 180 + 10;
    const y2 = (1 - lo/100) * 180 + 10;
    ctx.fillRect(40, y1, W - 50, y2 - y1);
  }});
  // axes
  ctx.strokeStyle = '#555'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(40, 10); ctx.lineTo(40, 190); ctx.lineTo(W - 10, 190); ctx.stroke();
  // y labels
  ctx.fillStyle = '#aaa'; ctx.font = '10px sans-serif'; ctx.textAlign = 'right';
  [0,25,50,75,100].forEach(v => {{
    const y = (1 - v/100) * 180 + 10;
    ctx.fillText(v, 36, y + 3);
  }});
  // line
  const n = plddt.length;
  ctx.strokeStyle = '#e94560'; ctx.lineWidth = 1.5;
  ctx.beginPath();
  plddt.forEach((v, i) => {{
    const x = 40 + (i / (n - 1)) * (W - 50);
    const y = (1 - v / 100) * 180 + 10;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }});
  ctx.stroke();
  // x label
  ctx.fillStyle = '#aaa'; ctx.textAlign = 'center';
  ctx.fillText('Residue index', W / 2, 200 - 2);
}})();

// PAE heatmap
(function() {{
  const pae = CONFIDENCE.pae;
  if (!pae || !pae.length) return;
  const N = pae.length;
  const SIZE = Math.min(500, N * 2);
  const canvas = document.getElementById('pae-canvas');
  canvas.width = SIZE + 40; canvas.height = SIZE + 40;
  const ctx = canvas.getContext('2d');
  const cellW = SIZE / N;
  const maxVal = 31.75;
  for (let i = 0; i < N; i++) {{
    for (let j = 0; j < N; j++) {{
      const v = pae[i][j] / maxVal;
      // blue (low) -> white -> yellow (high)
      const r = Math.round(v * 255);
      const g = Math.round(v * 220);
      const b = Math.round((1 - v) * 255);
      ctx.fillStyle = `rgb(${{r}},${{g}},${{b}})`;
      ctx.fillRect(40 + j * cellW, i * cellW, cellW, cellW);
    }}
  }}
  // axes
  ctx.strokeStyle = '#888'; ctx.lineWidth = 1;
  ctx.strokeRect(40, 0, SIZE, SIZE);
  ctx.fillStyle = '#aaa'; ctx.font = '11px sans-serif'; ctx.textAlign = 'center';
  ctx.fillText('Scored residue', 40 + SIZE / 2, SIZE + 30);
  ctx.save(); ctx.translate(14, SIZE / 2); ctx.rotate(-Math.PI / 2);
  ctx.fillText('Aligned residue', 0, 0); ctx.restore();
}})();
</script>
</body>
</html>
"""

def main():
    parser = argparse.ArgumentParser(description='Generate ESMFold2 HTML viewer')
    parser.add_argument('--cif', required=True, help='Path to .cif structure file')
    parser.add_argument('--confidence', required=True, help='Path to confidence JSON file')
    parser.add_argument('--output', required=True, help='Path to write HTML viewer')
    args = parser.parse_args()

    with open(args.cif) as f:
        cif_data = f.read().replace('`', r'\`')

    with open(args.confidence) as f:
        confidence = json.load(f)

    # Scale pLDDT to 0-100 if the API returned 0-1 values
    if confidence.get('plddt') and max(confidence['plddt']) <= 1.0:
        confidence['plddt'] = [v * 100 for v in confidence['plddt']]

    name = os.path.splitext(os.path.basename(args.output))[0].replace('_viewer', '')

    html = TEMPLATE.format(
        name=name,
        cif_data=cif_data,
        confidence_json=json.dumps(confidence),
    )

    with open(args.output, 'w') as f:
        f.write(html)

    print(f'Viewer written to {args.output}')

if __name__ == '__main__':
    main()
