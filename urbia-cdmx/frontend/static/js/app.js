/**
 * URBIA CDMX — Frontend JavaScript
 * Mejoras: (1) explicación del motor, (2) leyenda niveles,
 * (3) perímetros de alcaldías, (4) normalización de nombres,
 * (5) alerta de NA/desconocida, (6) filtros multinivel
 */

const API = '';

// ── Estado global ────────────────────────────────────────────────────────────
let mapaLeaflet   = null;
let marcadores    = [];
let perimetroLayer = null;
let incidentesCache = [];
let pesosActuales = { S: 0.30, D: 0.25, M: 0.20, A: 0.15, R: 0.10 };

// ── Mejora 2: descripciones de cada nivel ───────────────────────────────────
const NIVELES = {
  critica: { label: 'Crítica',  rango: '70–100', color: '#dc2626', bg: '#fee2e2', desc: 'Requiere atención inmediata por riesgo grave para personas o infraestructura.' },
  alta:    { label: 'Alta',     rango: '50–69',  color: '#ea580c', bg: '#ffedd5', desc: 'Requiere atención prioritaria. Alto impacto o probabilidad de agravarse.' },
  media:   { label: 'Media',    rango: '30–49',  color: '#ca8a04', bg: '#fef9c3', desc: 'Necesita atención programada. Sin evidencia de riesgo inmediato.' },
  baja:    { label: 'Baja',     rango: '0–29',   color: '#16a34a', bg: '#dcfce7', desc: 'Puede atenderse mediante mantenimiento rutinario y seguimiento.' },
};

// ── Navegación ───────────────────────────────────────────────────────────────
document.querySelectorAll('nav a').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const sec = link.dataset.section;
    document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
    link.classList.add('active');
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(`sec-${sec}`).classList.add('active');
    document.getElementById('page-title').textContent = link.textContent.trim();
    if (sec === 'mapa') { if (!mapaLeaflet) iniciarMapa(); else filtrarMapa(); }
    if (sec === 'ranking') { cargarRanking(); cargarExplicacionMotor(); }
    if (sec === 'planeacion') actualizarPlanes();
    if (sec === 'fuentes') cargarFuentes();
    if (sec === 'chat') cargarSugerencias();
  });
});

