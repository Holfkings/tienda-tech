// ===== Estado global =====
const state = {
    token: localStorage.getItem('token') || null,
    usuario: JSON.parse(localStorage.getItem('usuario') || 'null'),
    productos: [],
    categorias: [],
    carrito: [],
    filtroCategoria: '',
    busqueda: '',
};

// ===== Utilidades =====
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function formatCOP(valor) {
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(valor);
}

function showToast(msg, type = 'success') {
    const toast = $('#toast');
    toast.textContent = msg;
    toast.className = `toast show ${type}`;
    setTimeout(() => toast.classList.remove('show'), 3000);
}

async function api(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
        logout();
        throw new Error('Sesión expirada');
    }
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${res.status}`);
    }
    return res.status === 204 ? null : res.json();
}

// ===== Navegación =====
function navigate(view) {
    $$('.view').forEach(v => v.classList.remove('active'));
    $(`#view-${view}`).classList.add('active');
    $$('.nav-link, .mobile-link').forEach(l => l.classList.remove('active'));
    const link = $(`[data-nav="${view}"]`);
    if (link) link.classList.add('active');
    $('#mobile-menu').classList.remove('open');
    if (view === 'admin') loadAdmin();
    if (view === 'carrito') openCarrito();
}

// ===== Auth =====
function setAuth(token, usuario) {
    state.token = token;
    state.usuario = usuario;
    localStorage.setItem('token', token);
    localStorage.setItem('usuario', JSON.stringify(usuario));
    updateUI();
}

function logout() {
    state.token = null;
    state.usuario = null;
    localStorage.removeItem('token');
    localStorage.removeItem('usuario');
    updateUI();
    navigate('catalogo');
}

function updateUI() {
    const isAuth = !!state.token;
    const isAdmin = state.usuario?.es_admin;
    $$('.nav-login, .mobile-login').forEach(el => el.style.display = isAuth ? 'none' : '');
    $$('.nav-admin, .mobile-admin').forEach(el => el.style.display = isAdmin ? '' : 'none');
    if (isAuth) {
        $$('.nav-login').forEach(el => el.style.display = 'none');
    }
}

