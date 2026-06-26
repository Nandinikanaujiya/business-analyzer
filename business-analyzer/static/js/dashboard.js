// ==========================================
//  Business ERP Suite & Analytics Javascript
// ==========================================

let currentData = null;
let currentTab = 'dashboard';
let trendInterval = 'daily';

// State lists
let customersList = [];
let filteredCustomersList = [];
let productsList = [];
let filteredProductsList = [];
let categoriesList = [];
let ordersList = [];
let filteredOrdersList = [];
let selectedOrderItems = []; // items in new order modal
let activeOrderFilter = 'all';

// Pagination state
let currentPage = { customers: 1, products: 1, orders: 1 };
const pageSize = 8;

// Chart.js Instances
let chartLineInst = null;
let chartBarInst = null;
let chartPieInst = null;

// DOM Elements
const fileInput = document.getElementById('fileInput');
const fileHint  = document.getElementById('fileHint');
const analyzeBtn = document.getElementById('analyzeBtn');
const loadingBar = document.getElementById('loadingBar');
const errorBox  = document.getElementById('errorBox');
const results   = document.getElementById('results');
const uploadZone = document.getElementById('uploadZone');

// Initialize on Load
window.addEventListener('DOMContentLoaded', () => {
  // Check if session user is active and pull dashboard
  checkLoginAndLoadDashboard();
  setupUploadListeners();
});

function setupUploadListeners() {
  if (!fileInput) return;
  fileInput.addEventListener('change', () => {
    const f = fileInput.files[0];
    if (f) {
      fileHint.textContent = `Selected: ${f.name} (${(f.size/1024).toFixed(1)} KB)`;
      fileHint.style.color = '#00d4aa';
      analyzeBtn.disabled = false;
    }
  });

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
}

// ── Tab Management ──
function switchTab(tabId) {
  currentTab = tabId;
  document.querySelectorAll('.content-tab').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  
  document.getElementById(`tab-${tabId}`).classList.add('active');
  document.getElementById(`nav-${tabId}`).classList.add('active');
  
  // Set headers
  const title = document.getElementById('tab-title');
  const sub = document.getElementById('tab-subtitle');
  if (tabId === 'dashboard') {
    title.textContent = "Dashboard Overview";
    sub.textContent = "Real-time analytical operations control";
    loadDashboardStats();
  } else if (tabId === 'customers') {
    title.textContent = "Customer Management";
    sub.textContent = "Manage profiles, contacts, and purchase logs";
    loadCustomers();
  } else if (tabId === 'products') {
    title.textContent = "Product Inventory";
    sub.textContent = "Track stock quantities, prices, and low stock limits";
    loadProducts();
    loadCategories();
  } else if (tabId === 'orders') {
    title.textContent = "Order Operations";
    sub.textContent = "Create transactions and filter statuses";
    loadOrders();
    loadCustomers(); // Needed for order creation
    loadProducts();  // Needed for order creation
  }
}

// ── Modal Management ──
function openModal(id) {
  document.getElementById(id).style.display = 'flex';
}
function closeModal(id) {
  document.getElementById(id).style.display = 'none';
}

// ── Dashboard Loading ──
async function checkLoginAndLoadDashboard() {
  try {
    const res = await fetch('/api/dashboard');
    if (res.status === 200) {
      const data = await res.json();
      currentData = data;
      renderResults(data);
      results.style.display = 'block';
    }
  } catch (e) {
    console.log("No data uploaded yet or server disconnected.");
  }
}

async function loadDashboardStats() {
  try {
    const res = await fetch('/api/dashboard');
    if (res.ok) {
      const data = await res.json();
      currentData = data;
      renderResults(data);
    }
  } catch (e) {}
}

// ── File Analysis Ingestion ──
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

// ── Render Results & Chart.js ──
function fmt(n) { return '₹' + Number(n).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2}); }
function fmtShort(n) { return '₹' + Number(n).toLocaleString('en-IN', {maximumFractionDigits:0}); }