// ── Helpers ──────────────────────────────────────────────────────────────────
async function fetchJSON(url) {
  const r = await fetch(API + url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

function colorPrioridad(nivel, esEmergencia) {
  if (esEmergencia || nivel === 'critica') return '#dc2626';
  if (nivel === 'alta')   return '#ea580c';
  if (nivel === 'media')  return '#ca8a04';
  return '#16a34a';
}

function iconoMapa(nivel, esEmergencia) {
  const color = colorPrioridad(nivel, esEmergencia);
  const anim  = esEmergencia ? 'animation:pulso 1s infinite;' : '';
  return L.divIcon({
    html: `<div style="background:${color};width:14px;height:14px;border-radius:50%;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.4);${anim}"></div>`,
    className: '', iconSize: [14,14], iconAnchor: [7,7],
  });
}

function formatPeso(val) { return (val * 100).toFixed(0) + '%'; }

// ── Resumen ──────────────────────────────────────────────────────────────────
async function cargarResumen() {
  try {
    const d = await fetchJSON('/api/resumen');
    document.getElementById('last-update').textContent = 'Act: ' + new Date().toLocaleTimeString('es-MX');
    document.getElementById('cards-resumen').innerHTML = `
      <div class="card blue"><div class="label">Reportes</div><div class="value">${d.total_reportes.toLocaleString()}</div><div class="sub">registrados</div></div>
      <div class="card"><div class="label">Incidentes únicos</div><div class="value">${d.incidentes_unicos.toLocaleString()}</div><div class="sub">estimados</div></div>
      <div class="card orange"><div class="label">Casos abiertos</div><div class="value">${d.casos_abiertos.toLocaleString()}</div><div class="sub">sin atender</div></div>
      <div class="card red"><div class="label">Críticos/Altos</div><div class="value">${d.casos_criticos.toLocaleString()}</div><div class="sub">prioritarios</div></div>
      <div class="card red"><div class="label">Emergencias</div><div class="value">${d.casos_emergencia}</div><div class="sub">activas ⚠️</div></div>
      <div class="card green"><div class="label">Alcaldías</div><div class="value">${d.alcaldias_analizadas}</div><div class="sub">analizadas</div></div>
    `;
    cargarGraficasResumen();
  } catch(e) {
    document.getElementById('cards-resumen').innerHTML = `<div class="alert alert-warn">Error: ${e.message}</div>`;
  }
}

async function cargarGraficasResumen() {
  try {
    const incidentes = await fetchJSON('/api/incidentes');
    incidentesCache = incidentes;
    const cats = {}, alcs = {}, nivs = { critica:0, alta:0, media:0, baja:0 };
    incidentes.forEach(i => {
      cats[i.categoria] = (cats[i.categoria]||0) + 1;
      if (i.alcaldia) alcs[i.alcaldia] = (alcs[i.alcaldia]||0) + 1;
      if (nivs[i.nivel_prioridad] !== undefined) nivs[i.nivel_prioridad]++;
    });
    document.getElementById('chart-categoria').innerHTML = barras(cats);
    document.getElementById('chart-alcaldia').innerHTML  = barras(alcs);
    document.getElementById('chart-niveles').innerHTML   = barrasNivel(nivs);
  } catch(e) {}
}

function barras(obj) {
  const colores = { vial:'#2563eb', hidraulica:'#0891b2', seguridad:'#dc2626', otro:'#94a3b8' };
  const max = Math.max(...Object.values(obj), 1);
  return Object.entries(obj).sort((a,b)=>b[1]-a[1]).slice(0,10).map(([k,v]) => `
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:7px;">
      <div style="font-size:12px;width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#374151">${k}</div>
      <div style="flex:1;height:14px;background:#f1f5f9;border-radius:3px;overflow:hidden;">
        <div style="height:100%;width:${(v/max*100).toFixed(0)}%;background:${colores[k]||'#64748b'};border-radius:3px;transition:width .4s"></div>
      </div>
      <div style="font-size:12px;font-weight:600;width:30px;text-align:right;">${v.toLocaleString()}</div>
    </div>`).join('');
}

function barrasNivel(obj) {
  return Object.entries(NIVELES).map(([k, n]) => {
    const v = obj[k] || 0;
    const max = Math.max(...Object.values(obj), 1);
    return `
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:7px;">
      <div style="font-size:12px;width:60px;font-weight:600;color:${n.color}">${n.label}</div>
      <div style="flex:1;height:14px;background:#f1f5f9;border-radius:3px;overflow:hidden;">
        <div style="height:100%;width:${(v/max*100).toFixed(0)}%;background:${n.color};border-radius:3px;"></div>
      </div>
      <div style="font-size:12px;font-weight:600;width:40px;text-align:right;">${v.toLocaleString()}</div>
      <div style="font-size:11px;color:#94a3b8;width:50px;">${n.rango}</div>
    </div>`;
  }).join('');
}

// ── Mapa ──────────────────────────────────────────────────────────────────────
function iniciarMapa() {
  mapaLeaflet = L.map('map').setView([19.42, -99.13], 11);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors', maxZoom: 18,
  }).addTo(mapaLeaflet);
  cargarAlcaldiasFiltros();
  cargarCapaMapa();
}

