/**
 * SmartRetailX - Shared Frontend Utilities
 * api.js — API client constants, JWT session management, and helpers
 *
 * Phase 2 changes:
 *   - session.save() now stores the full JWT access_token
 *   - apiFetch() automatically attaches Authorization: Bearer <token>
 *   - session.getRole() / session.isAdmin() decode the JWT payload client-side
 *   - applyRbacNav() hides the Admin link for non-admin users
 */

// ── Service Base URLs ────────────────────────────────────────────────────────
const API = {
  USER:      'http://localhost:8001',
  PRODUCT:   'http://localhost:8002',
  ORDER:     'http://localhost:8003',
  INVENTORY: 'http://localhost:8004',
};

// ── Cart Storage & User Isolation ──────────────────────────────────────────────
/**
 * Manages shopping cart state in localStorage isolated per user ID.
 * Storage key format: `srx_cart_${user_id}` or `srx_cart_guest`.
 */
const cartManager = {
  getStorageKey() {
    const user = session.getUser();
    return (user && user.user_id) ? `srx_cart_${user.user_id}` : 'srx_cart_guest';
  },

  getCart() {
    try {
      const key = this.getStorageKey();
      return JSON.parse(localStorage.getItem(key) || '[]');
    } catch (_) {
      return [];
    }
  },

  saveCart(cartItems) {
    const key = this.getStorageKey();
    localStorage.setItem(key, JSON.stringify(cartItems));
  },

  clearActiveCart() {
    const key = this.getStorageKey();
    localStorage.removeItem(key);
    sessionStorage.removeItem('srx_cart');
    localStorage.removeItem('srx_cart');
  }
};

// ── JWT Session Store ─────────────────────────────────────────────────────────
/**
 * Stores the JWT access_token and user metadata in localStorage.
 *
 * Security note: localStorage is used here for simplicity in the local Phase 2
 * build. In a production deployment (Phase 3 / AWS), the access_token should be
 * stored in an httpOnly cookie to prevent XSS theft. The metadata (email, role)
 * can remain in localStorage since they are not used for authentication — the
 * token itself is always the authoritative credential.
 */
const session = {
  /** Saves the LoginResponse from the User Service. */
  save(loginData) {
    localStorage.setItem('srx_token', loginData.access_token);
    localStorage.setItem('srx_user', JSON.stringify({
      user_id: loginData.user_id,
      email:   loginData.email,
      role:    loginData.role,
    }));
  },

  /** Returns the raw JWT string, or null if not logged in. */
  getToken() {
    return localStorage.getItem('token') || localStorage.getItem('srx_token');
  },

  /** Returns stored user metadata object {user_id, email, role}. */
  load() {
    try { return JSON.parse(localStorage.getItem('srx_user')); } catch (_) { return null; }
  },

  /** Clears both the token, user metadata, and active cart on logout or session expiration. */
  clear() {
    cartManager.clearActiveCart();
    localStorage.removeItem('srx_token');
    localStorage.removeItem('srx_user');
  },

  logout() {
    this.clear();
    showToast('Signed out successfully.', 'info');
    setTimeout(() => { window.location.href = 'index.html'; }, 500);
  },

  isLoggedIn() { return !!this.getToken(); },
  getUser()    { return this.load(); },

  /** Returns 'admin', 'customer', or null. Read from stored metadata (not decoded JWT). */
  getRole()  { const u = this.load(); return u ? u.role : null; },
  isAdmin()  { return this.getRole() === 'admin'; },
};

// ── JWT Payload Decoder (client-side, no verification) ────────────────────────
/**
 * Decodes a JWT payload without verifying the signature.
 * Verification happens server-side; client-side we only read claims for UI logic.
 * Never trust client-decoded claims for security decisions.
 */
function decodeJwtPayload(token) {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(base64));
  } catch (_) {
    return null;
  }
}

// ── Generic Fetch Wrapper ─────────────────────────────────────────────────────
/**
 * Wraps fetch() with:
 *   - Content-Type: application/json
 *   - Authorization: Bearer <token>  (automatically attached if logged in)
 *   - Consistent error extraction from FastAPI {detail: "..."} responses
 *   - Network error detection (doesn't trigger 401 session wipes on connection failures)
 */
