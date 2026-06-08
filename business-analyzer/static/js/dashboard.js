// ============================
//  Business Growth Analyzer JS
// ============================

let currentData = null;

const fileInput = document.getElementById('fileInput');
const fileHint  = document.getElementById('fileHint');
const analyzeBtn = document.getElementById('analyzeBtn');
const loadingBar = document.getElementById('loadingBar');
const errorBox  = document.getElementById('errorBox');
const results   = document.getElementById('results');
const uploadZone = document.getElementById('uploadZone');

// ── File selection ──
fileInput.addEventListener('change', () => {
  const f = fileInput.files[0];
  if (f) {
    fileHint.textContent = `Selected: ${f.name} (${(f.size/1024).toFixed(1)} KB)`;
    fileHint.style.color = '#00d4aa';
    analyzeBtn.disabled = false;
  }
});

// ── Drag and Drop ──
uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('drag'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag');
  const f = e.dataTransfer.files[0];
  if (f) {
    const dt = new DataTransfer();
    dt.items.add(f);
    fileInput.files = dt.files;
    fileHint.textContent = `Selected: ${f.name}`;
    fileHint.style.color = '#00d4aa';
    analyzeBtn.disabled = false;
  }
});

// ── Analyze ──
async function analyzeFile() {
  const file = fileInput.files[0];
  if (!file) return;

  analyzeBtn.disabled = true;
  analyzeBtn.innerHTML = '<span>Analyzing...</span> ⏳';
  loadingBar.style.display = 'block';
  errorBox.style.display = 'none';
  results.style.display = 'none';

  const fd = new FormData();
  fd.append('file', file);

  try {
    const res = await fetch('/upload', { method: 'POST', body: fd });
    const data = await res.json();

    if (data.error) throw new Error(data.error);

    currentData = data;
    renderResults(data);
    results.style.display = 'block';
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    errorBox.textContent = '⚠ ' + err.message;
    errorBox.style.display = 'block';
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.innerHTML = '<span>Analyze Business Data</span> →';
    loadingBar.style.display = 'none';
  }
}

// ── Render Results ──
function fmt(n) { return '₹' + Number(n).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2}); }
function fmtShort(n) { return '₹' + Number(n).toLocaleString('en-IN', {maximumFractionDigits:0}); }