function renderResults(d) {
  const s = d.summary;

  // Summary cards
  document.getElementById('s-revenue').textContent = fmt(s.total_revenue);
  document.getElementById('s-orders').textContent = s.total_orders.toLocaleString();
  document.getElementById('s-customers').textContent = s.total_customers.toLocaleString();
  
  const profitEl = document.getElementById('s-profit');
  profitEl.textContent = fmt(s.net_profit);
  profitEl.style.color = s.net_profit >= 0 ? '#00d4aa' : '#ff6b6b';
  document.getElementById('s-margin').textContent = s.profit_margin.toFixed(2) + '%';
  document.getElementById('s-top').textContent = d.top_product;

  // Low stock alerts
  const lowWarning = document.getElementById('lowStockWarning');
  if (s.low_stock_alerts > 0) {
    lowWarning.style.display = 'flex';
    document.getElementById('lowStockMessage').textContent = `Low Stock Alert! You have ${s.low_stock_alerts} product(s) running below their minimum stock thresholds. Go to Products to review.`;
  } else {
    lowWarning.style.display = 'none';
  }

  // AI Insights
  const il = document.getElementById('insightsList');
  il.innerHTML = '';
  (d.suggestions || []).forEach(tip => {
    const div = document.createElement('div');
    div.className = 'insight-item';
    div.innerHTML = tip;
    il.appendChild(div);
  });

  // Render Chart.js
  renderLineChart();
  renderBarChart(d.products);
  renderPieChart(d.products);
}

// ── Chart.js Builders ──
const chartStyles = {
  accent: '#6c63ff',
  accentGlow: 'rgba(108,99,255,0.2)',
  green: '#00d4aa',
  greenGlow: 'rgba(0,212,170,0.15)',
  red: '#ff6b6b',
  text: '#e8e8f0',
  grid: '#1e2230'
};

function renderLineChart() {
  if (!currentData || !currentData.trends) return;
  const ctx = document.getElementById('chartLine').getContext('2d');
  
  const trendData = currentData.trends[trendInterval] || [];
  
  // Extract labels and datasets
  let labels = [];
  let revenues = [];
  let profits = [];
  
  trendData.forEach(item => {
    if (trendInterval === 'daily') labels.push(item.day);
    else if (trendInterval === 'weekly') labels.push(item.week);
    else if (trendInterval === 'monthly') labels.push(item.month);
    else if (trendInterval === 'yearly') labels.push(item.year);
    
    revenues.push(item.revenue);
    profits.push(item.profit);
  });
  
  if (chartLineInst) chartLineInst.destroy();
  
  chartLineInst = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Revenue',
          data: revenues,
          borderColor: chartStyles.accent,
          backgroundColor: chartStyles.accentGlow,
          fill: true,
          tension: 0.3
        },
        {
          label: 'Net Profit',
          data: profits,
          borderColor: chartStyles.green,
          backgroundColor: chartStyles.greenGlow,
          fill: true,
          tension: 0.3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: chartStyles.text } }
      },
      scales: {
        x: { grid: { color: chartStyles.grid }, ticks: { color: chartStyles.text } },
        y: { grid: { color: chartStyles.grid }, ticks: { color: chartStyles.text } }
      }
    }
  });
}

function renderBarChart(products) {
  if (!products || products.length === 0) return;
  const ctx = document.getElementById('chartBar').getContext('2d');
  
  const topProducts = products.slice(0, 5);
  const labels = topProducts.map(p => p.name.substring(0, 10));
  const valuations = topProducts.map(p => p.price * p.stock);
  
  if (chartBarInst) chartBarInst.destroy();
  
  chartBarInst = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Stock Value (Price * Stock)',
        data: valuations,
        backgroundColor: [
          chartStyles.accent,
          '#4a90d9',
          chartStyles.green,
          '#f7b731',
          chartStyles.red
        ],
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: chartStyles.text } },
        y: { grid: { color: chartStyles.grid }, ticks: { color: chartStyles.text } }
      }
    }
  });
}