async function cargarCapaMapa() {
  marcadores.forEach(m => mapaLeaflet.removeLayer(m));
  marcadores = [];
  try {
    const alcaldia  = document.getElementById('filtro-alcaldia-mapa')?.value || '';
    const categoria = document.getElementById('filtro-categoria-mapa')?.value || '';
    const nivelesChecked = [...document.querySelectorAll('.check-nivel:checked')].map(c => c.value);

    let url = '/api/mapa';
    const params = [];
    if (alcaldia)  params.push(`alcaldia=${encodeURIComponent(alcaldia)}`);
    if (categoria) params.push(`categoria=${encodeURIComponent(categoria)}`);
    if (nivelesChecked.length > 0 && nivelesChecked.length < 4)
      params.push(`nivel_prioridad=${encodeURIComponent(nivelesChecked.join(','))}`);
    if (params.length) url += '?' + params.join('&');

    const data = await fetchJSON(url);
    data.forEach(inc => {
      const m = L.marker([inc.latitud, inc.longitud], {
        icon: iconoMapa(inc.nivel_prioridad, inc.es_emergencia)
      });
      const color   = colorPrioridad(inc.nivel_prioridad, inc.es_emergencia);
      const nInfo   = NIVELES[inc.nivel_prioridad] || {};
      const origenTag = inc.origen === 'demo'
        ? '<span style="color:#7c3aed;font-size:11px;">⚠️ DEMO</span>'
        : '<span style="color:#6b7280;font-size:11px;">📋 Histórico real</span>';
      m.bindPopup(`
        <div style="font-family:Inter,sans-serif;min-width:230px;">
          ${inc.es_emergencia ? '<div style="background:#fee2e2;color:#dc2626;padding:4px 8px;border-radius:4px;font-size:11px;font-weight:700;margin-bottom:8px;">⚠️ EMERGENCIA ACTIVA</div>' : ''}
          <strong style="font-size:13px;">${inc.calle || 'Sin calle registrada'}</strong><br>
          <span style="font-size:12px;color:#64748b;">${inc.alcaldia || 'Alcaldía no confirmada'} · ${inc.colonia || ''}</span>
          <div style="margin:8px 0;padding:8px;background:#f8fafc;border-radius:6px;font-size:12px;">
            <div>Tipo: <b>${inc.tipo || inc.categoria}</b></div>
            <div>Puntaje: <b style="color:${color}">${(inc.puntaje_total||0).toFixed(1)}/100</b></div>
            <div>Reportes: <b>${inc.total_reportes}</b></div>
            <div style="margin-top:5px;">
              <span style="display:inline-block;padding:2px 8px;border-radius:4px;background:${nInfo.bg||'#f1f5f9'};color:${color};font-weight:700;font-size:11px;">
                ${(inc.nivel_prioridad||'').toUpperCase()} (${nInfo.rango||''})
              </span>
            </div>
            ${nInfo.desc ? `<div style="font-size:11px;color:#64748b;margin-top:4px;">${nInfo.desc}</div>` : ''}
          </div>
          ${origenTag}
        </div>`);
      m.addTo(mapaLeaflet);
      marcadores.push(m);
    });

    // Mejora 3: perímetro de alcaldía seleccionada
    if (alcaldia) dibujarPerimetro(alcaldia);
    else { if (perimetroLayer) { mapaLeaflet.removeLayer(perimetroLayer); perimetroLayer = null; } }
  } catch(e) { console.error('Error mapa:', e); }
}

// Mejora 3: perímetro y zoom automático
async function dibujarPerimetro(alcaldia) {
  if (perimetroLayer) { mapaLeaflet.removeLayer(perimetroLayer); perimetroLayer = null; }
  if (!alcaldia) return;
  try {
    const data = await fetchJSON(`/api/alcaldias/perimetros?alcaldia=${encodeURIComponent(alcaldia)}`);
    if (!data.perimetro) return;
    perimetroLayer = L.polygon(data.perimetro, {
      color: '#2563eb', weight: 2.5, opacity: 0.9,
      fillColor: '#2563eb', fillOpacity: 0.05, dashArray: '6,4',
    }).addTo(mapaLeaflet);
    perimetroLayer.bindTooltip(`📍 ${alcaldia} — perímetro aproximado`, { permanent: false });
    mapaLeaflet.fitBounds(perimetroLayer.getBounds(), { padding: [30, 30] });
  } catch(e) { console.warn('Sin perímetro para:', alcaldia); }
}

