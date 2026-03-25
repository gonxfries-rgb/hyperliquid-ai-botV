function authHeaders() {
  const token = document.getElementById('token').value.trim();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchJson(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    body = text;
  }
  if (!response.ok) {
    throw new Error(typeof body === 'string' ? body : JSON.stringify(body, null, 2));
  }
  return body;
}

function renderPills(status) {
  const pillHost = document.getElementById('status-pills');
  pillHost.innerHTML = '';
  const items = [
    `connected: ${status.connected}`,
    `running: ${status.running}`,
    `panic: ${status.panic_mode}`,
    `mode: ${status.mode}`,
    `env: ${status.app_env}`,
    `symbol: ${status.symbol}`,
    `mid: ${status.current_mid ?? 'n/a'}`,
  ];
  items.forEach((item) => {
    const span = document.createElement('span');
    span.className = 'pill';
    span.textContent = item;
    pillHost.appendChild(span);
  });
}

async function refresh() {
  try {
    const [status, events, orders] = await Promise.all([
      fetchJson('/api/status'),
      fetchJson('/api/events?limit=20'),
      fetchJson('/api/orders?limit=20'),
    ]);
    renderPills(status);
    document.getElementById('status-json').textContent = JSON.stringify(status, null, 2);
    document.getElementById('events-json').textContent = JSON.stringify(events.items, null, 2);
    document.getElementById('orders-json').textContent = JSON.stringify(orders.items, null, 2);
  } catch (error) {
    document.getElementById('status-json').textContent = `Error: ${error.message}`;
  }
}

async function postAction(path) {
  try {
    const response = await fetchJson(path, { method: 'POST' });
    document.getElementById('control-response').textContent = JSON.stringify(response, null, 2);
    refresh();
  } catch (error) {
    document.getElementById('control-response').textContent = `Error: ${error.message}`;
  }
}

async function submitTestOrder() {
  const payload = {
    symbol: document.getElementById('symbol').value.trim().toUpperCase(),
    side: document.getElementById('side').value,
    size: Number(document.getElementById('size').value),
    order_type: document.getElementById('order-type').value,
    limit_price: document.getElementById('limit-price').value ? Number(document.getElementById('limit-price').value) : null,
    reduce_only: false,
  };
  try {
    const response = await fetchJson('/api/control/test-order', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    document.getElementById('control-response').textContent = JSON.stringify(response, null, 2);
    refresh();
  } catch (error) {
    document.getElementById('control-response').textContent = `Error: ${error.message}`;
  }
}

async function flattenSymbol() {
  const symbol = document.getElementById('symbol').value.trim().toUpperCase();
  postAction(`/api/control/flatten/${symbol}`);
}

refresh();
setInterval(refresh, 4000);