function renderPieChart(products) {
  if (!products || products.length === 0) return;
  const ctx = document.getElementById('chartPie').getContext('2d');
  
  // Group by category valuation
  const catSums = {};
  products.forEach(p => {
    const cat = p.category_name || 'General';
    const val = p.price * p.stock;
    catSums[cat] = (catSums[cat] || 0) + val;
  });
  
  const labels = Object.keys(catSums);
  const data = Object.values(catSums);
  
  if (chartPieInst) chartPieInst.destroy();
  
  chartPieInst = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: [
          '#6c63ff',
          '#00d4aa',
          '#ff6b6b',
          '#f7b731',
          '#45aaf2',
          '#fd9644'
        ],
        borderWidth: 1,
        borderColor: '#13161f'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: chartStyles.text, font: { size: 10 } }
        }
      }
    }
  });
}

function switchTrendTab(interval) {
  trendInterval = interval;
  document.querySelectorAll('.trend-tabs .tab-btn').forEach(btn => btn.classList.remove('active'));
  document.getElementById(`btn-${interval}`).classList.add('active');
  renderLineChart();
}

// ── Customer CRUD Operations ──
async function loadCustomers() {
  const res = await fetch('/api/customers');
  if (res.ok) {
    customersList = await res.json();
    filteredCustomersList = [...customersList];
    renderCustomersTable();
  }
}

function filterCustomers() {
  const q = document.getElementById('custSearch').value.toLowerCase().trim();
  filteredCustomersList = customersList.filter(c => 
    c.name.toLowerCase().includes(q) || 
    (c.email && c.email.toLowerCase().includes(q)) || 
    (c.phone && c.phone.includes(q))
  );
  currentPage.customers = 1;
  renderCustomersTable();
}

function renderCustomersTable() {
  const tbody = document.querySelector('#customersTable tbody');
  tbody.innerHTML = '';
  
  const start = (currentPage.customers - 1) * pageSize;
  const pageData = filteredCustomersList.slice(start, start + pageSize);
  
  pageData.forEach(c => {
    tbody.innerHTML += `<tr>
      <td style="font-weight:600;">${c.name}</td>
      <td>${c.email || '—'}</td>
      <td>${c.phone || '—'}</td>
      <td>${c.total_orders.toLocaleString()}</td>
      <td style="color:#00d4aa;font-weight:600;">${fmtShort(c.total_spent)}</td>
      <td>
        <button class="sample-btn" style="padding:4px 8px;margin-right:4px;" onclick="viewHistory(${c.id})">History</button>
        <button class="sample-btn" style="padding:4px 8px;margin-right:4px;" onclick="editCustomer(${c.id}, '${c.name}', '${c.email || ''}', '${c.phone || ''}', '${c.notes || ''}')">Edit</button>
        <button class="sample-btn" style="padding:4px 8px;border-color:var(--red);color:var(--red);" onclick="deleteCustomer(${c.id})">Delete</button>
      </td>
    </tr>`;
  });
  
  // Pagination UI
  const totalPages = Math.ceil(filteredCustomersList.length / pageSize) || 1;
  document.getElementById('custPageInfo').textContent = `Page ${currentPage.customers} of ${totalPages}`;
  document.getElementById('custPrev').disabled = currentPage.customers === 1;
  document.getElementById('custNext').disabled = currentPage.customers === totalPages;
}

async function saveCustomer(e) {
  e.preventDefault();
  const id = document.getElementById('cust-id').value;
  const name = document.getElementById('cust-name').value;
  const email = document.getElementById('cust-email').value;
  const phone = document.getElementById('cust-phone').value;
  const notes = document.getElementById('cust-notes').value;
  
  const method = id ? 'PUT' : 'POST';
  const url = id ? `/api/customers/${id}` : '/api/customers';
  
  const res = await fetch(url, {
    method: method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, phone, notes })
  });
  
  if (res.ok) {
    closeModal('modalCustomer');
    document.getElementById('customerForm').reset();
    document.getElementById('cust-id').value = '';
    loadCustomers();
  } else {
    const err = await res.json();
    alert(err.error || "Failed to save customer.");
  }
}