function filtrarMapa() { cargarCapaMapa(); }

function toggleTodosNiveles(checked) {
  document.querySelectorAll('.check-nivel').forEach(c => c.checked = checked);
  cargarCapaMapa();
}

// ── Mejora 4+5: alcaldías normalizadas ───────────────────────────────────────
async function cargarAlcaldiasFiltros() {
  try {
    // Mejora 4: usamos el catálogo oficial de las 16 alcaldías
    const catalogo = await fetchJSON('/api/alcaldias/catalogo');
    ['filtro-alcaldia-mapa', 'filtro-alcaldia-ranking'].forEach(id => {
      const sel = document.getElementById(id);
      if (!sel) return;
      // Limpiar opciones existentes excepto la primera
      while (sel.options.length > 1) sel.remove(1);
      catalogo.forEach(a => {
        const opt = document.createElement('option');
        opt.value = a; opt.textContent = a;
        sel.appendChild(opt);
      });
    });
  } catch(e) {}
}

// ── Ranking ───────────────────────────────────────────────────────────────────
async function cargarRanking() {
  const alcaldia = document.getElementById('filtro-alcaldia-ranking')?.value || '';
  const categoria = document.getElementById('filtro-categoria-ranking')?.value || '';
  const nivel = document.getElementById('filtro-prioridad-ranking')?.value || '';
  let url = '/api/incidentes';
  const params = [];
  if (alcaldia)  params.push(`alcaldia=${encodeURIComponent(alcaldia)}`);
  if (categoria) params.push(`categoria=${encodeURIComponent(categoria)}`);
  if (nivel)     params.push(`nivel_prioridad=${encodeURIComponent(nivel)}`);
  if (params.length) url += '?' + params.join('&');

  try {
    const data = await fetchJSON(url);
    incidentesCache = data;
    const tbody = document.getElementById('ranking-tbody');
    if (!data.length) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#94a3b8;padding:24px;">Sin incidentes con los filtros seleccionados.</td></tr>';
      return;
    }
    tbody.innerHTML = data.map((inc, i) => {
      const color  = colorPrioridad(inc.nivel_prioridad, inc.es_emergencia);
      const nInfo  = NIVELES[inc.nivel_prioridad] || {};
      const pct    = (inc.puntaje_total || 0).toFixed(1);
      const badgeClass = inc.es_emergencia ? 'badge-emergencia' : `badge-${inc.nivel_prioridad||'baja'}`;
      const badgeText  = inc.es_emergencia ? '⚠️ EMERGENCIA' : `${nInfo.label||inc.nivel_prioridad} (${nInfo.rango||''})`;
      // Mejora 5: marcar visualmente los sin alcaldía
      const alcaldiaDisplay = inc.alcaldia
        ? inc.alcaldia
        : '<span style="color:#94a3b8;font-size:11px;">Sin confirmar</span>';
      const origenBadge = inc.origen === 'real'
        ? '<span class="badge badge-real">Real</span>'
        : '<span class="badge badge-demo">Demo</span>';
      const just = (inc.justificacion||'').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      return `
        <tr>
          <td style="font-weight:700;color:#94a3b8">${i+1}</td>
          <td>
            <div style="font-weight:600;font-size:13px;">${inc.calle || '—'}</div>
            <div style="font-size:11px;color:#94a3b8;">${alcaldiaDisplay} · ${inc.colonia||''}</div>
          </td>
          <td><span style="font-size:12px;">${inc.tipo||inc.categoria||'—'}</span></td>
          <td style="font-weight:600;text-align:center;">${inc.total_reportes||1}</td>
          <td>
            <span class="badge ${badgeClass}">${badgeText}</span>
            <div style="font-size:11px;color:#94a3b8;margin-top:3px;">${nInfo.desc||''}</div>
          </td>
          <td>
            <div class="puntaje-bar">
              <div class="puntaje-track">
                <div class="puntaje-fill" style="width:${pct}%;background:${color};"></div>
              </div>
              <span style="font-size:12px;font-weight:700;color:${color};white-space:nowrap">${pct}</span>
            </div>
          </td>
          <td>${origenBadge}</td>
          <td>
            <button class="justificacion-btn" onclick="toggleJust('just-${inc.id}')">Ver ▾</button>
            <div class="justificacion-panel" id="just-${inc.id}">${just||'Sin justificación.'}</div>
          </td>
        </tr>`;
    }).join('');
  } catch(e) {
    document.getElementById('ranking-tbody').innerHTML = `<tr><td colspan="8">${e.message}</td></tr>`;
  }
}