// ===== Productos =====
async function loadProductos() {
    try {
        const params = new URLSearchParams();
        if (state.filtroCategoria) params.set('categoria', state.filtroCategoria);
        if (state.busqueda) params.set('buscar', state.busqueda);
        const data = await api(`/api/productos?${params}`);
        state.productos = data;
        renderProductos();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function loadCategorias() {
    try {
        state.categorias = await api('/api/productos/categorias');
        const select = $('#filtro-categoria');
        select.innerHTML = '<option value="">Todas las categorías</option>';
        state.categorias.forEach(cat => {
            const opt = document.createElement('option');
            opt.value = cat;
            opt.textContent = cat;
            select.appendChild(opt);
        });
    } catch (e) { /* silencio */ }
}

function renderProductos() {
    const grid = $('#productos-grid');
    if (state.productos.length === 0) {
        grid.innerHTML = '<p style="grid-column:1/-1;text-align:center;color:var(--text-muted)">No se encontraron productos</p>';
        return;
    }
    grid.innerHTML = state.productos.map(p => `
        <div class="producto-card">
            <div class="producto-img">${p.imagen_url ? `<img src="${p.imagen_url}" alt="${p.nombre}" style="width:100%;height:100%;object-fit:cover">` : '📦'}</div>
            <div class="producto-info">
                <div class="producto-nombre">${p.nombre}</div>
                <div class="producto-descripcion">${p.descripcion || ''}</div>
                <div class="producto-precio">${formatCOP(p.precio)}</div>
                <div class="producto-stock ${p.stock === 0 ? 'sin-stock' : ''}">${p.stock === 0 ? 'Agotado' : `${p.stock} disponibles`}</div>
                <button class="btn-agregar" data-id="${p.id}" ${p.stock === 0 ? 'disabled' : ''}>Agregar al carrito</button>
            </div>
        </div>
    `).join('');
}

// ===== Carrito =====
async function loadCarrito() {
    if (!state.token) { renderCarritoVacio(); return; }
    try {
        state.carrito = await api('/api/carrito');
        renderCarrito();
    } catch (e) { renderCarritoVacio(); }
}

function renderCarritoVacio() {
    $('#carrito-items').innerHTML = '<div class="carrito-vacio">Tu carrito está vacío</div>';
    $('#carrito-total').textContent = formatCOP(0);
    $('#btn-comprar').disabled = true;
    updateCarritoCount();
}

function renderCarrito() {
    const container = $('#carrito-items');
    if (state.carrito.length === 0) { renderCarritoVacio(); return; }

    let total = 0;
    container.innerHTML = state.carrito.map(item => {
        const subtotal = item.producto.precio * item.cantidad;
        total += subtotal;
        return `
            <div class="carrito-item" data-id="${item.id}">
                <div class="carrito-item-img">${item.producto.imagen_url ? `<img src="${item.producto.imagen_url}" style="width:100%;height:100%;object-fit:cover;border-radius:8px">` : '📦'}</div>
                <div class="carrito-item-info">
                    <div class="carrito-item-nombre">${item.producto.nombre}</div>
                    <div class="carrito-item-precio">${formatCOP(item.producto.precio)} c/u</div>
                    <div class="carrito-item-cantidad">
                        <button class="btn-menos" data-id="${item.id}">−</button>
                        <span>${item.cantidad}</span>
                        <button class="btn-mas" data-id="${item.id}">+</button>
                    </div>
                </div>
                <button class="carrito-item-quitar" data-id="${item.id}">&times;</button>
            </div>
        `;
    }).join('');

    $('#carrito-total').textContent = formatCOP(total);
    $('#btn-comprar').disabled = false;
    updateCarritoCount();
}

function updateCarritoCount() {
    const count = state.carrito.reduce((sum, i) => sum + i.cantidad, 0);
    $('#carrito-count').textContent = count;
    $('#carrito-count-mobile').textContent = count;
}

async function agregarAlCarrito(productoId) {
    if (!state.token) { navigate('login'); return; }
    try {
        await api('/api/carrito', { method: 'POST', body: JSON.stringify({ producto_id: productoId, cantidad: 1 }) });
        showToast('Producto agregado al carrito');
        await loadCarrito();
    } catch (e) { showToast(e.message, 'error'); }
}

async function updateCarritoItem(itemId, cantidad) {
    try {
        await api(`/api/carrito/${itemId}`, { method: 'PUT', body: JSON.stringify({ cantidad }) });
        await loadCarrito();
    } catch (e) { showToast(e.message, 'error'); }
}

async function quitarDelCarrito(itemId) {
    try {
        await api(`/api/carrito/${itemId}`, { method: 'DELETE' });
        await loadCarrito();
    } catch (e) { showToast(e.message, 'error'); }
}

function openCarrito() {
    $('#carrito-overlay').classList.add('open');
    $('#carrito-drawer').classList.add('open');
    loadCarrito();
}

function closeCarrito() {
    $('#carrito-overlay').classList.remove('open');
    $('#carrito-drawer').classList.remove('open');
}

// ===== Admin =====
async function loadAdmin() {
    if (!state.usuario?.es_admin) { navigate('catalogo'); return; }
    try {
        const productos = await api('/api/productos?limit=500&solo_activos=false');
        renderAdminProductos(productos);
    } catch (e) { showToast(e.message, 'error'); }
}

function renderAdminProductos(productos) {
    const container = $('#admin-productos');
    container.innerHTML = productos.map(p => `
        <div class="admin-producto-item">
            <div class="admin-producto-info">
                <div class="admin-producto-nombre">${p.nombre}</div>
                <div class="admin-producto-meta">SKU: ${p.sku} · ${formatCOP(p.precio)} · Stock: ${p.stock} · ${p.activo ? 'Activo' : 'Inactivo'}</div>
            </div>
            <div class="admin-producto-actions">
                <button class="btn-edit" data-id="${p.id}">Editar</button>
                <button class="btn-delete" data-id="${p.id}">Eliminar</button>
            </div>
        </div>
    `).join('');
}

function openModal(producto = null) {
    $('#modal-title').textContent = producto ? 'Editar Producto' : 'Nuevo Producto';
    $('#prod-id').value = producto?.id || '';
    $('#prod-sku').value = producto?.sku || '';
    $('#prod-nombre').value = producto?.nombre || '';
    $('#prod-descripcion').value = producto?.descripcion || '';
    $('#prod-precio').value = producto?.precio || '';
    $('#prod-stock').value = producto?.stock ?? '';
    $('#prod-categoria').value = producto?.categoria || '';
    $('#prod-imagen').value = producto?.imagen_url || '';
    $('#prod-activo').checked = producto?.activo ?? true;
    $('#modal-producto').classList.add('open');
}

function closeModal() {
    $('#modal-producto').classList.remove('open');
}

async function saveProducto(e) {
    e.preventDefault();
    const id = $('#prod-id').value;
    const data = {
        sku: $('#prod-sku').value,
        nombre: $('#prod-nombre').value,
        descripcion: $('#prod-descripcion').value,
        precio: parseFloat($('#prod-precio').value),
        stock: parseInt($('#prod-stock').value),
        categoria: $('#prod-categoria').value,
        imagen_url: $('#prod-imagen').value,
        activo: $('#prod-activo').checked,
    };
    try {
        if (id) {
            await api(`/api/productos/${id}`, { method: 'PUT', body: JSON.stringify(data) });
            showToast('Producto actualizado');
        } else {
            await api('/api/productos', { method: 'POST', body: JSON.stringify(data) });
            showToast('Producto creado');
        }
        closeModal();
        loadAdmin();
        loadProductos();
    } catch (e) { showToast(e.message, 'error'); }
}

async function deleteProducto(id) {
    if (!confirm('¿Eliminar este producto?')) return;
    try {
        await api(`/api/productos/${id}`, { method: 'DELETE' });
        showToast('Producto eliminado');
        loadAdmin();
        loadProductos();
    } catch (e) { showToast(e.message, 'error'); }
}

// ===== Eventos =====
function initEventos() {
    // Nav
    $$('[data-nav]').forEach(el => {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            navigate(el.dataset.nav);
        });
    });

    // Hamburger
    $('#hamburger').addEventListener('click', () => {
        $('#mobile-menu').classList.toggle('open');
    });

    // Buscador
    let debounce;
    $('#buscador').addEventListener('input', (e) => {
        clearTimeout(debounce);
        debounce = setTimeout(() => {
            state.busqueda = e.target.value;
            loadProductos();
        }, 300);
    });

    // Filtro categoría
    $('#filtro-categoria').addEventListener('change', (e) => {
        state.filtroCategoria = e.target.value;
        loadProductos();
    });

    // Agregar al carrito (delegación)
    $('#productos-grid').addEventListener('click', (e) => {
        if (e.target.classList.contains('btn-agregar')) {
            agregarAlCarrito(parseInt(e.target.dataset.id));
        }
    });

    // Carrito drawer
    $('#carrito-close').addEventListener('click', closeCarrito);
    $('#carrito-overlay').addEventListener('click', closeCarrito);

    // Carrito acciones (delegación)
    $('#carrito-items').addEventListener('click', (e) => {
        const id = e.target.dataset.id;
        if (!id) return;
        if (e.target.classList.contains('btn-mas')) {
            const item = state.carrito.find(i => i.id === parseInt(id));
            updateCarritoItem(parseInt(id), item.cantidad + 1);
        } else if (e.target.classList.contains('btn-menos')) {
            const item = state.carrito.find(i => i.id === parseInt(id));
            if (item.cantidad <= 1) quitarDelCarrito(parseInt(id));
            else updateCarritoItem(parseInt(id), item.cantidad - 1);
        } else if (e.target.classList.contains('carrito-item-quitar')) {
            quitarDelCarrito(parseInt(id));
        }
    });

    // Comprar
    $('#btn-comprar').addEventListener('click', () => {
        showToast('Funcionalidad de pago próximamente');
    });

    // Auth tabs
    $$('.auth-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            $$('.auth-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const isLogin = tab.dataset.tab === 'login';
            $('#form-login').style.display = isLogin ? '' : 'none';
            $('#form-register').style.display = isLogin ? 'none' : '';
        });
    });

    // Login
    $('#form-login').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const data = await api('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify({ email: $('#login-email').value, password: $('#login-password').value }),
            });
            setAuth(data.access_token, { email: $('#login-email').value, es_admin: data.es_admin || false });
            showToast('Bienvenido');
            navigate('catalogo');
        } catch (e) { showToast(e.message, 'error'); }
    });

    // Register
    $('#form-register').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const data = await api('/api/auth/register', {
                method: 'POST',
                body: JSON.stringify({
                    nombre: $('#reg-nombre').value,
                    email: $('#reg-email').value,
                    password: $('#reg-password').value,
                }),
            });
            setAuth(data.access_token, { email: $('#reg-email').value, es_admin: data.es_admin || false });
            showToast('Cuenta creada');
            navigate('catalogo');
        } catch (e) { showToast(e.message, 'error'); }
    });

    // Admin
    $('#btn-nuevo-producto').addEventListener('click', () => openModal());
    $('#modal-cancelar').addEventListener('click', closeModal);
    $('#modal-producto').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeModal();
    });
    $('#form-producto').addEventListener('submit', saveProducto);

    // Admin acciones (delegación)
    $('#admin-productos').addEventListener('click', async (e) => {
        const id = e.target.dataset.id;
        if (!id) return;
        if (e.target.classList.contains('btn-edit')) {
            const productos = await api('/api/productos?limit=500&solo_activos=false');
            const prod = productos.find(p => p.id === parseInt(id));
            if (prod) openModal(prod);
        } else if (e.target.classList.contains('btn-delete')) {
            deleteProducto(parseInt(id));
        }
    });
}

// ===== Init =====
async function init() {
    updateUI();
    initEventos();
    await Promise.all([loadProductos(), loadCategorias()]);
    if (state.token) loadCarrito();
}

document.addEventListener('DOMContentLoaded', init);