function editCustomer(id, name, email, phone, notes) {
  document.getElementById('cust-id').value = id;
  document.getElementById('cust-name').value = name;
  document.getElementById('cust-email').value = email;
  document.getElementById('cust-phone').value = phone;
  document.getElementById('cust-notes').value = notes;
  document.getElementById('custModalTitle').textContent = "Edit Customer";
  openModal('modalCustomer');
}

async function deleteCustomer(id) {
  if (confirm("Are you sure you want to delete this customer?")) {
    await fetch(`/api/customers/${id}`, { method: 'DELETE' });
    loadCustomers();
  }
}

async function viewHistory(id) {
  const res = await fetch(`/api/customers/${id}/history`);
  if (res.ok) {
    const history = await res.json();
    
    // Find customer details
    const c = customersList.find(cust => cust.id === id);
    document.getElementById('history-cust-name').textContent = c.name;
    document.getElementById('history-cust-email').textContent = c.email || 'No email';
    document.getElementById('history-cust-total').textContent = fmtShort(c.total_spent);
    
    const tbody = document.querySelector('#custHistoryTable tbody');
    tbody.innerHTML = '';
    
    if (history.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;">No purchases found.</td></tr>`;
    } else {
      history.forEach(h => {
        tbody.innerHTML += `<tr>
          <td>${h.date.substring(0, 10)}</td>
          <td>${h.product_name}</td>
          <td>${h.quantity}</td>
          <td>${fmtShort(h.price)}</td>
          <td style="color:${h.status === 'Completed' ? '#00d4aa' : '#ff6b6b'};">${h.status}</td>
        </tr>`;
      });
    }
    openModal('modalCustHistory');
  }
}

// ── Product CRUD Operations ──
async function loadProducts() {
  const res = await fetch('/api/products');
  if (res.ok) {
    productsList = await res.json();
    filteredProductsList = [...productsList];
    renderProductsTable();
  }
}

function filterProducts() {
  const q = document.getElementById('prodSearch').value.toLowerCase().trim();
  filteredProductsList = productsList.filter(p => 
    p.name.toLowerCase().includes(q) || 
    (p.sku && p.sku.toLowerCase().includes(q)) || 
    (p.category_name && p.category_name.toLowerCase().includes(q))
  );
  currentPage.products = 1;
  renderProductsTable();
}

function renderProductsTable() {
  const tbody = document.querySelector('#productsTable tbody');
  tbody.innerHTML = '';
  
  const start = (currentPage.products - 1) * pageSize;
  const pageData = filteredProductsList.slice(start, start + pageSize);
  
  pageData.forEach(p => {
    let statusClass = 'growth-pos';
    let statusText = 'In Stock';
    if (p.stock === 0) {
      statusClass = 'growth-neg';
      statusText = 'Out of Stock';
    } else if (p.stock <= p.threshold) {
      statusClass = 'growth-neg'; // or orange
      statusText = 'Low Stock';
    }
    
    tbody.innerHTML += `<tr>
      <td style="font-family:'Syne',sans-serif;font-size:12.5px;">${p.sku || '—'}</td>
      <td style="font-weight:600;">${p.name}</td>
      <td>${p.category_name || 'General'}</td>
      <td>${fmtShort(p.price)}</td>
      <td>${fmtShort(p.cost)}</td>
      <td style="font-weight:600;">${p.stock}</td>
      <td class="${statusClass}">${statusText}</td>
      <td>
        <button class="sample-btn" style="padding:4px 8px;margin-right:4px;" onclick="editProduct(${p.id}, '${p.name}', ${p.category_id}, '${p.sku || ''}', ${p.price}, ${p.cost}, ${p.stock}, ${p.threshold})">Edit</button>
        <button class="sample-btn" style="padding:4px 8px;border-color:var(--red);color:var(--red);" onclick="deleteProduct(${p.id})">Delete</button>
      </td>
    </tr>`;
  });
  
  const totalPages = Math.ceil(filteredProductsList.length / pageSize) || 1;
  document.getElementById('prodPageInfo').textContent = `Page ${currentPage.products} of ${totalPages}`;
  document.getElementById('prodPrev').disabled = currentPage.products === 1;
  document.getElementById('prodNext').disabled = currentPage.products === totalPages;
}