function toggleJust(id) {
  const el = document.getElementById(id);
  el.style.display = el.style.display === 'block' ? 'none' : 'block';
}

// ── Mejora 1: explicación del motor ─────────────────────────────────────────
async function cargarExplicacionMotor() {
  const detalle = document.getElementById('motor-detalle');
  if (!detalle || detalle.dataset.cargado) return;  // cargar solo una vez
  try {
    const d = await fetchJSON('/api/motor/explicacion');
    detalle.dataset.cargado = '1';

    document.getElementById('motor-advertencia').textContent = d.advertencia;
    document.getElementById('motor-formula').textContent = d.formula;
    document.getElementById('motor-nota-emerg').textContent = d.nota_emergencias;

    // Variables
    document.getElementById('motor-variables').innerHTML = d.variables.map(v => `
      <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin-bottom:10px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
          <span style="font-size:22px;font-weight:800;color:#2563eb;">${v.clave}</span>
          <div>
            <div style="font-size:14px;font-weight:700;">${v.nombre}</div>
            <div style="font-size:12px;color:#64748b;">Peso: <b>${(v.peso*100).toFixed(0)}%</b></div>
          </div>
        </div>
        <p style="font-size:12px;color:#64748b;margin-bottom:8px;">${v.descripcion}</p>
        ${v.formula ? `<div style="font-family:monospace;font-size:12px;background:#fff;padding:6px 10px;border-radius:4px;margin-bottom:8px;border:1px solid #e2e8f0;">${v.formula}</div>` : ''}
        <div style="display:flex;flex-wrap:wrap;gap:5px;">
          ${(v.rangos||v.indicadores||[]).map(r => `
            <span style="font-size:11px;padding:2px 8px;background:#fff;border:1px solid #e2e8f0;border-radius:4px;">
              ${r.condicion}: <b>${r.puntaje??r.puntos}</b>
            </span>`).join('')}
        </div>
        ${v.nota ? `<p style="font-size:11px;color:#94a3b8;margin-top:6px;">ℹ️ ${v.nota}</p>` : ''}
      </div>`).join('');

    // Niveles de riesgo
    document.getElementById('motor-niveles').innerHTML = d.niveles_prioridad.map(n => `
      <div style="display:flex;align-items:flex-start;gap:10px;padding:10px 12px;border-radius:8px;margin-bottom:7px;background:${n.color}11;border:1px solid ${n.color}44;">
        <span style="display:inline-block;padding:3px 12px;border-radius:5px;background:${n.color}22;color:${n.color};font-weight:700;font-size:12px;white-space:nowrap;">${n.nivel} ${n.rango}</span>
        <span style="font-size:12px;color:#374151;">${n.descripcion}</span>
      </div>`).join('');
  } catch(e) { console.warn('Motor no disponible:', e); }
}

// ── Pesos ─────────────────────────────────────────────────────────────────────
const PESOS_INFO = [
  { key:'S', label:'S — Seguridad y Gravedad',       desc:'Riesgo directo para personas' },
  { key:'D', label:'D — Frecuencia de Denuncias',    desc:'Volumen de reportes (log)' },
  { key:'M', label:'M — Impacto en Movilidad',       desc:'Afectación a circulación y servicios' },
  { key:'A', label:'A — Antigüedad del Incidente',   desc:'Días sin atender' },
  { key:'R', label:'R — Riesgo de Lluvia',           desc:'Peligrosidad hidrometeorológica' },
];