async function apiFetch(url, options = {}) {
  const headers = { 'Content-Type': 'application/json' };

  // Attach JWT Bearer token automatically if one exists in session
  const token = session.getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const merged = {
    headers,
    ...options,
    // Merge caller-provided headers on top (allows override if needed)
    headers: { ...headers, ...(options.headers || {}) },
  };

  if (merged.body && typeof merged.body !== 'string') {
    merged.body = JSON.stringify(merged.body);
  }

  let response;
  try {
    response = await fetch(url, merged);
  } catch (netErr) {
    // Intercept network/CORS connectivity errors so session is NOT wiped
    throw new Error(`Unable to reach service at ${url}. Please check if the service is running.`);
  }

  if (response.status === 401) {
    // Token expired or invalid — clear session and redirect to login
    session.clear();
    showToast('Your session has expired. Please sign in again.', 'error');
    setTimeout(() => { window.location.href = 'index.html'; }, 1500);
    throw new Error('Session expired');
  }

  if (!response.ok) {
    let errMsg = `HTTP ${response.status}`;
    try {
      const errData = await response.json();
      errMsg = errData.detail || JSON.stringify(errData);
    } catch (_) { /* ignore parse errors */ }
    throw new Error(errMsg);
  }

  if (response.status === 204) return null;
  return response.json();
}

// ── Order Placement Helper ───────────────────────────────────────────────────
/**
 * Places an order via POST /orders on Order Service.
 * Ensures Authorization header is explicitly attached with Bearer token.
 */
async function placeOrder(orderData) {
  const token = session.getToken() || localStorage.getItem('token') || localStorage.getItem('srx_token');
  if (!token) {
    throw new Error('You must be signed in to place an order.');
  }
  return await apiFetch(`${API.ORDER}/orders`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: orderData,
  });
}

// ── Customer Order History Helper ─────────────────────────────────────────────
/**
 * Fetches order history for the currently logged-in user.
 * Sends Authorization: Bearer <token>. Filters results to match user_id if customer.
 */
async function fetchMyOrders() {
  const user = session.getUser();
  if (!user || !user.user_id) {
    throw new Error('You must be signed in to view your order history.');
  }

  let orders = [];
  try {
    orders = await apiFetch(`${API.ORDER}/orders/user/${user.user_id}`);
  } catch (_) {
    orders = await apiFetch(`${API.ORDER}/orders?limit=200`);
  }

  if (!Array.isArray(orders)) orders = [];

  // Filter orders by user_id for customers
  if (!session.isAdmin()) {
    orders = orders.filter(o => o.user_id === user.user_id);
  }

  return orders;
}

// ── Restock Product Helper ───────────────────────────────────────────────────
/**
 * Restocks a product in the Inventory Service (creates inventory record if not found).
 */
async function restockProduct(productId, quantity) {
  return await apiFetch(`${API.INVENTORY}/inventory/${productId}/restock?quantity=${quantity}`, {
    method: 'PATCH',
  });
}

// ── RBAC: Hide Admin Nav Link for Non-Admin Users ────────────────────────────
/**
 * Reads the stored role and removes the Admin navigation link
 * if the current user is not an admin.
 * Call this on every page's DOMContentLoaded or script init.
 */
function applyRbacNav() {
  if (!session.isAdmin()) {
    // Hide all nav links pointing to admin.html
    document.querySelectorAll('a[href="admin.html"]').forEach(link => {
      link.style.display = 'none';
    });
  }
}

// ── Toast Notifications ───────────────────────────────────────────────────────
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'opacity 200ms ease, transform 200ms ease';
    setTimeout(() => toast.remove(), 200);
  }, 3500);
}

// ── Format Helpers ─────────────────────────────────────────────────────────────
function formatCurrency(value) {
  return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(value);
}

function formatDate(isoString) {
  if (!isoString) return '—';
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(new Date(isoString));
}

function statusBadge(status) {
  const map = {
    pending:   'badge-warning',
    confirmed: 'badge-info',
    shipped:   'badge-info',
    delivered: 'badge-success',
    cancelled: 'badge-danger',
    customer:  'badge-neutral',
    admin:     'badge-info',
  };
  const cls = map[status] || 'badge-neutral';
  return `<span class="badge ${cls}">${status}</span>`;
}

// ── Live Inventory Helper ──────────────────────────────────────────────────────
/**
 * Fetches the live, single-source-of-truth stock level for a product from the Inventory Service (Port 8004).
 */
async function getLiveInventoryStock(productId) {
  try {
    const data = await apiFetch(`${API.INVENTORY}/inventory/${productId}`);
    return (data && typeof data.stock_quantity === 'number') ? data.stock_quantity : 0;
  } catch (_) {
    return 0;
  }
}

// ── Service Health Check ───────────────────────────────────────────────────────
async function checkServiceHealth(baseUrl, dotId) {
  const dot = document.getElementById(dotId);
  if (!dot) return;
  dot.className = 'service-dot checking';
  try {
    await fetch(`${baseUrl}/health`, { signal: AbortSignal.timeout(2500) });
    dot.className = 'service-dot online';
    dot.title = 'Online';
  } catch (_) {
    dot.className = 'service-dot offline';
    dot.title = 'Offline — start the service with uvicorn';
  }
}