function openProductModal() {
  document.getElementById('productForm').reset();
  document.getElementById('prod-id').value = '';
  document.getElementById('prodModalTitle').textContent = "Add Product";
  
  // Populate categories dropdown
  const select = document.getElementById('prod-category');
  select.innerHTML = '';
  categoriesList.forEach(c => {
    select.innerHTML += `<option value="${c.id}">${c.name}</option>`;
  });
  openModal('modalProduct');
}

function editProduct(id, name, catId, sku, price, cost, stock, threshold) {
  document.getElementById('prod-id').value = id;
  document.getElementById('prod-name').value = name;
  document.getElementById('prod-sku').value = sku;
  document.getElementById('prod-price').value = price;
  document.getElementById('prod-cost').value = cost;
  document.getElementById('prod-stock').value = stock;
  document.getElementById('prod-threshold').value = threshold;
  
  const select = document.getElementById('prod-category');
  select.innerHTML = '';
  categoriesList.forEach(c => {
    const sel = c.id === catId ? 'selected' : '';
    select.innerHTML += `<option value="${c.id}" ${sel}>${c.name}</option>`;
  });
  
  document.getElementById('prodModalTitle').textContent = "Edit Product";
  openModal('modalProduct');
}

async function saveProduct(e) {
  e.preventDefault();
  const id = document.getElementById('prod-id').value;
  const name = document.getElementById('prod-name').value;
  const category_id = document.getElementById('prod-category').value;
  const sku = document.getElementById('prod-sku').value;
  const price = document.getElementById('prod-price').value;
  const cost = document.getElementById('prod-cost').value;
  const stock = document.getElementById('prod-stock').value;
  const threshold = document.getElementById('prod-threshold').value;
  
  const method = id ? 'PUT' : 'POST';
  const url = id ? `/api/products/${id}` : '/api/products';
  
  const res = await fetch(url, {
    method: method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, category_id, sku, price, cost, stock, threshold })
  });
  
  if (res.ok) {
    closeModal('modalProduct');
    loadProducts();
    loadDashboardStats();
  } else {
    const err = await res.json();
    alert(err.error || "Failed to save product.");
  }
}

async function deleteProduct(id) {
  if (confirm("Are you sure you want to delete this product?")) {
    await fetch(`/api/products/${id}`, { method: 'DELETE' });
    loadProducts();
    loadDashboardStats();
  }
}

// ── Categories Management ──
async function loadCategories() {
  const res = await fetch('/api/categories');
  if (res.ok) {
    categoriesList = await res.json();
    
    // Render list inside manage categories modal
    const ul = document.getElementById('categoriesList');
    ul.innerHTML = '';
    categoriesList.forEach(c => {
      ul.innerHTML += `<li style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #1e2230;">
        <span>${c.name}</span>
      </li>`;
    });
  }
}

async function saveCategory(e) {
  e.preventDefault();
  const name = document.getElementById('new-cat-name').value.trim();
  if(!name) return;
  
  const res = await fetch('/api/categories', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name })
  });
  
  if (res.ok) {
    document.getElementById('new-cat-name').value = '';
    loadCategories();
  } else {
    alert("Category already exists or name invalid.");
  }
}

// ── Order Management ──
async function loadOrders() {
  const res = await fetch('/api/orders');
  if (res.ok) {
    ordersList = await res.json();
    filteredOrdersList = [...ordersList];
    renderOrdersTable();
  }
}

function filterOrdersByStatus(status) {
  activeOrderFilter = status;
  document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
  document.getElementById(`order-filter-${status.toLowerCase()}`).classList.add('active');
  
  if (status === 'all') {
    filteredOrdersList = [...ordersList];
  } else {
    filteredOrdersList = ordersList.filter(o => o.status === status);
  }
  currentPage.orders = 1;
  renderOrdersTable();
}