function renderPesos() {
  document.getElementById('pesos-grid').innerHTML = PESOS_INFO.map(p => `
    <div class="peso-item">
      <label>${p.label}</label>
      <div style="font-size:11px;color:#94a3b8;margin-bottom:8px;">${p.desc}</div>
      <div class="peso-val" id="val-${p.key}">${formatPeso(pesosActuales[p.key])}</div>
      <input type="range" min="0" max="100" step="5" value="${Math.round(pesosActuales[p.key]*100)}"
        oninput="actualizarPeso('${p.key}', this.value)" />
    </div>`).join('');
  actualizarSuma();
}

function actualizarPeso(key, val) {
  pesosActuales[key] = val / 100;
  document.getElementById(`val-${key}`).textContent = formatPeso(pesosActuales[key]);
  actualizarSuma();
}

function actualizarSuma() {
  const suma = Object.values(pesosActuales).reduce((a,b)=>a+b,0);
  const el = document.getElementById('suma-pesos');
  el.textContent = `Suma: ${suma.toFixed(2)}`;
  el.style.color = Math.abs(suma-1.0) < 0.01 ? '#16a34a' : '#dc2626';
}

function resetPesos() {
  pesosActuales = { S:0.30, D:0.25, M:0.20, A:0.15, R:0.10 };
  renderPesos();
}

async function recalcularPesos() {
  const suma = Object.values(pesosActuales).reduce((a,b)=>a+b,0);
  if (Math.abs(suma-1.0) > 0.01) { alert(`Los pesos deben sumar 1.00. Suma actual: ${suma.toFixed(2)}`); return; }
  try {
    const r = await fetch(API + '/api/recalcular', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ peso_S:pesosActuales.S, peso_D:pesosActuales.D,
        peso_M:pesosActuales.M, peso_A:pesosActuales.A, peso_R:pesosActuales.R }),
    });
    const data = await r.json();
    if (r.ok) { alert(`✅ ${data.mensaje}`); cargarRanking(); }
    else alert(`Error: ${data.detail}`);
  } catch(e) { alert('Error: ' + e.message); }
}

// ── Planeación ────────────────────────────────────────────────────────────────
const COSTOS_REF = {
  bache:20000, bacheo:20000, grieta:9000, pavimento_deteriorado:28000, hundimiento:45000,
  coladera_obstruida:5500, drenaje_obstruido:19000, inundacion_vialidad:38000,
  encharcamiento:9000, vialidad_bloqueada:22000, choque_vial:5000, atropello:5000,
};