function renderResults(d) {
  const s = d.summary;

  // Summary cards
  document.getElementById('s-revenue').textContent = fmt(s.total_revenue);
  document.getElementById('s-cost').textContent = fmt(s.total_cost);
  const profitEl = document.getElementById('s-profit');
  profitEl.textContent = fmt(s.net_profit);
  profitEl.style.color = s.net_profit >= 0 ? '#00d4aa' : '#ff6b6b';
  document.getElementById('s-margin').textContent = s.profit_margin.toFixed(2) + '%';
  document.getElementById('s-top').textContent = d.top_product;

  const pred = d.prediction;
  document.getElementById('s-predict').textContent = fmt(pred.next_month);
  const trendEl = document.getElementById('s-trend');
  trendEl.textContent = pred.trend === 'up' ? '↑ Upward trend' : pred.trend === 'down' ? '↓ Declining trend' : '→ Stable';
  trendEl.style.color = pred.trend === 'up' ? '#00d4aa' : pred.trend === 'down' ? '#ff6b6b' : '#f7b731';

  // Monthly table
  const mBody = document.querySelector('#monthlyTable tbody');
  mBody.innerHTML = '';
  (d.monthly || []).forEach(row => {
    const g = parseFloat(row.growth || 0);
    const gClass = g >= 0 ? 'growth-pos' : 'growth-neg';
    const gText = (g >= 0 ? '+' : '') + g.toFixed(1) + '%';
    mBody.innerHTML += `<tr>
      <td>${row.month_str}</td>
      <td>${fmtShort(row.revenue)}</td>
      <td>${fmtShort(row.cost)}</td>
      <td style="color:${row.profit>=0?'#00d4aa':'#ff6b6b'};font-weight:600;">${fmtShort(row.profit)}</td>
      <td class="${gClass}">${gText}</td>
    </tr>`;
  });

  // Products table
  const totalRev = d.products.reduce((a, p) => a + p.revenue, 0);
  const pBody = document.querySelector('#productsTable tbody');
  pBody.innerHTML = '';
  (d.products || []).forEach((p, i) => {
    const share = totalRev ? (p.revenue / totalRev * 100).toFixed(1) : 0;
    pBody.innerHTML += `<tr class="${i===0?'rank-1':''}">
      <td><span class="rank-badge">${i+1}</span></td>
      <td style="font-weight:600;">${p.product}</td>
      <td>${Number(p.quantity).toLocaleString()}</td>
      <td>${fmtShort(p.revenue)}</td>
      <td style="color:${p.profit>=0?'#00d4aa':'#ff6b6b'}">${fmtShort(p.profit)}</td>
      <td>
        <div style="display:flex;align-items:center;gap:8px;">
          <div class="progress-bar"><div class="progress-fill" style="width:${share}%"></div></div>
          <span style="font-size:12px;color:#9499b5;">${share}%</span>
        </div>
      </td>
    </tr>`;
  });

  // Charts
  document.getElementById('chart-bar').src = 'data:image/png;base64,' + d.charts.bar;
  document.getElementById('chart-line').src = 'data:image/png;base64,' + d.charts.line;
  document.getElementById('chart-pie').src = 'data:image/png;base64,' + d.charts.pie;

  // Insights
  const il = document.getElementById('insightsList');
  il.innerHTML = '';
  (d.suggestions || []).forEach(tip => {
    const div = document.createElement('div');
    div.className = 'insight-item';
    div.innerHTML = tip;
    il.appendChild(div);
  });
}

// ── Download PDF ──
async function downloadReport() {
  if (!currentData) return;
  const btn = document.getElementById('downloadBtn');
  btn.textContent = '⏳ Generating PDF...';
  btn.disabled = true;
  try {
    const res = await fetch('/download_report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentData)
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'business_report.pdf'; a.click();
    URL.revokeObjectURL(url);
  } catch(e) { alert('PDF generation failed. Try again.'); }
  btn.textContent = '📄 Download Full PDF Report';
  btn.disabled = false;
}

// ── Sample CSV ──
function downloadSample() {
  const rows = [
    'Date,Product Name,Quantity,Price,Cost',
    '2024-01-05,Laptop,10,45000,32000',
    '2024-01-12,Mouse,50,800,350',
    '2024-01-20,Keyboard,30,1500,700',
    '2024-02-03,Laptop,8,45000,32000',
    '2024-02-14,Monitor,15,12000,8000',
    '2024-02-22,Mouse,60,800,350',
    '2024-03-01,Keyboard,45,1500,700',
    '2024-03-10,Laptop,12,46000,33000',
    '2024-03-18,Monitor,20,12500,8200',
    '2024-04-05,Mouse,80,820,360',
    '2024-04-15,Headphones,25,3500,1800',
    '2024-04-25,Laptop,9,47000,33500',
    '2024-05-02,Keyboard,55,1600,720',
    '2024-05-12,Headphones,30,3600,1850',
    '2024-05-20,Monitor,18,13000,8500',
    '2024-06-01,Laptop,14,48000,34000',
    '2024-06-10,Mouse,90,850,370',
    '2024-06-20,Headphones,35,3700,1900',
  ];
  const blob = new Blob([rows.join('\n')], {type:'text/csv'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href=url; a.download='sample_sales.csv'; a.click();
  URL.revokeObjectURL(url);
}

// ── Sidebar toggle (mobile) ──
function toggleSidebar() {
  document.querySelector('.sidebar').classList.toggle('open');
}

// Close sidebar on nav click (mobile)
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelector('.sidebar').classList.remove('open');
  });
});