function renderOrdersTable() {
  const tbody = document.querySelector('#ordersTable tbody');
  tbody.innerHTML = '';
  
  const start = (currentPage.orders - 1) * pageSize;
  const pageData = filteredOrdersList.slice(start, start + pageSize);
  
  pageData.forEach(o => {
    let statusClass = 'growth-pos';
    if (o.status === 'Pending') statusClass = 'stat-trend'; // orange/yellow
    else if (o.status === 'Cancelled') statusClass = 'growth-neg';
    
    let statusActions = '';
    if (o.status === 'Pending') {
      statusActions = `
        <button class="sample-btn" style="padding:4px 8px;margin-right:4px;border-color:#00d4aa;color:#00d4aa;" onclick="changeStatus(${o.id}, 'Completed')">Complete</button>
        <button class="sample-btn" style="padding:4px 8px;border-color:var(--red);color:var(--red);" onclick="changeStatus(${o.id}, 'Cancelled')">Cancel</button>
      `;
    }
    
    tbody.innerHTML += `<tr>
      <td style="font-family:'Syne',sans-serif;font-weight:600;">#ORD-${o.id}</td>
      <td>${o.customer_name || 'Walk-in'}</td>
      <td>${o.date.substring(0, 16)}</td>
      <td style="font-weight:600;color:var(--accent2);">${fmtShort(o.total_amount)}</td>
      <td class="${statusClass}">${o.status}</td>
      <td>
        ${statusActions}
      </td>
    </tr>`;
  });
  
  const totalPages = Math.ceil(filteredOrdersList.length / pageSize) || 1;
  document.getElementById('orderPageInfo').textContent = `Page ${currentPage.orders} of ${totalPages}`;
  document.getElementById('orderPrev').disabled = currentPage.orders === 1;
  document.getElementById('orderNext').disabled = currentPage.orders === totalPages;
}

function openOrderModal() {
  document.getElementById('orderForm').reset();
  selectedOrderItems = [];
  renderOrderItemsTable();
  
  // Populate Customer Dropdown
  const custSelect = document.getElementById('order-customer');
  custSelect.innerHTML = '<option value="">-- Choose Customer --</option>';
  customersList.forEach(c => {
    custSelect.innerHTML += `<option value="${c.id}">${c.name}</option>`;
  });
  
  // Populate Product Dropdown
  const prodSelect = document.getElementById('order-item-product');
  prodSelect.innerHTML = '<option value="">-- Choose Product --</option>';
  productsList.forEach(p => {
    prodSelect.innerHTML += `<option value="${p.id}" data-price="${p.price}">${p.name} (₹${p.price})</option>`;
  });
  
  openModal('modalOrder');
}

function updateOrderItemPrice() {
  // Can be used to display stock warnings or bind unit price
}

function addOrderItemRow() {
  const select = document.getElementById('order-item-product');
  const qtyInput = document.getElementById('order-item-qty');
  const prodId = select.value;
  const qty = parseInt(qtyInput.value);
  
  if (!prodId || qty < 1) return;
  
  const opt = select.options[select.selectedIndex];
  const prodName = opt.text.split(' (')[0];
  const price = parseFloat(opt.dataset.price);
  
  // Check if item exists
  const existing = selectedOrderItems.find(item => item.product_id === parseInt(prodId));
  if (existing) {
    existing.quantity += qty;
  } else {
    selectedOrderItems.push({
      product_id: parseInt(prodId),
      product_name: prodName,
      quantity: qty,
      price: price
    });
  }
  
  qtyInput.value = 1;
  renderOrderItemsTable();
}

function removeOrderItemRow(index) {
  selectedOrderItems.splice(index, 1);
  renderOrderItemsTable();
}