async function actualizarPlanes() {
  const presupuesto = parseInt(document.getElementById('presupuesto-slider').value);
  document.getElementById('presupuesto-val').textContent = `$${presupuesto.toLocaleString('es-MX')} MXN`;
  if (!incidentesCache.length) {
    try { incidentesCache = await fetchJSON('/api/incidentes'); } catch(e) { return; }
  }
  const ordenados = [...incidentesCache].sort((a,b) =>
    (a.es_emergencia&&!b.es_emergencia) ? -1 : (!a.es_emergencia&&b.es_emergencia) ? 1 :
    (b.puntaje_total||0)-(a.puntaje_total||0));

  let gastoA=0; const planA=[];
  for (const inc of ordenados) {
    const costo = COSTOS_REF[(inc.tipo||'').toLowerCase()]||22000;
    if (inc.es_emergencia || gastoA+costo<=presupuesto) { planA.push({...inc,costo}); gastoA+=costo; }
    if (!inc.es_emergencia && gastoA>=presupuesto) break;
  }

  const emergencias = ordenados.filter(i=>i.es_emergencia);
  const normales = [...ordenados.filter(i=>!i.es_emergencia)]
    .sort((a,b)=>(COSTOS_REF[(a.tipo||'').toLowerCase()]||22000)-(COSTOS_REF[(b.tipo||'').toLowerCase()]||22000));
  let gastoB=0; const planB=[...emergencias];
  emergencias.forEach(e=>{gastoB+=COSTOS_REF[(e.tipo||'').toLowerCase()]||22000;});
  for (const inc of normales) {
    const costo = COSTOS_REF[(inc.tipo||'').toLowerCase()]||22000;
    if (gastoB+costo<=presupuesto) { planB.push({...inc,costo}); gastoB+=costo; }
  }

  const renderPlan = (lista, gasto) => `
    <div style="font-size:13px;margin-bottom:10px;font-weight:600;">
      ${lista.length} intervenciones · $${gasto.toLocaleString('es-MX')} MXN est.
    </div>
    ${lista.slice(0,8).map(i=>`
      <div style="font-size:12px;padding:6px 0;border-bottom:1px solid #f1f5f9;display:flex;justify-content:space-between;gap:8px;">
        <span style="color:#374151;">${i.calle||'Sin calle'} <span style="color:#94a3b8">(${i.alcaldia||'?'})</span></span>
        <span style="color:#2563eb;font-weight:600;white-space:nowrap;">$${(i.costo||0).toLocaleString()}</span>
      </div>`).join('')}
    ${lista.length>8?`<div style="font-size:12px;color:#94a3b8;margin-top:6px;">… y ${lista.length-8} más</div>`:''}
    <div style="font-size:11px;color:#94a3b8;margin-top:10px;">⚠️ Costos ficticios — requieren levantamiento técnico.</div>`;

  document.getElementById('plan-a-content').innerHTML = renderPlan(planA, gastoA);
  document.getElementById('plan-b-content').innerHTML = renderPlan(planB, gastoB);
}

// ── Chat ──────────────────────────────────────────────────────────────────────
const PREGUNTAS_SUGERIDAS = [
  '¿Cuáles son las 10 vialidades más urgentes?',
  '¿Hay emergencias activas?',
  '¿Qué coladeras deben inspeccionarse antes de las lluvias?',
  '¿Qué intervenciones se pueden hacer con $200,000 pesos?',
  '¿Qué autoridad es responsable?',
  '¿Cuántos reportes hay en total?',
];

function cargarSugerencias() {
  document.getElementById('sugerencias').innerHTML = PREGUNTAS_SUGERIDAS.map(p =>
    `<span class="sugerencia" onclick="preguntarChat(this.dataset.p)" data-p="${p}">💬 ${p}</span>`
  ).join('');
}

function preguntarChat(texto) {
  document.getElementById('chat-input').value = texto;
  enviarMensaje();
}

async function enviarMensaje() {
  const input = document.getElementById('chat-input');
  const texto = input.value.trim();
  if (!texto) return;
  input.value = '';
  const msgs = document.getElementById('chat-messages');
  msgs.innerHTML += `<div class="msg msg-user">${texto}</div>`;
  const spinner = document.createElement('div');
  spinner.className = 'msg msg-bot';
  spinner.innerHTML = '<span class="spinner"></span>';
  msgs.appendChild(spinner);
  msgs.scrollTop = msgs.scrollHeight;
  try {
    const r = await fetch(API+'/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({pregunta:texto}),
    });
    const data = await r.json();
    spinner.remove();
    msgs.innerHTML += `
      <div class="msg msg-bot">${(data.respuesta||'').replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\n/g,'<br>')}</div>
      <div class="msg-meta">📂 ${data.fuente||''} · Confianza: ${data.confianza||'n/a'} · ${data.fecha_corte||''}</div>`;
  } catch(e) {
    spinner.remove();
    msgs.innerHTML += `<div class="msg msg-bot">❌ Error: ${e.message}</div>`;
  }
  msgs.scrollTop = msgs.scrollHeight;
}