function renderOrderItemsTable() {
  const tbody = document.querySelector('#orderItemsTable tbody');
  tbody.innerHTML = '';
  
  let grandTotal = 0;
  
  selectedOrderItems.forEach((item, index) => {
    const total = item.quantity * item.price;
    grandTotal += total;
    tbody.innerHTML += `<tr>
      <td>${item.product_name}</td>
      <td>${item.quantity}</td>
      <td>${fmtShort(item.price)}</td>
      <td style="font-weight:600;">${fmtShort(total)}</td>
      <td>
        <button type="button" class="sample-btn" style="padding:2px 6px;border-color:var(--red);color:var(--red);" onclick="removeOrderItemRow(${index})">×</button>
      </td>
    </tr>`;
  });
  
  document.getElementById('order-grand-total').textContent = fmt(grandTotal);
}

async function saveOrder(e) {
  e.preventDefault();
  const customer_id = document.getElementById('order-customer').value;
  const status = document.getElementById('order-status').value;
  
  if (!customer_id || selectedOrderItems.length === 0) {
    alert("Please select a customer and add at least one product item.");
    return;
  }
  
  const res = await fetch('/api/orders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      customer_id: parseInt(customer_id),
      status: status,
      items: selectedOrderItems
    })
  });
  
  if (res.ok) {
    closeModal('modalOrder');
    loadOrders();
    loadDashboardStats();
  } else {
    const err = await res.json();
    alert(err.error || "Failed to place order.");
  }
}

async function changeStatus(orderId, newStatus) {
  const res = await fetch(`/api/orders/${orderId}/status`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus })
  });
  
  if (res.ok) {
    loadOrders();
    loadDashboardStats();
  } else {
    alert("Failed to update status.");
  }
}

// ── Pagination Helper ──
function paginate(type, direction) {
  currentPage[type] += direction;
  if (type === 'customers') renderCustomersTable();
  if (type === 'products') renderProductsTable();
  if (type === 'orders') renderOrdersTable();
}

// ── Sample CSV Generator ──
function downloadSample() {
  const rows = [
    'Date,Product,Category,Quantity,Price,Cost,Customer',
    '2025-01-05,MacBook Pro,Laptops,10,120000,90000,Alpha Tech Corp',
    '2025-01-12,Logitech MX Master,Accessories,50,8500,4500,Devendra Kumar',
    '2025-01-20,Mechanical Keyboard,Accessories,30,12000,7000,Nandini Kanaujiya',
    '2025-02-03,MacBook Pro,Laptops,8,120000,90000,Alpha Tech Corp',
    '2025-02-14,Dell 4K Monitor,Monitors,15,35000,24000,Devendra Kumar',
    '2025-02-22,Logitech MX Master,Accessories,60,8500,4500,Nandini Kanaujiya',
    '2025-03-01,Mechanical Keyboard,Accessories,45,12000,7000,Priya Singh',
    '2025-03-10,MacBook Pro,Laptops,12,125000,92000,Kunal Verma',
    '2025-03-18,Dell 4K Monitor,Monitors,20,36000,25000,Priya Singh',
    '2025-04-05,Logitech MX Master,Accessories,80,8700,4600,Kunal Verma',
    '2025-04-15,Sony WH-1000XM5,Headphones,25,28000,18000,Pooja Sharma',
    '2025-04-25,MacBook Pro,Laptops,9,125000,92000,Pooja Sharma',
    '2025-05-02,Mechanical Keyboard,Accessories,55,12200,7100,Nandini Kanaujiya',
    '2025-05-12,Sony WH-1000XM5,Headphones,30,28500,18200,Alpha Tech Corp',
    '2025-05-20,Dell 4K Monitor,Monitors,18,36500,25200,Devendra Kumar',
    '2025-06-01,MacBook Pro,Laptops,14,130000,95000,Kunal Verma',
    '2025-06-10,Logitech MX Master,Accessories,90,8900,4700,Nandini Kanaujiya',
    '2025-06-20,Sony WH-1000XM5,Headphones,35,29000,18500,Priya Singh',
  ];
  const blob = new Blob([rows.join('\n')], {type:'text/csv'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href=url; a.download='business_erp_sample.csv'; a.click();
  URL.revokeObjectURL(url);
}

// ── Sidebar toggling (Mobile) ──
function toggleSidebar() {
  document.querySelector('.sidebar').classList.toggle('open');
}