// ── Fuentes ───────────────────────────────────────────────────────────────────
async function cargarFuentes() {
  try {
    const fuentes = await fetchJSON('/api/fuentes');
    document.getElementById('fuentes-grid').innerHTML = fuentes.map(f => `
      <div class="fuente-card">
        <h4><span class="dot ${f.disponible?'dot-green':'dot-red'}"></span>${f.nombre}</h4>
        <p>Cobertura: ${f.fecha_cobertura||'No especificada'}</p>
        <p>Registros: ${f.registros!=null?f.registros.toLocaleString():'No disponible'}</p>
        <p>Licencia: ${f.licencia||'No especificada'}</p>
        ${f.url && f.url!=='local'
          ? `<p style="margin-top:6px;">🔗 <a href="${f.url}" target="_blank" rel="noopener" style="word-break:break-all;">${f.url}</a></p>`
          : '<span style="color:#94a3b8;font-size:12px;">📁 Datos locales</span>'}
        ${f.notas?`<p style="margin-top:8px;padding:6px 8px;background:#fffbeb;border-radius:4px;font-size:11px;">${f.notas}</p>`:''}
      </div>`).join('');

    const norm = await fetchJSON('/api/normativa');
    document.getElementById('normativa-content').innerHTML = `
      <div class="alert alert-warn">${norm.advertencia}</div>
      <div style="font-size:12px;margin-bottom:12px;">Fuente primaria: <a href="${norm.fuente_primaria}" target="_blank">${norm.fuente_primaria}</a></div>
      ${norm.normas.map(n=>`
        <div style="background:var(--blanco);border:1px solid var(--gris-borde);border-radius:8px;padding:14px;margin-bottom:10px;">
          <div style="font-weight:600;font-size:14px;">${n.nombre}</div>
          <div style="font-size:12px;color:#64748b;margin:4px 0;">${n.disposicion}</div>
          <div style="display:flex;gap:12px;font-size:12px;margin-top:6px;flex-wrap:wrap;">
            <span>📌 ${n.aplicabilidad}</span>
            <span style="color:#94a3b8">${n.tipo}</span>
          </div>
          <a href="${n.url}" target="_blank" style="font-size:12px;">🔗 Fuente</a>
        </div>`).join('')}
      <div class="alert alert-info" style="margin-top:12px;">${norm.nota_sistema}</div>`;
  } catch(e) {
    document.getElementById('fuentes-grid').innerHTML = `<div class="alert alert-warn">Error: ${e.message}</div>`;
  }
}

// ── Carga CSV ─────────────────────────────────────────────────────────────────
async function subirCSV(event) {
  const file = event.target.files[0];
  if (!file) return;
  const form = new FormData();
  form.append('file', file);
  document.getElementById('upload-result').innerHTML = '<div class="alert alert-info"><span class="spinner"></span> Cargando...</div>';
  try {
    const r = await fetch(API+'/api/upload-csv', {method:'POST', body:form});
    const data = await r.json();
    document.getElementById('upload-result').innerHTML = r.ok
      ? `<div class="alert alert-info">✅ ${data.mensaje} Incidentes: ${data.incidentes_generados}${data.errores?.length?`<br>⚠️ Errores: ${data.errores.length}`:''}</div>`
      : `<div class="alert alert-warn">❌ ${data.detail}</div>`;
    if (r.ok) { await cargarResumen(); incidentesCache = await fetchJSON('/api/incidentes'); }
  } catch(e) {
    document.getElementById('upload-result').innerHTML = `<div class="alert alert-warn">❌ ${e.message}</div>`;
  }
}

// ── Recarga global ────────────────────────────────────────────────────────────
async function recargarDatos() {
  await cargarResumen();
  incidentesCache = await fetchJSON('/api/incidentes').catch(()=>[]);
  if (mapaLeaflet) cargarCapaMapa();
}

// ── Init ──────────────────────────────────────────────────────────────────────
(async () => {
  await cargarResumen();
  renderPesos();
  cargarAlcaldiasFiltros();
  cargarSugerencias();
  incidentesCache = await fetchJSON('/api/incidentes').catch(()=>[]);
})();
