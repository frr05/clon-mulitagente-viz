// Tablero interactivo de las Bases de Licitación. Datos: tablero_datos.js (scripts/05_tablero.py).
// Primero la licitación (de qué tratan sus Bases, cómo se citan, cuánto se parecen a las otras); los cambios son una
// forma de ver qué le pasa a la licitación cuando se modifica (qué artículos cambian, cuándo, si cambian igual en las cinco).
// Un solo nivel de agregación: el artículo x.y.z con sus sub-artículos adentro.
// Dibuja con plotagents (plotagents.js) y agrega lo propio: filtros cruzados, buscador, ficha, resumen de la
// concesión, antes y después de las modificaciones (antes_despues.js), efecto de un cambio y un detalle bajo cada gráfico.
// Siempre hay una concesión elegida; la fase y el tipo de cambio son filtros que se prenden y apagan (sin un botón «todo»).
// Un solo estado S: cada control, gráfico o clic lo cambia y todo() vuelve a pintar la página entera.
(() => {
  "use strict";
  const T = window.TAB, A = T.arts, C = T.conc, N = A.c.length;
  const PA = window.plotagents;
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (x) => Math.round(x).toLocaleString("es-CL");
  const pct = (x) => `${Math.round(x * 100)} %`;
  const may = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);
  const sinTilde = (s) => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const corto = (t, n = 38) => (t.length <= n ? t : t.slice(0, n - 1).trimEnd() + "…");
  C.forEach((c, ci) => (c.n = A.c.filter((x) => x === ci).length));
  const COLORES = Object.fromEntries(C.map((c) => [c.nombre, c.color]));
  const PORNOMBRE = Object.fromEntries(C.map((c, ci) => [c.nombre, ci]));
  const TIPO = {
    reemplaza_articulo: "reemplaza el artículo", reemplaza_parrafo: "reemplaza un párrafo", reemplaza_texto: "reemplaza texto",
    agrega: "agrega", agrega_articulo: "agrega el artículo", agrega_parrafo: "agrega un párrafo", agrega_texto: "agrega texto",
    elimina: "elimina", elimina_texto: "elimina texto",
  };
  const FAMILIA = (tipo) => (tipo.startsWith("reemplaza") ? "reemplaza" : tipo.startsWith("agrega") ? "agrega" : "elimina");
  // sin opción «todo»: un segundo clic en el filtro prendido lo apaga ("todas" / "todos" = sin filtro)
  const FASES = [["lic", "Licitación"], ["con", "Contrato"]];
  const TIPOS = [["reemplaza", "Reemplaza"], ["agrega", "Agrega"], ["elimina", "Elimina"]];
  const LINEAS = [["citas", "Todas las citas"], ["no", "Ninguna"]];
  const LIC = "Durante la licitación", CON = "Durante el contrato";
  // qué cuenta el color de los nodos del mapa
  const MODOS_COLOR = [["comunidad", "Comunidad"], ["tipo", "Tipo"], ["anio", "Año"], ["fase", "Fase"], ["parte", "Parte"]];
  // el mapa muestra las Bases (tamaño: citas que recibe), sus cambios (tamaño: cambios; destaca los enlaces que crean o
  // destruyen) o todo junto (las Bases a color, los artículos que cambiaron con un aro y los enlaces creados y destruidos)
  const VISTAS = [["bases", "Las Bases"], ["cambios", "Sus cambios"], ["todo", "Todo"]];
  const COLOR_BASES = new Set(["comunidad", "parte"]);           // los colores que tienen sentido sin cambios
  // comunidades generales (las mismas en las cinco): Louvain sobre la similitud de contenido, en scripts/05_tablero.py
  const COM = window.TAB.comunidades || [];
  const COLOR_COM = ["#3b47b5", "#e0a030", "#2aa876", "#d0385e", "#8a55d3", "#1f9bd1", "#e07a5f", "#6b8e23", "#c2459b", "#7a7f99"];
  const colorCom = (i) => COLOR_COM[i % COLOR_COM.length];
  const PALETA = {
    tipo: { reemplaza: ["Reemplaza", "#3b47b5"], agrega: ["Agrega", "#2aa876"], elimina: ["Elimina", "#d0385e"] },
    fase: { lic: ["En la licitación", "#3b47b5"], con: ["En el contrato", "#e0a030"] },
    parte: { Administrativas: ["Administrativas", "#3b47b5"], "Técnicas": ["Técnicas", "#e0a030"], "Económicas": ["Económicas", "#d0385e"] },
  };
  const RAMPA = ["#f2c14e", "#e07a5f", "#8a55d3", "#2b2d7a"];      // de lo más antiguo a lo más reciente
  const rampa = (t) => {
    t = Math.min(1, Math.max(0, t)) * (RAMPA.length - 1);
    const i = Math.min(RAMPA.length - 2, Math.floor(t)), f = t - i;
    const a = RAMPA[i], b = RAMPA[i + 1];
    return "#" + [1, 3, 5].map((k) => Math.round(parseInt(a.slice(k, k + 2), 16) * (1 - f) + parseInt(b.slice(k, k + 2), 16) * f).toString(16).padStart(2, "0")).join("");
  };
  const AZUL = "#3b47b5", GRIS = "#c8cad4";
  // antes y después: cada artículo x.y.z en las Bases tal como se publicaron y en su versión vigente
  const AD = window.ANTES_DESPUES?.concesiones || null;
  const adDe = Array.from({ length: N }, () => []);       // g → [[id, datos], …] del artículo y sus sub-artículos
  const posNum = new Map();
  for (let g = 0; g < N; g++) {
    posNum.set(`${A.c[g]}|${A.num[g]}`, g);
    for (const s of A.sub[g]) posNum.set(`${A.c[g]}|${s}`, g);
  }
  // «BL:1.7.13.2» de la concesión ci → el grupo x.y.z que lo contiene (1.7.13)
  const gDeId = (ci, id) => {
    let num = String(id).replace(/^[^:]*:/, ""), g = posNum.get(`${ci}|${num}`);
    while (g == null && num.includes(".")) { num = num.slice(0, num.lastIndexOf(".")); g = posNum.get(`${ci}|${num}`); }
    return g;
  };
  if (AD) {
    C.forEach((c, ci) => {
      for (const [id, a] of Object.entries(AD[c.cod]?.arts || {})) {
        const g = gDeId(ci, id);
        if (g != null) adDe[g].push([id, a]);
      }
    });
    adDe.forEach((l) => l.sort((x, y) => x[0].localeCompare(y[0], "es", { numeric: true })));
  }
  // enlaces que crean o destruyen los cambios, entre artículos x.y.z de una misma concesión:
  //  · cita nueva: una cita que aparece en un acto posterior (el árbol no registra citas que se pierdan);
  //  · contenido: dos artículos pasan a estar (o dejan de estar) entre los 8 más parecidos del otro. Para no contar los que
  //    solo cambian de puesto en el borde, el vecino que sale tenía que estar al menos DELTA sobre el último vecino nuevo,
  //    y el que entra, DELTA sobre el último vecino antiguo. Si un par gana y pierde a la vez (por sub-artículos distintos), se netea.
  const DELTA = 0.02;
  const ENLACES = C.map(() => []);
  const enlacesDe = Array.from({ length: N }, () => []);
  if (AD) C.forEach((c, ci) => {
    const neto = new Map(), phi = new Map(), citas = new Map();
    for (const [id, a] of Object.entries(AD[c.cod]?.arts || {})) {
      const ga = gDeId(ci, id);
      if (ga == null) continue;
      for (const [b, acto] of a.cs || []) {
        const gb = gDeId(ci, b);
        if (gb == null || gb === ga) continue;
        const k = `${ga}|${gb}`;
        if (!citas.has(k)) citas.set(k, { a: ga, b: gb, tipo: "cita", signo: 1, acto });
      }
      const m0 = new Map(a.v0 || []), m1 = new Map(a.v1 || []);
      if (!m0.size || !m1.size) continue;
      const min0 = Math.min(...m0.values()), min1 = Math.min(...m1.values());
      const suma = (b, sg, p) => {
        const gb = gDeId(ci, b);
        if (gb == null || gb === ga) return;
        const k = ga < gb ? `${ga}|${gb}` : `${gb}|${ga}`;
        neto.set(k, (neto.get(k) || 0) + sg);
        phi.set(`${k}|${sg}`, Math.max(phi.get(`${k}|${sg}`) || 0, p));
      };
      for (const [b, p] of m0) if (!m1.has(b) && p >= min1 + DELTA) suma(b, -1, p);
      for (const [b, p] of m1) if (!m0.has(b) && p >= min0 + DELTA) suma(b, +1, p);
    }
    const l = [...citas.values()];
    for (const [k, v] of neto) {
      if (!v) continue;
      const [a, b] = k.split("|").map(Number), sg = Math.sign(v);
      l.push({ a, b, tipo: "contenido", signo: sg, phi: phi.get(`${k}|${sg}`) });
    }
    ENLACES[ci] = l;
    for (const e of l) { enlacesDe[e.a].push(e); enlacesDe[e.b].push(e); }
  });

  // el artículo entero antes → después: palabras, incisos y φ (de su texto principal, o el menor de sus sub-artículos)
  const adSuma = (g) => {
    const l = adDe[g].filter(([, a]) => a.d.length || a.nuevo);
    if (!l.length) return null;
    const phis = l.map(([, a]) => a.phi).filter((x) => x != null);
    const w0 = l.reduce((s, [, a]) => s + (a.nuevo ? 0 : a.w[0]), 0), w1 = l.reduce((s, [, a]) => s + a.w[1], 0);
    return {
      w0, w1, mas: l.reduce((s, [, a]) => s + a.inc[0], 0), menos: l.reduce((s, [, a]) => s + a.inc[1], 0),
      phi: phis.length ? Math.min(...phis) : null, nuevo: !!A.nuevo?.[g], partes: l,
      // «a verificar» solo si el artículo entero queda más corto y algún sub-artículo puede haber perdido texto nuevo
      dudoso: w1 < w0 && l.some(([, a]) => a.dudoso),
    };
  };
  // citas en las Bases originales: las de hoy menos las que nacen en un acto posterior (05_tablero.py: «nueva»)
  const NUEVA = A.nueva || A.sale.map(() => []);
  const entra0 = (g) => A.entra[g].filter((a) => !NUEVA[a].includes(g));
  const sale0 = (g) => A.sale[g].filter((b) => !NUEVA[g].includes(b));
  const PR0 = A.pr0 || A.pr;
  const gsDe = (ci) => { const l = []; for (let g = 0; g < N; g++) if (A.c[g] === ci) l.push(g); return l; };
  // la concesión entera antes → después: los artículos que cambian su texto y sus palabras
  const antesDespues = (ci) => {
    if (!AD) return null;
    const l = gsDe(ci).map((g) => [g, adSuma(g)]).filter(([, x]) => x);
    if (!l.length) return null;
    const viejos = l.filter(([, x]) => !x.nuevo);
    return {
      n: l.length, l, w0: viejos.reduce((s, [, x]) => s + x.w0, 0), w1: viejos.reduce((s, [, x]) => s + x.w1, 0),
      nuevos: l.length - viejos.length, cortos: viejos.filter(([, x]) => x.w1 < x.w0 && !x.dudoso).length,
      largos: viejos.filter(([, x]) => x.w1 > x.w0).length, iguales: viejos.filter(([, x]) => x.w1 === x.w0).length, dudosos: viejos.filter(([, x]) => x.dudoso).length,
    };
  };
  // puesto de cada artículo en el ranking de citas (PageRank) de su concesión, hoy y en las Bases originales
  const puestos = (ci) => {
    const gs = gsDe(ci);
    const hoy = gs.slice().sort((a, b) => A.pr[b] - A.pr[a]);
    const antes = gs.filter((g) => !A.nuevo?.[g]).sort((a, b) => PR0[b] - PR0[a]);
    return { hoy, p1: new Map(hoy.map((g, i) => [g, i + 1])), p0: new Map(antes.map((g, i) => [g, i + 1])) };
  };

  // ---------- derivados
  // equivalentes de un artículo = los otros artículos de su base común, con su parecido φ
  const eqs = (g) => T.bases.m[A.base[g]].filter((b) => b !== g).map((b) => [b, (A.ct[g].find(([x]) => x === b) || [b, null])[1]]);
  const anioActo = (ci, k) => +(String(C[ci].actos[k]?.[1] || "").slice(0, 4)) || null;
  // años desde las Bases: el año 0 son los 12 meses desde su publicación, el 1 los 12 siguientes…
  const fecha = (x) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(x || "")); return m ? Date.UTC(+m[1], +m[2] - 1, +m[3]) : null; };
  const ANIO_MS = 365.25 * 864e5;
  const relActo = (ci, k) => { const a = fecha(C[ci].actos[k]?.[1]), b = fecha(C[ci].actos[0]?.[1]); return a == null || b == null ? null : Math.max(0, Math.floor((a - b) / ANIO_MS)); };
  const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const periodo = (ci, k) => {
    const b = fecha(C[ci].actos[0]?.[1]);
    if (b == null) return "";
    const d0 = new Date(b + k * ANIO_MS), d1 = new Date(b + (k + 1) * ANIO_MS - 864e5);
    const f = (d) => `${MESES[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
    return `${f(d0)}–${f(d1)}`;
  };
  // hasta qué año llega cada concesión: el último acto con fecha de las cinco marca el presente de los datos
  const FIN = Math.max(...C.flatMap((c) => c.actos.map((a) => fecha(a[1]) ?? 0)));
  const EDAD = C.map((c) => { const b = fecha(c.actos[0]?.[1]); return b == null ? 0 : Math.floor((FIN - b) / ANIO_MS); });
  // fase: antes del decreto de adjudicación, licitación; desde él, contrato. La publicación en el Diario Oficial del
  // mismo día que el decreto viene en la lista antes que él, pero es su publicación: va al contrato.
  const faseDe = (ci, k) => {
    if (k >= C[ci].adj) return "con";
    const a = C[ci].actos[k], d = C[ci].actos[C[ci].adj];
    return d && a && a[1] === d[1] && /publicaci[oó]n diario oficial/i.test(a[0]) ? "con" : "lic";
  };
  const nombreFase = (f) => (f === "lic" ? "Licitación" : "Contrato");
  const cambios = [];                       // todos los cambios, con su año, fase y familia
  const deArt = Array.from({ length: N }, () => []);
  const huella = new Map();                 // "ci|acto" → artículos que cambió ese acto
  for (let g = 0; g < N; g++) {
    const ci = A.c[g];
    A.h[g].forEach((h, i) => {
      // un cambio = un acto que modifica el artículo; h[1] son sus ediciones [tipo, inciso, texto]
      const cb = { g, i, ci, acto: h[0], ed: h[1], fams: [...new Set(h[1].map((e) => FAMILIA(e[0])))], anio: anioActo(ci, h[0]) ?? 9999, rel: relActo(ci, h[0]), fase: faseDe(ci, h[0]) };
      cambios.push(cb);
      deArt[g].push(cb);
      const k = `${ci}|${cb.acto}`;
      if (!huella.has(k)) huella.set(k, new Set());
      huella.get(k).add(g);
    });
  }
  const rangoConc = C.map((_, ci) => {
    const a = cambios.filter((c) => c.ci === ci && c.anio < 9999).map((c) => c.anio);
    return [Math.min(anioActo(ci, 0) || Infinity, ...a), Math.max(...a)];
  });

  // ---------- la licitación: medidas de sus Bases (no dependen de los cambios)
  const citasRec = (g) => A.ci?.[g] ?? A.entra[g].length;          // citas que recibe (con su peso)
  const PCTS = Array.from({ length: 21 }, (_, i) => i * 5);
  // concentración de las citas: curva de Lorenz (del más citado al menos), parte del 10 % más citado y Gini
  const concentracion = (ci) => {
    const v = gsDe(ci).map(citasRec).sort((a, b) => b - a), n = v.length, tot = v.reduce((s, x) => s + x, 0) || 1;
    const acum = []; v.reduce((s, x, i) => (acum[i] = s + x), 0);
    const hasta = (p) => { const k = Math.round((p / 100) * n); return k ? acum[k - 1] / tot : 0; };
    const asc = v.slice().reverse();
    const gini = (2 * asc.reduce((s, x, i) => s + (i + 1) * x, 0)) / (n * tot) - (n + 1) / n;
    return { curva: PCTS.map((p) => [p, hasta(p)]), top10: hasta(10), gini, tot, sinCitas: v.filter((x) => !x).length, n };
  };
  // plantilla común: en cuántas de las otras concesiones tiene equivalente cada artículo
  const EN_OTRAS = ["En las otras cuatro", "En tres", "En dos", "En una", "Propio"];
  const enOtras = (g) => EN_OTRAS[Math.max(0, Math.min(4, C.length - 1 - eqs(g).length))];
  const plantilla = (ci) => {
    const n = Object.fromEntries(EN_OTRAS.map((k) => [k, []]));
    for (const g of gsDe(ci)) n[enOtras(g)].push(g);
    return n;
  };
  // los artículos de cada comunidad en una concesión
  const porComunidad = (ci) => { const m = COM.map(() => []); for (const g of gsDe(ci)) m[A.cm[g]].push(g); return m; };
  // cuartos por citas en las Bases originales (PageRank sin las citas nuevas): del más citado al menos
  const CUARTOS = ["El 25 % más citado", "2.º cuarto", "3.º cuarto", "El 25 % menos citado"];
  const cuartos = (ci) => {
    const gs = gsDe(ci).filter((g) => !A.nuevo?.[g]).sort((a, b) => PR0[b] - PR0[a]);
    return CUARTOS.map((_, q) => gs.slice(Math.round((q * gs.length) / 4), Math.round(((q + 1) * gs.length) / 4)));
  };
  const parte = (l, f) => (l.length ? l.filter(f).length / l.length : null);

  // ---------- estado (también en la URL: se puede compartir una vista)
  // siempre una concesión elegida (sin «las cinco»); el año no filtra: verAnio solo abre los actos de un año en el detalle
  const S = { conc: 0, fase: "todas", tipo: "todos", sel: null, cambio: null, citas: "red", lineas: "citas", color: "comunidad", com: null, verAnio: null, vista: "bases" };
  const visible = (g) => A.c[g] === S.conc;
  const conCambios = () => S.vista === "cambios";
  const conEnlaces = () => S.vista !== "bases";
  // lo que de verdad usa el mapa: en la vista de las Bases no hay color por cambios ni líneas «entre cambiados»
  const colorEf = () => (conCambios() || COLOR_BASES.has(S.color) ? S.color : "comunidad");
  const lineasEf = () => S.lineas;
  const rango = () => rangoConc[S.conc];
  // ¿cuenta este cambio con los filtros? (la concesión la decide visible())
  const pasa = (c, { fase = true, tipo = true } = {}) =>
    (!fase || S.fase === "todas" || c.fase === S.fase) && (!tipo || S.tipo === "todos" || c.fams.includes(S.tipo));
  const cuenta = (g, o) => deArt[g].reduce((s, c) => s + (pasa(c, o) ? 1 : 0), 0);
  const pasaActo = (ci, k) => S.fase === "todas" || faseDe(ci, k) === S.fase;
  const citasActos = (g) => A.ca[g].reduce((s, [k, n]) => s + (pasaActo(A.c[g], k) ? n : 0), 0);
  const filtrado = () => cambios.filter((c) => visible(c.g) && pasa(c));
  const alcance = () => C[S.conc].nombre;
  const palabra = () => ({ todos: "cambios", reemplaza: "reemplazos", agrega: "agregados", elimina: "eliminaciones" }[S.tipo]);
  const queCambios = () => palabra() + (S.fase === "lic" ? " durante la licitación" : S.fase === "con" ? " durante el contrato" : "");

  function leerURL() {
    const q = new URLSearchParams(location.hash.slice(1));
    const ci = C.findIndex((c) => c.cod === q.get("c"));
    S.conc = ci >= 0 ? ci : 0;
    S.fase = FASES.some(([k]) => k === q.get("f")) ? q.get("f") : "todas";
    S.tipo = TIPOS.some(([k]) => k === q.get("t")) ? q.get("t") : "todos";
    S.citas = q.get("m") === "actos" ? "actos" : "red";
    S.lineas = LINEAS.some(([k]) => k === q.get("l")) ? q.get("l") : "citas";
    S.color = MODOS_COLOR.some(([k]) => k === q.get("co")) ? q.get("co") : "comunidad";
    S.vista = VISTAS.some(([k]) => k === q.get("v")) ? q.get("v") : "bases";
    S.com = null;
    S.sel = null; S.cambio = null;
    const art = q.get("art");
    if (art) {
      const [cod, num] = art.split("/");
      const g = A.num.findIndex((n, x) => n === num && C[A.c[x]].cod === cod);
      if (g >= 0) S.sel = g;
    }
  }
  function escribirURL() {
    const q = new URLSearchParams();
    q.set("c", C[S.conc].cod);
    if (S.fase !== "todas") q.set("f", S.fase);
    if (S.tipo !== "todos") q.set("t", S.tipo);
    if (S.citas !== "red") q.set("m", S.citas);
    if (S.lineas !== "citas") q.set("l", S.lineas);
    if (S.color !== "comunidad") q.set("co", S.color);
    if (S.vista !== "bases") q.set("v", S.vista);
    if (S.sel != null) q.set("art", `${C[A.c[S.sel]].cod}/${A.num[S.sel]}`);
    const h = q.toString();
    history.replaceState(null, "", h ? `#${h}` : location.pathname + location.search);
  }

  // ---------- acciones (todo lo que filtra pasa por aquí)
  function ponerConc(ci) {
    if (ci === S.conc || !(ci >= 0)) return;          // siempre hay una concesión: un clic en la elegida no la quita
    S.conc = ci; S.verAnio = null;
    if (S.sel != null && !visible(S.sel)) {
      const eq = eqs(S.sel).find(([b]) => visible(b));   // saltamos a su equivalente en la nueva concesión
      S.sel = eq ? eq[0] : null;
      S.cambio = null;
    }
    todo();
  }
  const ponerFase = (f) => { S.fase = S.fase === f ? "todas" : f; todo(); };
  function seleccionar(g, cambio = null) {
    if (g != null && !visible(g)) { S.conc = A.c[g]; S.verAnio = null; }   // un equivalente lleva a su licitación
    S.sel = g; S.cambio = cambio;
    todo();
  }
  const irAlMapa = () => document.querySelector(".principal").scrollIntoView({ behavior: "smooth", block: "start" });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape" || document.activeElement?.id === "buscar") return;
    if (S.sel != null) seleccionar(null);
    else if (S.com != null) { S.com = null; todo(); }
  });

  // ---------- controles
  $("#n-art").textContent = `${fmt(N)}`;
  $("#generado").textContent = `datos generados ${T.generado}`;
  const concs = $("#concs");
  concs.innerHTML = C.map((c, ci) => `<button type="button" data-c="${ci}" title="${esc(c.largo)}"><span class="pt" style="background:${c.color}"></span>${esc(c.nombre)}</button>`).join("");
  concs.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-c]");
    if (b) ponerConc(+b.dataset.c);
  });
  const segmentos = (el, op, act) => {
    el.innerHTML = op.map(([k, t]) => `<button type="button" data-k="${k}">${t}</button>`).join("");
    el.addEventListener("click", (e) => { const b = e.target.closest("button[data-k]"); if (b) act(b.dataset.k); });
  };
  // sin botones de fase ni de tipo arriba: la fase se elige con un clic en el gráfico de licitación y contrato, y queda
  // como ficha con × en la barra
  segmentos($("#modo-citas"), [["red", "Entre artículos"], ["actos", "Desde actos"]], (k) => { S.citas = k; todo(); });
  segmentos($("#conexiones"), LINEAS, (k) => { S.lineas = k; todo(); });
  segmentos($("#mapa-color"), MODOS_COLOR, (k) => { S.color = k; S.com = null; todo(); });
  segmentos($("#mapa-vista"), VISTAS, (k) => { S.vista = k; todo(); });
  // un clic en una comunidad de la leyenda (o en su nombre sobre el mapa) la resalta; otro clic la suelta
  function ponerCom(i, fijar = false) {
    S.com = !fijar && S.com === i && S.sel == null ? null : i;
    S.sel = null; S.cambio = null;                       // la comunidad se ve en el mapa sin artículo abierto
    if (colorEf() !== "comunidad") S.color = "comunidad";
    todo();
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-com]");
    if (b) ponerCom(+b.dataset.com);
  });

  // filtros activos, cada uno con su ×
  $("#activos").addEventListener("click", (e) => {
    const b = e.target.closest("[data-quitar]");
    if (!b) return;
    const k = b.dataset.quitar;
    if (k === "todo") {
      Object.assign(S, { fase: "todas", tipo: "todos", sel: null, cambio: null, verAnio: null });
      return todo();
    }
    if (k === "fase") S.fase = "todas";
    if (k === "tipo") S.tipo = "todos";
    if (k === "anio") S.verAnio = null;
    if (k === "sel") { S.sel = null; S.cambio = null; }
    if (k === "cambio") S.cambio = null;
    todo();
  });
  function pintarActivos() {
    const f = [];
    if (S.fase !== "todas") f.push(["fase", `Fase: <b>${S.fase === "lic" ? "licitación" : "contrato"}</b>`]);
    if (S.tipo !== "todos") f.push(["tipo", `Tipo: <b>${esc(palabra())}</b>`]);
    if (S.verAnio != null) f.push(["anio", `Actos del <b>año ${S.verAnio}</b>`]);
    if (S.sel != null) f.push(["sel", `Artículo: <b>${esc(C[A.c[S.sel]].cod)} ${esc(A.num[S.sel])}</b>`]);
    if (S.cambio != null) f.push(["cambio", `Cambio: <b>${esc(C[A.c[S.sel]].actos[A.h[S.sel][S.cambio][0]]?.[0] || "")}</b>`]);
    $("#activos").innerHTML = f.length
      ? f.map(([k, t]) => `<button type="button" class="f" data-quitar="${k}" title="Quitar este filtro">${t}<span class="x">×</span></button>`).join("") +
        (f.length > 1 ? `<button type="button" class="limpiar" data-quitar="todo">Quitar todos</button>` : "")
      : "";
  }

  // buscador (también encuentra sub-artículos: 1.7.13.2 lleva a 1.7.13)
  const caja = $("#buscar"), sug = $("#sugerencias");
  const indice = Array.from({ length: N }, (_, g) => sinTilde(`${A.num[g]} ${A.sub[g].join(" ")} ${A.t[g]} ${C[A.c[g]].cod} ${C[A.c[g]].nombre}`));
  let opciones = [], activa = -1;
  caja.addEventListener("input", () => {
    const q = sinTilde(caja.value.trim());
    if (q.length < 2) { sug.hidden = true; return; }
    const pal = q.split(/\s+/);
    opciones = [];
    for (let g = 0; g < N; g++) if (pal.every((p) => indice[g].includes(p))) opciones.push(g);
    const empieza = (g) => (A.num[g].startsWith(q) ? 1 : 0);
    opciones.sort((a, b) => (visible(b) - visible(a)) || (empieza(b) - empieza(a)) || (cuenta(b) - cuenta(a)) || A.pr[b] - A.pr[a]);
    opciones = opciones.slice(0, 12);
    activa = opciones.length ? 0 : -1;
    pintarSug();
  });
  function pintarSug() {
    sug.innerHTML = opciones.length
      ? opciones.map((g, i) => `<li role="option" data-g="${g}" aria-selected="${i === activa}"><span class="cod" style="background:${C[A.c[g]].color}">${esc(C[A.c[g]].cod)}</span><span>${esc(A.num[g])} ${esc(corto(A.t[g], 56))}</span><span class="quien" style="margin-left:auto">${cuenta(g)} ${palabra()}</span></li>`).join("")
      : `<li aria-disabled="true">Sin resultados</li>`;
    sug.hidden = false;
  }
  caja.addEventListener("keydown", (e) => {
    if (sug.hidden) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      activa = (activa + (e.key === "ArrowDown" ? 1 : -1) + opciones.length) % Math.max(1, opciones.length);
      pintarSug();
    } else if (e.key === "Enter" && activa >= 0) { e.preventDefault(); elegirSug(opciones[activa]); }
    else if (e.key === "Escape") sug.hidden = true;
  });
  sug.addEventListener("mousedown", (e) => { const li = e.target.closest("li[data-g]"); if (li) { e.preventDefault(); elegirSug(+li.dataset.g); } });
  caja.addEventListener("blur", () => setTimeout(() => (sug.hidden = true), 150));
  function elegirSug(g) { sug.hidden = true; caja.value = ""; seleccionar(g); irAlMapa(); }

  // ---------- mapa: una licitación a la vez, con sus cambios superpuestos sobre sus Bases
  // La base es cada artículo de esa licitación (gris, del tamaño de todos los cambios que llegó a tener). Encima, en el
  // mismo SVG, lo que cambió hasta el año elegido: color pleno en la licitación, tono claro en el contrato.
  const B = T.bases;
  const GRIS_BASE = "#dcdfe8", BASES = "Bases", ANCLA = "__ancla";
  const numsBase = (k) => B.m[k].map((g) => `${C[A.c[g]].cod} ${A.num[g]}`).join(" · ");
  const claro = (hex, t = 0.55) => "#" + [1, 3, 5].map((i) => Math.round(parseInt(hex.slice(i, i + 2), 16) * (1 - t) + 255 * t).toString(16).padStart(2, "0")).join("");
  const mapaConc = () => S.conc;
  // la caja del dibujo (div.mapa); la <section id="el-mapa"> que la contiene es el ancla de la barra de navegación (nav.js)
  const mapaEl = document.querySelector("div.mapa");
  const lienzo = document.createElement("div"), capa = document.createElement("div");
  capa.className = "rotulos";
  // lo propio de cada vista (enlaces, aro, selección) va en un recuadro dentro del mapa: la cabecera mide lo mismo en las tres
  const recuadro = document.createElement("div");
  recuadro.className = "recuadro";
  mapaEl.append(lienzo, capa, recuadro);
  let mapa = null, encima = new Map();
  function lineasMapa(mc, cnt) {
    const lineas = lineasEf();
    if (lineas === "no") return [];
    const e = [];
    for (let g = 0; g < N; g++) {
      if (A.c[g] !== mc) continue;
      for (const b of A.sale[g]) e.push({ from: g, to: b });
    }
    return e;
  }
  function relacionados() {
    const g = S.sel, aristas = [], luz = new Set([g]);
    for (const b of A.sale[g]) { aristas.push({ from: g, to: b }); luz.add(b); }
    for (const a of A.entra[g]) { aristas.push({ from: a, to: g }); luz.add(a); }
    if (S.cambio != null) for (const x of huella.get(`${A.c[g]}|${A.h[g][S.cambio][0]}`) || []) luz.add(x);
    return { aristas, luz: [...luz] };
  }
  // posiciones del mapa: las de la similitud de contenidos, estiradas al lienzo y separadas para que no se tapen
  const R_MIN = 4.5, R_MAX = 18, ALTO_MAPA = 680;
  const acomodos = new Map();
  // con grupo (la comunidad de cada nodo), cada comunidad ocupa su propia zona: un círculo de área según sus puntos,
  // cerca de donde caían sus artículos, y adentro conserva la forma que tenía
  function acomodar(nodos, grupo = null) {
    const W = Math.max(420, Math.round(mapaEl.clientWidth || 900) - 24), H = ALTO_MAPA - 40;
    const clave = `${nodos.map((n) => `${n.id}:${n.size}`).join(",")}|${W}|${grupo ? "g" : ""}`;
    if (!acomodos.has(clave)) {
      const top = Math.max(...nodos.map((n) => n.size), 1e-9);
      const r = nodos.map((n) => Math.max(R_MIN, R_MAX * Math.sqrt(n.size / top)));
      // la misma escala para las cinco (la extensión del espacio conjunto), no la de cada concesión
      const m = R_MAX + 4;
      const ox = nodos.map((nd) => nxGlobal(nd.x, W, m)), oy = nodos.map((nd) => nyGlobal(nd.y, H, m));
      const n = nodos.length;
      if (grupo) enZonas(ox, oy, r, grupo, W, H, m);
      const px = ox.slice(), py = oy.slice(), tiron = grupo ? 0.06 : 0.02;
      for (let it = 0; it < 160; it++) {
        let movio = false;
        for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
          let dx = px[j] - px[i], dy = py[j] - py[i];
          const d = Math.hypot(dx, dy) || 0.01, falta = r[i] + r[j] + 2 - d;
          if (falta <= 0) continue;
          movio = true;
          if (d === 0.01) { dx = Math.cos(i + j); dy = Math.sin(i + j); }
          const ux = dx / d, uy = dy / d, wi = r[j] / (r[i] + r[j]), wj = r[i] / (r[i] + r[j]);
          px[i] -= ux * falta * wi; py[i] -= uy * falta * wi;
          px[j] += ux * falta * wj; py[j] += uy * falta * wj;
        }
        for (let i = 0; i < n; i++) {                  // un tirón suave hacia su lugar, y dentro del lienzo
          px[i] += (ox[i] - px[i]) * tiron; py[i] += (oy[i] - py[i]) * tiron;
          px[i] = Math.min(W - r[i] - 2, Math.max(r[i] + 2, px[i]));
          py[i] = Math.min(H - r[i] - 2, Math.max(r[i] + 2, py[i]));
        }
        if (!movio && it > 20) break;
      }
      acomodos.set(clave, px.map((x, i) => [x / W, py[i] / H]));
      if (acomodos.size > 40) acomodos.delete(acomodos.keys().next().value);
    }
    acomodos.get(clave).forEach(([x, y], i) => { nodos[i].x = x; nodos[i].y = y; });
  }
  // Zonas comunes a las cinco concesiones: cada comunidad tiene su lugar fijo en el lienzo (el mismo en todas), así que al
  // cambiar de concesión lo que cambia en el mapa son los artículos y sus enlaces, no la disposición. El centro de cada zona
  // parte de la mediana de la comunidad en el espacio conjunto; su radio alcanza para la concesión que más artículos tiene en
  // ella. Adentro, cada artículo va según su posición en el espacio conjunto, con la misma escala en las cinco: los
  // equivalentes caen casi en el mismo punto.
  const tamNodo = (g) => 1 + (A.ci?.[g] ?? A.entra[g].length);
  const TOP_TAM = C.map((_, ci) => Math.max(...gsDe(ci).map(tamNodo), 1e-9));
  const radioNodo = (g) => Math.max(R_MIN, R_MAX * Math.sqrt(tamNodo(g) / TOP_TAM[A.c[g]]));
  const EXT = [Math.min(...A.x), Math.max(...A.x), Math.min(...A.y), Math.max(...A.y)];
  const nxGlobal = (x, W, m) => m + ((x - EXT[0]) / (EXT[1] - EXT[0] || 1)) * (W - 2 * m);
  const nyGlobal = (y, H, m) => m + ((y - EXT[2]) / (EXT[3] - EXT[2] || 1)) * (H - 2 * m);
  const zonasCache = new Map();
  function zonas(W, H, m) {
    if (zonasCache.has(W)) return zonasCache.get(W);
    const med = (v) => { v = v.slice().sort((a, b) => a - b); return v[Math.floor(v.length / 2)]; };
    const zs = [];
    COM.forEach((_, i) => {
      const gs = []; for (let g = 0; g < N; g++) if (A.cm[g] === i) gs.push(g);
      if (!gs.length) return;
      const xs = gs.map((g) => nxGlobal(A.x[g], W, m)), ys = gs.map((g) => nyGlobal(A.y[g], H, m));
      const mx = med(xs), my = med(ys);
      const R = Math.max(...C.map((_, ci) => Math.sqrt(gs.filter((g) => A.c[g] === ci).reduce((s, g) => s + (radioNodo(g) + 2) ** 2, 0) * 1.9)));
      const ds = xs.map((x, k) => Math.hypot(x - mx, ys[k] - my)).sort((a, b) => a - b);
      // escala interna: la distancia mediana a su centro llega a media zona (los muy alejados quedan en el borde)
      zs.push({ i, cx: mx, cy: my, mx, my, R, mediana: ds[Math.floor(ds.length / 2)] || 1 });
    });
    // entre todas ocupan cerca de la mitad del lienzo (se agrandan o achican por igual)
    const area = zs.reduce((s, z) => s + Math.PI * z.R ** 2, 0), k = Math.sqrt((0.55 * W * H) / area);
    zs.forEach((z) => (z.R *= k));
    // las zonas se separan entre sí y quedan dentro del lienzo
    for (let it = 0; it < 400; it++) {
      let movio = false;
      for (let a = 0; a < zs.length; a++) for (let b = a + 1; b < zs.length; b++) {
        const A1 = zs[a], B1 = zs[b];
        let dx = B1.cx - A1.cx, dy = B1.cy - A1.cy;
        const d = Math.hypot(dx, dy) || 0.01, falta = A1.R + B1.R + 16 - d;
        if (falta <= 0) continue;
        movio = true;
        if (d === 0.01) { dx = Math.cos(a + b); dy = Math.sin(a + b); }
        const ux = dx / d, uy = dy / d, wa = B1.R / (A1.R + B1.R), wb = A1.R / (A1.R + B1.R);
        A1.cx -= ux * falta * wa; A1.cy -= uy * falta * wa;
        B1.cx += ux * falta * wb; B1.cy += uy * falta * wb;
      }
      for (const z of zs) {
        z.cx += (W / 2 - z.cx) * 0.004; z.cy += (H / 2 - z.cy) * 0.004;     // un poco hacia el centro, para no dejar huecos
        z.cx = Math.min(W - Math.min(z.R, W / 2), Math.max(Math.min(z.R, W / 2), z.cx));
        z.cy = Math.min(H - Math.min(z.R, H / 2), Math.max(Math.min(z.R, H / 2), z.cy));
      }
      if (!movio && it > 30) break;
    }
    // y el conjunto de zonas se estira hasta los bordes del lienzo (los radios crecen con el eje que menos se estira)
    const bx0 = Math.min(...zs.map((z) => z.cx - z.R)), bx1 = Math.max(...zs.map((z) => z.cx + z.R));
    const by0 = Math.min(...zs.map((z) => z.cy - z.R)), by1 = Math.max(...zs.map((z) => z.cy + z.R));
    const sx = (W - 2 * m) / (bx1 - bx0 || 1), sy = (H - 2 * m) / (by1 - by0 || 1), sr = Math.min(sx, sy);
    for (const z of zs) {
      z.cx = m + (z.cx - bx0) * sx; z.cy = m + (z.cy - by0) * sy;
      z.R *= sr;
    }
    const out = new Map(zs.map((z) => [z.i, z]));
    zonasCache.set(W, out);
    return out;
  }
  // cada punto, dentro de la zona de su comunidad, en la misma dirección y distancia (a escala) que en el espacio conjunto
  function enZonas(ox, oy, r, grupo, W, H, m) {
    const Z = zonas(W, H, m);
    grupo.forEach((k, i) => {
      const z = Z.get(k);
      if (!z) return;
      const s = (z.R * 0.5) / z.mediana;
      let dx = (ox[i] - z.mx) * s, dy = (oy[i] - z.my) * s;
      const d = Math.hypot(dx, dy), tope = Math.max(0, z.R - r[i]);
      if (d > tope) { dx *= tope / d; dy *= tope / d; }
      ox[i] = Math.min(W - m, Math.max(m, z.cx + dx));
      oy[i] = Math.min(H - m, Math.max(m, z.cy + dy));
    });
  }
  function pintarMapa() {
    const mc = mapaConc(), cb = conCambios(), color = colorEf();
    const nodos = [], cnt = new Array(N).fill(0);
    encima = new Map();
    let llenos = 0;
    for (let g = 0; g < N; g++) {
      if (A.c[g] !== mc) continue;
      const cs = deArt[g].filter((c) => pasa(c));
      cnt[g] = cs.length;
      const lic = cs.filter((c) => c.fase === "lic").length;
      if (cs.length) { llenos++; if (conEnlaces()) encima.set(g, cs); }
      const fams = ["reemplaza", "agrega", "elimina"].map((f) => [f, cs.filter((c) => c.fams.includes(f)).length]).filter(([, n]) => n);
      const nEq = eqs(g).length;
      nodos.push({
        id: g, label: `${A.num[g]} ${corto(A.t[g], 40)}`,
        group: color === "comunidad" ? `c${A.cm[g]}` : cb ? BASES : (A.parte[g] || BASES),
        // el mismo tamaño en las tres vistas (las citas que recibe): al cambiar de vista los puntos no se mueven ni
        // cambian de tamaño, y lo único que cambia son los enlaces y el color
        size: tamNodo(g), x: A.x[g], y: A.y[g],
        "Comunidad": COM[A.cm[g]]?.t || "—",
        "Parte": A.parte[g] || "—",
        "Citas": `${A.ci?.[g] ?? 0} recibidas de ${A.entra[g].length} artículos · cita a ${A.sale[g].length}`,
        "Equivalentes": nEq ? `en ${nEq} de las otras ${C.length - 1} concesiones` : "propio de esta concesión",
        "Cambios": `${cs.length} ${palabra()} (${lic} en la licitación, ${cs.length - lic} en el contrato)`,
        "Tipo": fams.map(([f, n]) => `${f} ${n}`).join(" · ") || "—",
        "Último cambio": cs.length ? String(Math.max(...cs.map((c) => c.anio))) : "—",
        "Antes → después": (() => { const x = adSuma(g); return x ? `${x.nuevo ? "nuevo" : fmt(x.w0)} → ${fmt(x.w1)} palabras` : "mismo texto"; })(),
      });
    }
    acomodar(nodos, color === "comunidad" ? nodos.map((n) => A.cm[n.id]) : null);
    // dos anclas invisibles en las esquinas del lienzo: plotagents ajusta el dibujo a la extensión de los puntos, y con ellas
    // la escala es la misma en las cinco concesiones (se borran del SVG al dibujar)
    nodos.push({ id: -1, label: "", group: ANCLA, size: 1, x: 0, y: 0 }, { id: -2, label: "", group: ANCLA, size: 1, x: 1, y: 1 });
    const conSel = S.sel != null;
    const r = conSel ? relacionados() : { aristas: lineasMapa(mc, cnt), luz: [] };
    if (!conSel && color === "comunidad" && S.com != null) {
      r.luz = nodos.filter((n) => A.cm[n.id] === S.com).map((n) => n.id);
      r.aristas = r.aristas.filter((e) => A.cm[e.from] === S.com || A.cm[e.to] === S.com);
    }
    // por comunidad: en las Bases, color pleno; con los cambios, tenue si no cambió y lleno (encima) si cambió
    const porCom = color === "comunidad";
    const colores = porCom ? Object.fromEntries(COM.map((_, i) => [`c${i}`, cb ? claro(colorCom(i), 0.42) : colorCom(i)]))
      : cb ? { [BASES]: GRIS_BASE } : { ...Object.fromEntries(Object.entries(PALETA.parte).map(([k, [, c]]) => [k, c])), [BASES]: GRIS_BASE };
    colores[ANCLA] = "rgba(0,0,0,0)";
    // por comunidad, cada cita va del color de la comunidad del artículo que cita
    if (porCom) for (const e of r.aristas) colores[`${e.from}→${e.to}`] = colorCom(A.cm[e.from]);
    const lineas = lineasEf();
    const spec = {
      type: "network", layout: "preset", stretch: true, nodes: nodos, data: r.aristas, colors: colores,
      legend: false, curveness: 0.2, edgeTip: false, height: ALTO_MAPA, minRadius: R_MIN, maxRadius: R_MAX, edgeWidth: conSel ? 1.2 : porCom ? 1 : 0.7,
      labels: 0, locale: "es", padding: [8, 8], edgeColor: porCom ? "source" : "neutral",
      // con los enlaces que crean o destruyen los cambios encima, las citas de siempre quedan de fondo
      edgeOpacity: conSel ? (conEnlaces() ? 0.35 : 0.7) : conEnlaces() ? (porCom ? 0.1 : 0.06) : porCom ? 0.16 : 0.08,
      tooltip: cb ? ["Comunidad", "Cambios", "Tipo", "Último cambio", "Parte", "Antes → después"] : S.vista === "todo" ? ["Comunidad", "Parte", "Citas", "Cambios", "Antes → después"] : ["Comunidad", "Parte", "Citas", "Equivalentes", "Cambios"],
    };
    if (r.luz.length) spec.highlight = r.luz;
    $("#conexiones").hidden = conSel;
    // cabecera: un título de una línea y la misma ayuda en las tres vistas
    $("#mapa-titulo").textContent = conSel
      ? `${C[mc].nombre} · ${A.num[S.sel]} ${A.t[S.sel]}`
      : cb ? `${C[mc].nombre}: ${fmt(llenos)} de ${fmt(C[mc].n)} artículos cambiaron`
        : `${C[mc].nombre}: los ${fmt(C[mc].n)} artículos de sus Bases`;
    $("#mapa-ayuda").innerHTML = `Cerca: contenido parecido · tamaño: citas que recibe · color: ${porCom ? "su comunidad" : esc(leyendaColor(mc, true))}`
      + (porCom ? `<div class="coms">${leyendaColor(mc)}</div>` : ` ${leyendaColor(mc)}`);
    // recuadro en el mapa: qué agrega esta vista
    const notas = [];
    if (conSel) notas.push(S.cambio != null ? "Resaltado: lo que cambió el mismo acto · Esc cierra" : "Sus citas · Esc cierra");
    else if (cb) notas.push(porCom ? "Tenue: no cambió" : "Gris: no cambió");
    else if (S.vista === "todo") notas.push(`<span class="aro-mue"></span> cambió`);
    if (conEnlaces()) notas.push(leyendaEnlaces(mc));
    recuadro.innerHTML = notas.map((x) => `<div>${x}</div>`).join("");
    recuadro.hidden = !notas.length;
    try {
      if (mapa) mapa.update(spec); else mapa = PA.render(lienzo, spec);
    } catch (e) { console.error(e); lienzo.textContent = "No se pudo dibujar el mapa."; }
    superponer(nodos, r.luz, mc);
    rotular();
  }
  // enlaces que crean (verde) o destruyen (rojo) los cambios; las citas nuevas siguen el filtro de fase
  const VERDE = "#1d9a5b", ROJO = "#d0385e";
  const enlacesVisibles = (mc) => ENLACES[mc].filter((e) => (e.tipo !== "cita" || pasaActo(mc, e.acto))
    && (S.sel == null || e.a === S.sel || e.b === S.sel)
    && (S.sel != null || S.com == null || colorEf() !== "comunidad" || A.cm[e.a] === S.com || A.cm[e.b] === S.com));
  // tres renglones cortos; la explicación larga queda en el title (el árbol no registra citas que se pierdan)
  function leyendaEnlaces(mc) {
    const l = enlacesVisibles(mc), n = (f) => l.filter(f).length;
    const ln = (c, d) => `<span class="ln${d ? " dash" : ""}" style="border-color:${c}"></span>`;
    const ayuda = "Cita nueva: aparece en un acto posterior (el árbol no registra las citas que se pierden). Se acercan / se alejan: entran o salen de los 8 artículos más parecidos del otro (φ), de las Bases originales a las vigentes.";
    return `<div class="enl" title="${esc(ayuda)}"><span>${ln(VERDE)} cita nueva <b>${n((e) => e.tipo === "cita")}</b></span><span>${ln(VERDE, 1)} se acercan <b>${n((e) => e.tipo !== "cita" && e.signo > 0)}</b></span><span>${ln(ROJO, 1)} se alejan <b>${n((e) => e.tipo !== "cita" && e.signo < 0)}</b></span></div>`;
  }
  const textoEnlace = (e, mc) => {
    const n = (g) => `${A.num[g]} ${corto(A.t[g], 40)}`;
    if (e.tipo === "cita") { const a = C[mc].actos[e.acto] || ["", ""]; return `Cita nueva: ${n(e.a)} → ${n(e.b)}\n${a[0]} (${a[1]})`; }
    return e.signo > 0 ? `Se acercan (φ ${coma(e.phi)} hoy):\n${n(e.a)} ↔ ${n(e.b)}` : `Se alejan (φ ${coma(e.phi)} en las Bases):\n${n(e.a)} ↔ ${n(e.b)}`;
  };
  function dibujarEnlaces(capaSvg, els, mc) {
    const gl = document.createElementNS(NS, "g");
    gl.setAttribute("class", "enlaces");
    gl.setAttribute("pointer-events", "visibleStroke");
    const defs = document.createElementNS(NS, "defs");
    defs.innerHTML = `<marker id="punta-enlace" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="${VERDE}"/></marker>`;
    gl.append(defs);
    for (const e of enlacesVisibles(mc)) {
      const a = els.get(e.a), b = els.get(e.b);
      if (!a || !b) continue;
      const x1 = +a.getAttribute("cx"), y1 = +a.getAttribute("cy"), x2 = +b.getAttribute("cx"), y2 = +b.getAttribute("cy");
      if (![x1, y1, x2, y2].every(Number.isFinite)) continue;
      // una curva suave; la cita termina en el borde del artículo citado, con punta
      const dx = x2 - x1, dy = y2 - y1, d = Math.hypot(dx, dy) || 1, rb = +b.getAttribute("r") || 3;
      const ex = e.tipo === "cita" ? x2 - (dx / d) * (rb + 2) : x2, ey = e.tipo === "cita" ? y2 - (dy / d) * (rb + 2) : y2;
      const qx = (x1 + ex) / 2 - (dy / d) * d * 0.15, qy = (y1 + ey) / 2 + (dx / d) * d * 0.15;
      const path = document.createElementNS(NS, "path");
      path.setAttribute("d", `M${x1.toFixed(1)} ${y1.toFixed(1)}Q${qx.toFixed(1)} ${qy.toFixed(1)} ${ex.toFixed(1)} ${ey.toFixed(1)}`);
      path.setAttribute("fill", "none");
      path.setAttribute("stroke", e.signo > 0 ? VERDE : ROJO);
      path.setAttribute("stroke-width", e.tipo === "cita" ? "2.2" : "1.6");
      path.setAttribute("stroke-linecap", "round");
      path.setAttribute("opacity", "0.85");
      if (e.tipo !== "cita") path.setAttribute("stroke-dasharray", "5 3");
      else path.setAttribute("marker-end", "url(#punta-enlace)");
      const t = document.createElementNS(NS, "title");
      t.textContent = textoEnlace(e, mc);
      path.append(t);
      gl.append(path);
    }
    capaSvg.append(gl);
  }

  // lo que cambió hasta el año, superpuesto sobre el punto de la base (mismo centro, radio según sus cambios)
  const NS = "http://www.w3.org/2000/svg";
  // los trozos de color de un nodo: [cuánto, color]
  function trozos(g, cs, mc) {
    const color = colorEf();
    if (color === "comunidad") return [[1, colorCom(A.cm[g])]];
    if (color === "fase") return ["lic", "con"].map((f) => [cs.filter((c) => c.fase === f).length, PALETA.fase[f][1]]);
    if (color === "tipo") {
      const n = { reemplaza: 0, agrega: 0, elimina: 0 };
      for (const c of cs) for (const e of c.ed) n[FAMILIA(e[0])]++;      // proporción de sus ediciones
      return Object.entries(n).map(([f, k]) => [k, PALETA.tipo[f][1]]);
    }
    if (color === "anio") {
      const [a0, a1] = rangoConc[mc];
      return [[1, rampa((Math.max(...cs.map((c) => c.anio)) - a0) / Math.max(1, a1 - a0))]];
    }
    return [[1, (PALETA.parte[A.parte[g]] || ["", "#8a8fa3"])[1]]];
  }
  function leyendaColor(mc, soloNombre = false) {
    if (soloNombre) return { tipo: "tipo de cambio", anio: "año de su último cambio", fase: "fase de su cambio", parte: "parte de las Bases" }[colorEf()] || "";
    const mue = (c) => `<span class="mue" style="background:${c}"></span>`;
    const color = colorEf();
    if (color === "comunidad") {
      // las comunidades de esta concesión, de la más grande a la más chica: cuántos artículos tiene (y cuántos cambiaron)
      const n = COM.map(() => [0, 0]);
      for (let g = 0; g < N; g++) if (A.c[g] === mc) { n[A.cm[g]][0]++; if (encima.has(g)) n[A.cm[g]][1]++; }
      return COM.map((c, i) => [c, i]).filter(([, i]) => n[i][0]).sort((a, b) => n[b[1]][0] - n[a[1]][0])
        .map(([c, i]) => `<button type="button" class="com${S.com === i ? " on" : ""}${S.com != null && S.com !== i ? " off" : ""}" data-com="${i}" title="${esc(c.ej.join(" · "))}${conEnlaces() ? ` · cambiaron ${n[i][1]} de ${n[i][0]}` : ""}">${mue(colorCom(i))} ${esc(c.t)} <span>${n[i][0]}</span></button>`).join("");
    }
    if (color === "anio") {
      const [a0, a1] = rangoConc[mc];
      return `último cambio: ${a0} <span class="rampa" style="background:linear-gradient(90deg,${RAMPA.join(",")})"></span> ${a1}`;
    }
    const pal = PALETA[color];
    return Object.values(pal).map(([t, c]) => `${mue(c)} ${t.toLowerCase()}`).join(" ");
  }
  function superponer(nodos, luz, mc) {
    const svg = lienzo.querySelector("svg");
    if (!svg) return;
    svg.querySelector("g.superpuesto")?.remove();
    svg.querySelectorAll('[data-node="-1"], [data-node="-2"]').forEach((el) => el.remove());
    const els = new Map([...svg.querySelectorAll("[data-node]")].map((el) => [+el.getAttribute("data-node"), el]));
    const capaSvg = document.createElementNS(NS, "g");
    capaSvg.setAttribute("class", "superpuesto");
    capaSvg.setAttribute("pointer-events", "none");
    const resaltadas = luz.length ? new Set(luz) : null;
    if (conEnlaces()) dibujarEnlaces(capaSvg, els, mc);
    for (const [g, cs] of encima) {
      if (S.vista === "todo") {                        // en «Todo», lo que cambió lleva un aro sobre su color de siempre
        const el = els.get(g);
        if (!el) continue;
        const aro = document.createElementNS(NS, "circle");
        aro.setAttribute("cx", el.getAttribute("cx")); aro.setAttribute("cy", el.getAttribute("cy"));
        aro.setAttribute("r", (+el.getAttribute("r") || 3) + 2.2);
        aro.setAttribute("fill", "none"); aro.setAttribute("stroke", "#141a3f"); aro.setAttribute("stroke-width", "1.4");
        if (resaltadas && !resaltadas.has(g)) aro.setAttribute("opacity", "0.15");
        capaSvg.append(aro);
        continue;
      }
      const partes = trozos(g, cs, mc).filter(([n]) => n > 0);
      const x = { n: partes.reduce((s, [n]) => s + n, 0) };
      const el = els.get(g);
      if (!el) continue;
      const cx = +el.getAttribute("cx"), cy = +el.getAttribute("cy");
      const rr = +el.getAttribute("r");                // la torta ocupa el punto entero: no cambia su tamaño
      if (!Number.isFinite(cx) || !rr) continue;
      const grupo = document.createElementNS(NS, "g");
      if (resaltadas && !resaltadas.has(g)) grupo.setAttribute("opacity", "0.15");
      let ang = -Math.PI / 2;
      for (const [n, color] of partes) {
        if (!n) continue;
        const fr = n / x.n, a2 = ang + fr * 2 * Math.PI;
        let forma;
        if (fr > 0.9999) {
          forma = document.createElementNS(NS, "circle");
          forma.setAttribute("cx", cx); forma.setAttribute("cy", cy); forma.setAttribute("r", rr);
        } else {
          forma = document.createElementNS(NS, "path");
          const p = (t) => `${(cx + rr * Math.cos(t)).toFixed(2)} ${(cy + rr * Math.sin(t)).toFixed(2)}`;
          forma.setAttribute("d", `M${cx} ${cy}L${p(ang)}A${rr} ${rr} 0 ${a2 - ang > Math.PI ? 1 : 0} 1 ${p(a2)}Z`);
        }
        forma.setAttribute("fill", color);
        forma.setAttribute("stroke", "#fff");
        forma.setAttribute("stroke-width", "0.6");
        grupo.append(forma);
        ang = a2;
      }
      capaSvg.append(grupo);
    }
    svg.append(capaSvg);
  }
  // plotagents no rotula cuando hay cientos de nodos: ponemos encima el rótulo de la selección
  function rotular() {
    capa.innerHTML = "";
    const g = S.sel;
    const svg = lienzo.querySelector("svg");
    if (!svg) return;
    if (g == null && colorEf() === "comunidad") return rotularComunidades(svg);
    if (g == null) return;
    const el = svg.querySelector(`[data-node="${g}"]`);
    if (!el) return;
    const caja = mapaEl.getBoundingClientRect(), r = el.getBoundingClientRect();
    const x = r.left + r.width / 2 - caja.left, y = r.top + r.height / 2 - caja.top;
    const d = document.createElement("div");
    d.className = "rotulo sel";
    d.style.left = `${x}px`; d.style.top = `${y - r.height / 2 - 8}px`;
    d.textContent = `${A.num[g]} ${corto(A.t[g], 40)}`;
    capa.append(d);
    const o = document.createElement("div");
    o.className = "aro";
    const rad = Math.max(r.width, 10) / 2 + 6;
    Object.assign(o.style, { left: `${x - rad}px`, top: `${y - rad}px`, width: `${2 * rad}px`, height: `${2 * rad}px` });
    capa.append(o);
  }
  // el nombre de cada comunidad, sobre su grupo de puntos y dentro del lienzo
  function rotularComunidades(svg) {
    const caja = mapaEl.getBoundingClientRect(), pos = new Map();
    for (const el of svg.querySelectorAll("[data-node]")) {
      const g = +el.getAttribute("data-node");
      if (A.c[g] !== S.conc) continue;
      const r = el.getBoundingClientRect();
      if (!pos.has(A.cm[g])) pos.set(A.cm[g], []);
      pos.get(A.cm[g]).push([r.left + r.width / 2 - caja.left, r.top - caja.top]);
    }
    const med = (v) => { v = v.slice().sort((a, b) => a - b); return v[Math.floor(v.length / 2)]; };
    for (const [i, ps] of pos) {
      if (S.com != null && S.com !== i) continue;
      const d = document.createElement("button");
      d.type = "button";
      d.className = "rotulo com";
      d.dataset.com = i;
      d.style.color = colorCom(i);
      d.textContent = COM[i].t;
      capa.append(d);
      const w = d.offsetWidth / 2 + 4;
      d.style.left = `${Math.min(caja.width - w, Math.max(w, med(ps.map((p) => p[0]))))}px`;
      d.style.top = `${Math.max(16, Math.min(...ps.map((p) => p[1])) - 3)}px`;
    }
  }
  window.addEventListener("resize", () => requestAnimationFrame(rotular));
  mapaEl.addEventListener("click", (e) => {
    const el = e.target.closest("[data-node]");
    if (!el) return;
    e.stopPropagation();
    const g = +el.getAttribute("data-node");
    if (Number.isFinite(g) && g >= 0) seleccionar(g === S.sel ? null : g);
  }, true);

  // ---------- piezas de texto que se repiten
  const chipArt = (g, extra = "") => `<button type="button" class="chip" data-g="${g}" title="${esc(C[A.c[g]].nombre)} · ${esc(A.num[g])} ${esc(A.t[g])}"><span class="pt" style="background:${C[A.c[g]].color}"></span>${esc(A.num[g])} ${esc(corto(A.t[g], 30))}${extra}</button>`;
  const lista = (gs, n = 10) => gs.length
    ? gs.slice(0, n).map((g) => chipArt(g)).join("") + (gs.length > n ? `<span class="quien"> y ${gs.length - n} más</span>` : "")
    : `<span class="quien">Ninguno</span>`;
  const resumen = (g) => {
    const cs = deArt[g].filter((c) => pasa(c, { fase: false }));
    const l = cs.filter((c) => c.fase === "lic").length;
    return { n: cs.filter((c) => pasa(c)).length, lic: l, con: cs.length - l };
  };
  // las citas que recibe un artículo x.y.z y en cuáles de sus sub-artículos caen (05_tablero.py: ci, cs)
  const repartoCitas = (g) => {
    const tot = A.ci?.[g] ?? 0, cs = A.cs?.[g] ?? [];
    if (!tot) return "No recibe citas de otros artículos.";
    if (cs.length === 1 && cs[0][0] === A.num[g]) return `${tot} ${tot === 1 ? "cita recibida" : "citas recibidas"}, todas al ${esc(A.num[g])}`;
    return `${tot} citas recibidas: ${cs.map(([n, v]) => `${esc(n)} (${v})`).join(" · ")}${cs.reduce((s, [, v]) => s + v, 0) < tot ? " · otras" : ""}`;
  };
  // "agrega un párrafo ×3 · reemplaza texto": qué hizo el acto en el artículo, sin repetir
  const queHizo = (ed) => {
    const n = new Map();
    for (const e of ed) n.set(e[0], (n.get(e[0]) || 0) + 1);
    return [...n].map(([t, k]) => `${TIPO[t] || t}${k > 1 ? ` ×${k}` : ""}`).join(" · ");
  };
  const ediciones = (ed) => `<ol class="ed">${ed.map((e) => `<li><span class="quien">${esc(TIPO[e[0]] || e[0])}${e[1] ? ` · ${esc(e[1])}` : ""}</span>${e[2] ? ` ${esc(e[2])}` : ""}</li>`).join("")}</ol>`;
  const itemCambio = (cb, conArt = false) => {
    const acto = C[cb.ci].actos[cb.acto] || ["", "", ""];
    return `<li><div class="f"><span class="fase ${cb.fase}">${nombreFase(cb.fase)}</span> <b>${esc(acto[0])}</b> · ${esc(acto[1])} · ${esc(queHizo(cb.ed))}${conArt ? ` · ${chipArt(cb.g)}` : ""}</div>${ediciones(cb.ed)}</li>`;
  };

  // ---------- ficha
  const ficha = $("#ficha");
  const signo = (x) => (x > 0 ? `+${fmt(x)}` : x < 0 ? `−${fmt(-x)}` : "0");
  const coma = (x, d = 2) => (x == null ? "—" : x.toFixed(d).replace(".", ","));
  const diffHTML = (ops) => ops.map(([op, t, omit]) => {
    const resto = omit ? ` <span class="omit">[+${fmt(omit)} palabras más]</span>` : "";
    return op === 0 ? esc(t) : op < 0 ? `<del>${esc(t)}${resto}</del>` : `<ins>${esc(t)}${resto}</ins>`;
  }).join(" ");
  const flecha = (p0, p1) => (p0 == null ? `<span class="sube">nuevo</span>` : p0 === p1 ? `<span class="igual">=</span>`
    : p0 > p1 ? `<span class="sube" title="En las Bases era el ${p0}.º">↑${p0 - p1}</span>` : `<span class="baja" title="En las Bases era el ${p0}.º">↓${p1 - p0}</span>`);
  const balance = (x) => (x.nuevo ? `<span class="badge">artículo nuevo</span>`
    : x.dudoso ? `<span class="badge dudoso" title="Queda más corto, pero puede ser porque el árbol no extrajo todo el texto nuevo. Revísalo contra el acto.">más corto · a verificar</span>`
    : x.w1 < x.w0 ? `<span class="badge simp">simplificado ${pct((x.w0 - x.w1) / Math.max(1, x.w0))}</span>`
    : x.w1 > x.w0 ? `<span class="badge">ampliado ${pct((x.w1 - x.w0) / Math.max(1, x.w0))}</span>` : `<span class="badge">mismo largo</span>`);

  // sin artículo abierto: la licitación elegida (sus Bases) y, aparte, qué pasa cuando se modifica
  function resumenConc() {
    const ci = S.conc, c = C[ci], gs = gsDe(ci);
    const posteriores = Math.max(0, c.actos.length - 1);
    const adj = c.actos[c.adj];
    const { hoy, p0, p1 } = puestos(ci);
    const citados = hoy.slice(0, 8).map((g) => `<li><span class="pos">${p1.get(g)}</span>${chipArt(g)}<span class="q">${A.entra[g].length} lo citan ${flecha(p0.get(g), p1.get(g))}</span></li>`).join("");
    const dejaron = [...p0].filter(([g, i]) => i <= 8 && p1.get(g) > 8).sort((a, b) => a[1] - b[1]).map(([g]) => g);
    const partes = Object.keys(PALETA.parte).map((k) => [k, gs.filter((g) => A.parte[g] === k).length]).filter(([, n]) => n);
    const coms = porComunidad(ci).map((l, i) => [i, l]).filter(([, l]) => l.length).sort((a, b) => b[1].length - a[1].length);
    const co = concentracion(ci), pl = plantilla(ci);
    const propios = pl.Propio.slice().sort((a, b) => citasRec(b) - citasRec(a));
    // cuando se modifica: qué artículos cambian (con los filtros de fase y tipo)
    const cambia = (g) => cuenta(g) > 0;
    const q = cuartos(ci).map((l) => parte(l, cambia));
    const tasaCom = coms.filter(([, l]) => l.length >= 5).map(([i, l]) => [i, parte(l, cambia)]).sort((a, b) => b[1] - a[1]);
    const masMod = gs.filter(cambia).sort((a, b) => cuenta(b) - cuenta(a)).slice(0, 5);
    const nCambia = gs.filter(cambia).length;
    const botonCom = (i, extra) => `<button type="button" class="com${S.com === i ? " on" : ""}" data-com="${i}" title="Resaltar en el mapa · ${esc(COM[i].ej.join(" · "))}"><span class="mue" style="background:${colorCom(i)}"></span> ${esc(COM[i].t)} <span>${extra}</span></button>`;
    return `<div class="resumen">
      <span class="etiq"><span class="pt" style="background:${c.color}"></span>${esc(c.largo)}</span>
      <h2>Las Bases de ${esc(c.nombre)}</h2>
      <p class="parte">Publicadas el ${esc(c.actos[0]?.[1] || "—")} · ${adj ? `adjudicada el ${esc(adj[1])}` : "sin decreto de adjudicación"} · ${posteriores} actos posteriores</p>
      <div class="nums">
        <div><b>${fmt(gs.length)}</b><span>artículos x.y.z</span></div>
        <div><b>${fmt(co.tot)}</b><span>citas entre artículos</span></div>
        <div><b>${pct(pl["En las otras cuatro"].length / gs.length)}</b><span>tiene equivalente en las otras cuatro</span></div>
      </div>
      <h3>Sus partes</h3>
      <p>${partes.map(([k, n]) => `<span class="mue" style="background:${PALETA.parte[k][1]}"></span> ${esc(k)} <b>${fmt(n)}</b> <span class="quien">(${pct(n / gs.length)})</span>`).join(" · ")}</p>
      <h3>De qué tratan <span class="quien">· comunidades de contenido</span></h3>
      <div class="coms">${coms.map(([i, l]) => botonCom(i, `${l.length} · ${pct(l.length / gs.length)}`)).join("")}</div>
      <h3>Los más citados <span class="quien">· flecha: vs. Bases originales</span></h3>
      <ol class="rank">${citados}</ol>
      ${dejaron.length ? `<p class="quien">Salieron de los 8 primeros: ${dejaron.map((g) => chipArt(g, ` · era ${p0.get(g)}.º`)).join("")}</p>` : ""}
      <p class="quien">El 10 % más citado recibe el ${pct(co.top10)} de las citas (Gini ${coma(co.gini)}); ${fmt(co.sinCitas)} artículos no reciben ninguna.</p>
      <h3>Propios de esta licitación <span class="quien">· sin equivalente en las otras (φ ≥ 0,5)</span></h3>
      ${propios.length ? `<p class="quien">${fmt(propios.length)} de ${fmt(gs.length)} artículos (${pct(propios.length / gs.length)}). Los más citados:</p>${lista(propios, 6)}` : `<p class="quien">Ninguno: todos tienen equivalente en otra concesión.</p>`}
      <div class="efecto">
        <h3>Cuando se modifica <span class="quien">· ${esc(queCambios())}</span></h3>
        ${nCambia ? `<p>Cambia el ${pct(nCambia / gs.length)} de sus artículos, pero no por igual: el ${pct(q[0] ?? 0)} del cuarto más citado de las Bases originales y el ${pct(q[3] ?? 0)} del menos citado.</p>
        ${tasaCom.length > 1 ? `<p>Por tema, lo que más cambia es ${esc(COM[tasaCom[0][0]].t.toLowerCase())} (${pct(tasaCom[0][1])} de sus artículos) y lo que menos, ${esc(COM[tasaCom[tasaCom.length - 1][0]].t.toLowerCase())} (${pct(tasaCom[tasaCom.length - 1][1])}).</p>` : ""}
        <p class="quien">Los que más cambiaron:</p>${masMod.map((g) => chipArt(g, ` · ${cuenta(g)}`)).join("")}`
        : `<p class="quien">Ningún artículo cambia con estos filtros.</p>`}
      </div>
      <p class="quien pie-ficha">Elige un punto del mapa o busca un artículo. Abajo, la licitación comparada con las otras cuatro.</p>
    </div>`;
  }
  // el artículo abierto en las Bases originales y en su versión vigente: texto y citas
  function bloqueAD(g) {
    if (!AD) return "";
    const x = adSuma(g);
    const nuevasSale = NUEVA[g], nuevasEntra = A.entra[g].filter((a) => NUEVA[a].includes(g));
    const citas = `<div class="nums ad-cit">
        <div><b>${fmt(entra0(g).length)} → ${fmt(A.entra[g].length)}</b><span>artículos lo citan</span></div>
        <div><b>${fmt(sale0(g).length)} → ${fmt(A.sale[g].length)}</b><span>artículos que cita</span></div>
        <div><b>${A.nuevo?.[g] ? "nuevo" : `${p0Sel(g) ?? "—"}.º → ${p1Sel(g)}.º`}</b><span>puesto en citas</span></div>
      </div>
      ${nuevasEntra.length ? `<p class="quien">Lo citan desde un acto posterior:</p>${lista(nuevasEntra, 6)}` : ""}
      ${nuevasSale.length ? `<p class="quien">Cita desde un acto posterior a:</p>${lista(nuevasSale, 6)}` : ""}`;
    if (!x) return `<div class="efecto ad"><h3>Antes y después</h3>
      <p class="quien">Entre las Bases y la versión vigente su texto no cambia (los cambios que registra no alteran el texto que el árbol guarda).</p>${citas}</div>`;
    const partes = x.partes.filter(([, a]) => a.d.length);
    return `<div class="efecto ad">
      <h3>Antes → después</h3>
      <div class="nums">
        <div><b>${x.nuevo ? "—" : fmt(x.w0)} → ${fmt(x.w1)}</b><span>palabras</span></div>
        <div><b>${coma(x.phi)}</b><span>parecido φ</span></div>
        <div><b>+${x.mas} / −${x.menos}</b><span>incisos</span></div>
      </div>
      <p>${balance(x)}</p>
      ${citas}
      ${partes.length ? `<details class="ad-texto"${partes.length === 1 ? " open" : ""}><summary>El texto con sus diferencias: <del>tachado</del> salió, <ins>subrayado</ins> entró</summary>
        ${partes.map(([id, a]) => `${partes.length > 1 ? `<h4>${esc(id.replace(/^[^:]*:/, ""))} · ${a.nuevo ? "nuevo" : fmt(a.w[0])} → ${fmt(a.w[1])} palabras</h4>` : ""}<div class="diff">${diffHTML(a.d)}</div>`).join("")}
      </details>` : ""}
    </div>`;
  }
  let puestosCache = null;
  const puestosSel = () => (puestosCache?.ci === S.conc ? puestosCache : (puestosCache = { ci: S.conc, ...puestos(S.conc) }));
  const p0Sel = (g) => puestosSel().p0.get(g), p1Sel = (g) => puestosSel().p1.get(g);

  function pintarFicha() {
    const g = S.sel;
    if (g == null) { ficha.innerHTML = resumenConc(); return; }
    const ci = A.c[g], c = C[ci], r = resumen(g);
    const hist = deArt[g].map((cb) => {
      const acto = c.actos[cb.acto] || ["", "", ""];
      const motivo = !pasa(cb, { tipo: false }) ? "otra fase" : !pasa(cb, { fase: false }) ? "otro tipo" : "";
      return `<li data-i="${cb.i}" aria-current="${S.cambio === cb.i}" class="${motivo ? "futuro" : ""}" tabindex="0">
        <div class="f"><span class="fase ${cb.fase}">${nombreFase(cb.fase)}</span><b>${esc(acto[0])}</b><span>${esc(acto[1])}</span>${motivo ? `<span class="no-pasa">· fuera del filtro (${motivo})</span>` : ""}</div>
        <div class="f">${esc(queHizo(cb.ed))}</div>
        ${ediciones(cb.ed)}
      </li>`;
    }).join("");
    const co = A.cm[g], nCom = gsDe(ci).filter((x) => A.cm[x] === co).length;
    ficha.innerHTML = `
      <button type="button" class="cerrar" aria-label="Cerrar la ficha">×</button>
      <button type="button" class="etiq chip" data-conc="${ci}" title="Filtrar por ${esc(c.nombre)}"><span class="pt" style="background:${c.color}"></span>${esc(c.nombre)}</button>
      <h2>${esc(A.num[g])} ${esc(A.t[g])}</h2>
      <div class="parte">${esc(A.parte[g])}${A.sub[g].length ? ` · incluye ${esc(A.sub[g].join(", "))}` : ""}</div>
      <div class="coms"><button type="button" class="com${S.com === co ? " on" : ""}" data-com="${co}" title="Resaltar la comunidad en el mapa"><span class="mue" style="background:${colorCom(co)}"></span> ${esc(COM[co]?.t || "—")} <span>${nCom} artículos</span></button></div>
      <div class="nums">
        <div><b>${A.entra[g].length}</b><span>artículos lo citan</span></div>
        <div><b>${A.sale[g].length}</b><span>artículos que cita</span></div>
        <div><b>${p1Sel(g)}.º</b><span>de ${fmt(C[ci].n)} en citas</span></div>
      </div>
      ${A.ci?.[g] ? `<p class="quien">${repartoCitas(g)}</p>` : ""}
      <h3>En las otras concesiones</h3>
      ${otras(g)}
      <h3>Lo citan (${A.entra[g].length})</h3>${lista(A.entra[g])}
      <h3>Cita a (${A.sale[g].length})</h3>${lista(A.sale[g])}
      <h2 class="sec-ficha">Cuando se modificó <span class="quien">· ${r.n} ${esc(palabra())}${r.lic + r.con ? ` · ${r.lic} en la licitación, ${r.con} en el contrato` : ""}</span></h2>
      ${S.cambio != null ? efecto(g, S.cambio) : ""}
      ${bloqueEnlaces(g)}
      ${bloqueAD(g)}
      <h3>Sus cambios ${A.h[g].length ? `<span class="quien">· elige uno para ver su efecto</span>` : ""}</h3>
      ${A.h[g].length ? `<ul class="hist">${hist}</ul>` : `<p class="quien">No cambió en ningún acto posterior a las Bases.</p>`}
      <h3>Su equivalente, en cada concesión <span class="quien">· cambios</span></h3>
      <div id="mini" class="mini"></div>
    `;
    pintarMini(g);
  }
  // los enlaces que crean o destruyen sus cambios (los mismos que el mapa dibuja en «Sus cambios» y «Todo»)
  function bloqueEnlaces(g) {
    const l = enlacesDe[g], otro = (e) => (e.a === g ? e.b : e.a);
    if (!l.length) return "";
    const grupo = (t, color, dash, es) => es.length ? `<p class="quien"><span class="ln${dash ? " dash" : ""}" style="border-color:${color}"></span> ${t} (${es.length})</p>${es.map((e) => chipArt(otro(e), e.phi != null ? ` · φ ${coma(e.phi)}` : "")).join("")}` : "";
    const cita = l.filter((e) => e.tipo === "cita");
    return `<div class="efecto enlaces-art"><h3>Enlaces que crean o destruyen sus cambios</h3>
      ${grupo("Ahora cita a", VERDE, 0, cita.filter((e) => e.a === g))}
      ${grupo("Ahora lo cita", VERDE, 0, cita.filter((e) => e.b === g))}
      ${grupo("Se acerca a", VERDE, 1, l.filter((e) => e.tipo !== "cita" && e.signo > 0))}
      ${grupo("Se aleja de", ROJO, 1, l.filter((e) => e.tipo !== "cita" && e.signo < 0))}
    </div>`;
  }
  function otras(g) {
    if (!eqs(g).length) return `<p class="quien">Es propio de esta concesión: no tiene un equivalente recíproco (φ ≥ 0,5) en otra.</p>`;
    return `<ul class="otras">${eqs(g).map(([b, phi]) => {
      const r = resumen(b);
      return `<li><div>${chipArt(b)}<div class="quien">${esc(C[A.c[b]].nombre)} · ${phi != null ? `φ ${String(phi).replace(".", ",")}` : "misma base"}</div></div>
        <span class="${r.n ? "si" : "no"}">${r.n ? `${r.n} ${palabra()}` : `sin ${palabra()}`}</span></li>`;
    }).join("")}</ul>`;
  }
  function efecto(g, i) {
    const ci = A.c[g], h = A.h[g][i], acto = C[ci].actos[h[0]] || ["", "", ""], fase = faseDe(ci, h[0]);
    const mismos = [...(huella.get(`${ci}|${h[0]}`) || [])].filter((x) => x !== g).sort((a, b) => A.pr[b] - A.pr[a]);
    const alcanzados = A.entra[g].slice().sort((a, b) => A.pr[b] - A.pr[a]);
    const enOtras = eqs(g).map(([b]) => {
      const cb = deArt[b].filter((x) => pasa(x, { fase: false }));
      return { b, n: cb.length, igualFase: cb.filter((x) => x.fase === fase).length };
    });
    const tambien = enOtras.filter((o) => o.n > 0).length;
    return `<div class="efecto">
      <h3>Efecto de este cambio</h3>
      <p><span class="fase ${fase}">${nombreFase(fase)}</span> <b>${esc(acto[0])}</b> · ${esc(acto[1])} · ${esc(queHizo(h[1]))}</p>
      <h3>El mismo acto cambió otros ${mismos.length} artículos</h3>${lista(mismos, 8)}
      <h3>Lo citan, y les llega el cambio (${alcanzados.length})</h3>${lista(alcanzados, 8)}
      <h3>Su equivalente cambió en ${tambien} de ${enOtras.length} otras concesiones</h3>
      <div class="quien">${enOtras.length ? enOtras.map((o) => `${esc(C[A.c[o.b]].nombre)}: ${o.n ? `${o.n} cambios, ${o.igualFase} en la misma fase` : "sin cambios"}`).join(" · ") : "Sin equivalentes claros."}</div>
    </div>`;
  }
  function pintarMini(g) {
    const el = $("#mini");
    if (!el) return;
    const ids = [g, ...eqs(g).map(([b]) => b)];
    if (ids.length < 2) { el.innerHTML = ""; return; }
    const filas = ids.map((x) => {
      const r = resumen(x);
      return { concesion: `${C[A.c[x]].nombre}${x === g ? " (este)" : ""}`, [LIC]: r.lic, [CON]: r.con, g: x };
    });
    const spec = {
      type: "bar", data: filas, x: "concesion", y: [LIC, CON], stack: true, horizontal: true, sort: "none",
      colors: { [LIC]: AZUL, [CON]: GRIS }, format: "integer", height: 70 + filas.length * 34, padding: [4, 12, 4, 4],
      subtitle: "",
      locale: "es",
    };
    if (S.fase !== "todas") spec.highlight = S.fase === "lic" ? LIC : CON;
    el.innerHTML = "";
    try { PA.render(el, spec); } catch (e) { console.error(e); }
    el.onclick = (e) => {
      const nombre = e.target.closest("[data-tip]")?.getAttribute("data-tip").split("\n")[0];
      const fila = filas.find((f) => f.concesion === nombre);
      if (fila && fila.g !== g) seleccionar(fila.g);
    };
  }
  ficha.addEventListener("click", (e) => {
    if (e.target.closest(".cerrar")) return seleccionar(null);
    const cc = e.target.closest("[data-conc]");
    if (cc) return ponerConc(+cc.dataset.conc);
    const chip = e.target.closest("[data-g]");
    if (chip) return seleccionar(+chip.dataset.g);
    const li = e.target.closest(".hist li[data-i]");
    if (li) { const i = +li.dataset.i; S.cambio = S.cambio === i ? null : i; todo(); }
  });
  ficha.addEventListener("keydown", (e) => { if (e.key === "Enter" && e.target.matches(".hist li[data-i]")) e.target.click(); });

  // ---------- gráficos de abajo (cada uno filtra al hacer clic) y su detalle
  const graf = {};
  const ALTO_G = 380;                            // los gráficos de a pares miden lo mismo
  const ALTO_PAR2 = 560;                         // los más citados (dos barras por artículo) y su vecino, la plantilla común
  function dibujar(id, spec) {
    try {
      if (graf[id]) graf[id].update(spec); else graf[id] = PA.render(document.getElementById(id), spec);
    } catch (e) { console.error(id, e); }
  }
  // un gráfico de un par mide lo mismo que su vecino de alto automático (un mapa de calor): se dibuja, se mide y se corrige
  function igualarAlto(id, ref, spec) {
    const d = document.getElementById(ref).offsetHeight - document.getElementById(id).offsetHeight;
    if (Math.abs(d) > 2) { spec.height = Math.max(ALTO_G, spec.height + d); dibujar(id, spec); }
  }
  const metricaCita = (g) => (S.citas === "red" ? A.pr[g] : citasActos(g));
  // rótulo de un artículo de la base en los rankings: su título y el número que tiene en la primera concesión
  const numComun = (k) => {
    const ns = T.bases.m[k].map((g) => A.num[g]);
    return ns.slice().sort((a, b) => ns.filter((x) => x === b).length - ns.filter((x) => x === a).length)[0];
  };
  // con una sola concesión a la vista, el artículo es el de esa concesión (su número y su título); con varias, el de la base
  const unico = (k) => { const v = T.bases.m[k].filter(visible); return v.length === 1 ? v[0] : null; };
  const rotuloBase = (k) => { const g = unico(k); return g != null ? `${A.num[g]} ${corto(A.t[g], 34)}` : `${corto(T.bases.t[k], 34)} · ${numComun(k)}`; };
  const tituloBase = (k) => { const g = unico(k); return g != null ? `${A.num[g]} ${corto(A.t[g], 50)}` : rotuloBase(k).split(" · ")[0]; };
  // los equivalentes en las otras concesiones (los que no están a la vista)
  const otrosBase = (k) => { const o = T.bases.m[k].filter((g) => !visible(g)); return o.length ? `equivale a ${o.map((g) => `${C[A.c[g]].cod} ${A.num[g]}`).join(" · ")}` : ""; };
  const familia = (t) => sinTilde(t).replace(/^(de |del |de la |de los |tipos de )/, "").split(/[ ,]+/).slice(0, 2).join(" ");
  let topCitG = [], topAdC = [], topAdT = [];

  // detalle: filas <details> que recuerdan cuáles quedaron abiertas entre repintados
  const abiertos = new Set();
  document.addEventListener("toggle", (e) => {
    const d = e.target;
    if (d.matches?.(".detalle details[data-k]")) d.open ? abiertos.add(d.dataset.k) : abiertos.delete(d.dataset.k);
  }, true);
  const fila = (k, punto, titulo, q, cuerpo) => `<details data-k="${esc(k)}" ${abiertos.has(k) ? "open" : ""}><summary>${punto ? `<span class="pt" style="background:${punto}"></span>` : ""}<span>${titulo}</span><span class="q">${q}</span></summary><div class="cuerpo">${cuerpo}</div></details>`;
  const detalle = (id, titulo, filas, vacio = "Nada con estos filtros.") => {
    $(id).innerHTML = `<h3>${titulo}</h3>${filas.length ? filas.join("") : `<p class="quien">${vacio}</p>`}`;
  };
  $(".graficos").addEventListener("click", (e) => {
    const b = e.target.closest(".detalle [data-g]");
    if (b) { seleccionar(+b.dataset.g); irAlMapa(); }
  });

  function graficos() {
    licitacion();
    modificaciones();
    const [a0, a1] = rango();
    // 1 · el % acumulado de los cambios, por año desde las Bases (año 0 = los 12 meses desde su publicación).
    // Las cinco, para comparar; la elegida resaltada y su licitación sombreada. Un clic en un año abre sus actos.
    const filasAnio = [], acum = [];
    for (let ci = 0; ci < C.length; ci++) {
      const cs = cambios.filter((c) => c.ci === ci && pasa(c) && c.rel != null);
      const n = cs.length, por = new Map();
      for (const c of cs) por.set(c.rel, (por.get(c.rel) || 0) + 1);
      let suma = 0;
      const serie = [];
      for (let k = 0; k <= EDAD[ci]; k++) {
        suma += por.get(k) || 0;
        const v = n ? suma / n : 0;
        serie.push(v);
        filasAnio.push({ anio: String(k), concesion: C[ci].nombre, acumulado: v, "En ese año": `${por.get(k) || 0} ${palabra()}`, "Período": periodo(ci, k) });
      }
      acum[ci] = { n, serie, cero: n ? (por.get(0) || 0) / n : 0 };
    }
    const yo = acum[S.conc], al90 = yo.serie.findIndex((v) => v >= 0.9);
    const enAnio = yo.serie.map((v, k) => v - (k ? yo.serie[k - 1] : 0)), pico = enAnio.indexOf(Math.max(...enAnio));
    const base = cambios.filter((c) => pasa(c) && c.rel != null && c.ci === S.conc);
    const adjRel = relActo(S.conc, C[S.conc].adj);
    dibujar("g-anios", {
      type: "line", data: filasAnio, x: "anio", y: "acumulado", series: "concesion", colors: COLORES, highlight: C[S.conc].nombre,
      title: yo.n ? `En ${alcance()}, el ${pct(enAnio[pico])} de los ${queCambios()} llegó en el año ${pico}${al90 > pico ? `; el 90 %, al año ${al90}` : ""}` : `Sin ${queCambios()} con estos filtros`,
      subtitle: `% acumulado de los ${queCambios()} desde las Bases · año 0: ${periodo(S.conc, 0)}${adjRel != null ? ` · adjudicada en el año ${adjRel}${adjRel > 0 ? " (sombreado: la licitación)" : ""}` : ""}`,
      xBands: adjRel > 0 ? [{ from: "0", to: String(adjRel), label: "licitación" }] : [],
      legend: "top", format: "percent", yDomain: [0, 1], height: 380, locale: "es", tooltip: ["En ese año", "Período"],
    });
    // detalle: los actos detrás de esos cambios
    const porActo = new Map();
    for (const c of base) {
      if (S.verAnio != null && c.rel !== S.verAnio) continue;
      const k = `${c.ci}|${c.acto}`;
      if (!porActo.has(k)) porActo.set(k, []);
      porActo.get(k).push(c);
    }
    const actos = [...porActo.entries()].sort((a, b) => b[1].length - a[1].length);
    detalle("#d-anios", `${S.verAnio != null ? `Los actos del año ${S.verAnio} (${periodo(S.conc, S.verAnio)})` : `Los actos con más ${queCambios()}`} (${actos.length})`,
      actos.slice(0, 15).map(([k, cs]) => {
        const [ci, acto] = k.split("|").map(Number), a = C[ci].actos[acto] || ["", "", ""];
        // un acto cambia cada artículo una vez; el número es cuántas ediciones dejó en él
        const arts = cs.map((c) => [c.g, c.ed.length]).sort((x, y) => y[1] - x[1]);
        return fila(`acto|${k}|${S.fase}|${S.tipo}`, C[ci].color, `<b>${esc(a[0])}</b>${S.conc < 0 ? ` · ${esc(C[ci].nombre)}` : ""} · ${esc(a[1])} <span class="fase ${faseDe(ci, acto)}">${nombreFase(faseDe(ci, acto))}</span>`,
          `${arts.length} ${arts.length === 1 ? "artículo" : "artículos"} · ${((n) => `${n} ${n === 1 ? "edición" : "ediciones"}`)(cs.reduce((s, c) => s + c.ed.length, 0))}`,
          arts.map(([g, n]) => chipArt(g, ` · ${n} ${n === 1 ? "edición" : "ediciones"}`)).join(""));
      }).concat(actos.length > 15 ? [`<p class="quien mas-filas">y ${actos.length - 15} actos más</p>`] : []));

    // 2 · licitación y contrato, por concesión (las cinco siempre; resalta la fase elegida)
    const hasta = cambios.filter((c) => pasa(c, { fase: false }));
    const filasFase = C.map((c, ci) => {
      const cs = hasta.filter((x) => x.ci === ci);
      const l = cs.filter((x) => x.fase === "lic").length;
      return { concesion: c.nombre, [LIC]: l, [CON]: cs.length - l };
    });
    const sel = S.conc < 0 ? hasta : hasta.filter((c) => c.ci === S.conc);
    const lic = sel.filter((c) => c.fase === "lic").length;
    const specF = { height: ALTO_G,
      type: "bar", data: filasFase, x: "concesion", y: [LIC, CON], stack: true, horizontal: true, sort: "none",
      colors: { [LIC]: AZUL, [CON]: GRIS }, format: "integer", locale: "es", padding: [8, 16, 8, 12],
      title: sel.length ? `En ${alcance()}, ${Math.round((lic / sel.length) * 10)} de cada 10 ${palabra()} se hacen antes de adjudicar` : "Sin cambios con estos filtros",
      subtitle: "Las cinco, para comparar",
    };
    if (S.fase !== "todas") specF.highlight = S.fase === "lic" ? LIC : CON;
    dibujar("g-fases", specF);
    detalle("#d-fases", "Cuándo se adjudicó cada concesión", C.map((c, ci) => ({ c, ci })).map(({ c, ci }) => {
      const adj = c.actos[c.adj] || ["sin decreto de adjudicación", "", ""];
      const cs = hasta.filter((x) => x.ci === ci);
      const nActos = (f) => new Set(cs.filter((x) => x.fase === f).map((x) => x.acto)).size;
      const l = cs.filter((x) => x.fase === "lic").length;
      return fila(`fase|${ci}`, c.color, `<b>${esc(c.nombre)}</b> · ${esc(adj[0])} ${adj[1] ? `(${esc(adj[1])})` : ""}`,
        `${l} lic. · ${cs.length - l} contr.`,
        `<p>Licitación: ${l} ${palabra()} en ${nActos("lic")} actos. Contrato: ${cs.length - l} en ${nActos("con")} actos.</p>
         <p class="quien">Actos de la concesión: ${c.actos.length}. Bases: ${esc(c.actos[0]?.[1] || "")}.</p>`);
    }));

    const visC = C.map((_, ci) => ci).filter((ci) => S.conc < 0 || ci === S.conc);
    const porConc = (k, f) => Object.fromEntries(visC.map((ci) => [C[ci].nombre, B.m[k].filter((g) => A.c[g] === ci).reduce((s, g) => s + f(g), 0)]));

    // 5 · más citados, por artículo de la base (entre artículos, o desde actos hasta el año y la fase elegidos)
    const totCit = B.m.map((ms) => ms.filter(visible).reduce((s, g) => s + metricaCita(g), 0));
    const topCit = [...totCit.keys()].filter((k) => totCit[k] > 0).sort((a, b) => totCit[b] - totCit[a]).slice(0, 10);
    topCitG = topCit;
    // ¿en cuántas concesiones su artículo es el más citado?
    const lider = visC.map((ci) => { let m = -1; for (let g = 0; g < N; g++) if (A.c[g] === ci && (m < 0 || metricaCita(g) > metricaCita(m))) m = g; return m; });
    const primeras = topCit.length ? lider.filter((g) => g >= 0 && A.base[g] === topCit[0]).length : 0;
    const actosQueCitan = (g) => A.ca[g].filter(([k]) => pasaActo(A.c[g], k)).sort((x, y) => y[1] - x[1]);
    // entre artículos: dos barras por artículo, su PageRank en las Bases originales y hoy (las citas nuevas entran después)
    const red = S.citas === "red", ANTES = "Bases originales", HOY = "Vigente";
    const prDe = (k, f) => B.m[k].filter(visible).reduce((s, g) => s + f(g), 0);
    const ganan = red ? topCit.filter((k) => prDe(k, (g) => A.pr[g]) > prDe(k, (g) => (A.nuevo?.[g] ? 0 : PR0[g])) + 1e-6).length : 0;
    dibujar("g-citas", topCit.length ? { height: red ? ALTO_PAR2 : ALTO_G,
      type: "bar", horizontal: true, sort: "none", stack: !red, format: red ? "percent" : "integer", locale: "es", padding: [8, 16, 8, 12],
      data: topCit.map((k) => ({ articulo: rotuloBase(k), ...(red
        ? { [ANTES]: prDe(k, (g) => (A.nuevo?.[g] ? 0 : PR0[g])), [HOY]: prDe(k, (g) => A.pr[g]) }
        : porConc(k, (g) => citasActos(g))) })),
      x: "articulo", y: red ? [ANTES, HOY] : visC.map((ci) => C[ci].nombre), colors: red ? { [ANTES]: GRIS, [HOY]: AZUL } : COLORES, legend: red ? "top" : false,
      title: S.conc < 0
        ? `${tituloBase(topCit[0])} es el más citado: el primero en ${primeras === visC.length ? "las cinco" : `${primeras} de ${visC.length}`} concesiones`
        : `${tituloBase(topCit[0])} es el más citado en ${alcance()}`,
      subtitle: red
        ? `PageRank en la red de citas entre artículos, en las Bases originales y hoy · ${ganan} de los ${topCit.length} ganan peso`
        : `Citas desde actos posteriores${S.fase !== "todas" ? (S.fase === "lic" ? " de la licitación" : " del contrato") : ""}`,
    } : { type: "kpi", items: [{ label: "Citas con estos filtros", value: 0 }] });
    detalle("#d-citas", S.conc < 0 ? "Quién cita a cada uno, concesión por concesión" : "Quién cita a cada uno", topCit.map((k) => fila(`cit|${k}|${S.citas}`, null,
      `<b>${esc(tituloBase(k))}</b>${S.conc < 0 ? ` <span class="quien">${esc(numsBase(k))}</span>` : ""}`,
      `${((n) => `${n} ${n === 1 ? "cita" : "citas"}`)(B.m[k].filter(visible).reduce((s, g) => s + (A.ci?.[g] ?? 0), 0))} · ${B.m[k].filter(visible).reduce((s, g) => s + citasActos(g), 0)} desde actos`,
      (S.conc >= 0 && otrosBase(k) ? `<p class="quien">${esc(may(otrosBase(k)))}</p>` : "") + B.m[k].filter(visible).map((g) => {
        const ac = actosQueCitan(g);
        return `<h3>${chipArt(g)}</h3>
          <p class="quien">${repartoCitas(g)}</p>
          ${lista(A.entra[g].slice().sort((a, b) => A.pr[b] - A.pr[a]), 10)}
          <ul>${ac.slice(0, 6).map(([kk, n]) => `<li><span class="fase ${faseDe(A.c[g], kk)}">${nombreFase(faseDe(A.c[g], kk))}</span> <b>${esc(C[A.c[g]].actos[kk]?.[0] || "")}</b> · ${esc(C[A.c[g]].actos[kk]?.[1] || "")} · ${n} ${n === 1 ? "cita" : "citas"}</li>`).join("") || `<li class="quien">Ningún acto posterior lo cita con estos filtros</li>`}</ul>`;
      }).join(""))));

    // 6 · antes y después: el ranking de citas en las Bases originales y hoy
    const { hoy, p0, p1 } = puestos(S.conc);
    const enRank = [...new Set([...hoy.slice(0, 10), ...[...p0].filter(([, i]) => i <= 10).map(([g]) => g)])];
    topAdC = enRank;
    const rot = (g) => `${A.num[g]} ${corto(A.t[g], 30)}`;
    const subieron = enRank.filter((g) => p0.get(g) == null || p0.get(g) > p1.get(g)).length;
    dibujar("g-ad-citas", {
      type: "slope", x: "estado", y: "peso", series: "articulo", locale: "es", height: ALTO_G, top: 10, padding: [8, 8, 8, 28],
      data: enRank.flatMap((g) => [
        ...(p0.has(g) ? [{ estado: "Bases originales", articulo: rot(g), peso: PR0[g] }] : []),
        { estado: "Vigente", articulo: rot(g), peso: A.pr[g] }]),
      title: subieron ? `${subieron} de los más citados de ${alcance()} suben desde las Bases originales` : `Los más citados de ${alcance()} son los mismos que en las Bases`,
      subtitle: `Puesto en el PageRank de la red de citas entre artículos, sin y con las ${fmt(NUEVA.reduce((s, l, g) => s + (A.c[g] === S.conc ? l.length : 0), 0))} citas que nacen en actos posteriores`,
    });
    detalle("#d-ad-citas", "Las citas que nacen después de las Bases", gsDe(S.conc).filter((g) => NUEVA[g].length).map((g) => fila(`adc|${g}`, null,
      `<b>${esc(A.num[g])}</b> ${esc(corto(A.t[g], 50))}`, `${NUEVA[g].length} ${NUEVA[g].length === 1 ? "cita nueva" : "citas nuevas"}`,
      `<p>${chipArt(g)} ahora cita a:</p>${lista(NUEVA[g], 10)}`)), "Ningún artículo gana citas a otros artículos después de las Bases.");

    // 7 · antes y después: el texto de los artículos que más cambian de largo
    const ad = antesDespues(S.conc);
    const viejos = ad ? ad.l.filter(([, x]) => !x.nuevo && !x.dudoso) : [];
    const topT = viejos.slice().sort((a, b) => Math.abs(b[1].w1 - b[1].w0) - Math.abs(a[1].w1 - a[1].w0)).slice(0, 10);
    topAdT = topT.map(([g]) => g);
    dibujar("g-ad-texto", topT.length ? { height: ALTO_G,
      type: "bar", horizontal: true, sort: "none", format: "integer", locale: "es", padding: [8, 16, 8, 12], legend: "top",
      data: topT.map(([g, x]) => ({ articulo: rot(g), "Bases originales": x.w0, "Vigente": x.w1 })),
      x: "articulo", y: ["Bases originales", "Vigente"], colors: { "Bases originales": GRIS, "Vigente": AZUL },
      title: `${fmt(ad.n)} artículos de ${alcance()} cambian su texto: de ${fmt(ad.w0)} a ${fmt(ad.w1)} palabras`,
      subtitle: "Palabras en las Bases originales y vigentes: los 10 que más cambian",
    } : { type: "kpi", items: [{ label: "Artículos que cambian su texto", value: 0 }] });
    detalle("#d-ad-texto", "Su texto antes y después", topT.map(([g, x]) => fila(`adt|${g}`, null,
      `<b>${esc(A.num[g])}</b> ${esc(corto(A.t[g], 46))}`, `${fmt(x.w0)} → ${fmt(x.w1)} · φ ${coma(x.phi)}`,
      `<p>${chipArt(g)} ${balance(x)}</p>${x.partes.filter(([, a]) => a.d.length).map(([id, a]) => `${x.partes.length > 1 ? `<h4>${esc(id.replace(/^[^:]*:/, ""))}</h4>` : ""}<div class="diff">${diffHTML(a.d)}</div>`).join("")}`)),
      AD ? "Ningún artículo cambia su texto." : "Falta visor/antes_despues.js: corre python3 scripts/04_antes_despues.py.");
  }

  // ---------- la licitación: de qué tratan sus Bases, cómo se citan y cuánto se parecen a las otras (sin filtros de cambios)
  const ordenCom = COM.map((_, i) => i).sort((a, b) => COM[b].n - COM[a].n);
  const GRIS_PAREJO = "#9aa0b4", PAREJO = "Reparto parejo";
  const COLOR_OTRAS = { "En las otras cuatro": "#2b2d7a", "En tres": "#4f58c4", "En dos": "#8a90dc", "En una": "#c3c7ee", "Propio": "#e0a030" };
  function licitacion() {
    const ci = S.conc, nombre = C[ci].nombre, gs = gsDe(ci);
    // 1 · de qué tratan: la parte de los artículos de cada concesión en cada comunidad de contenido
    const pc = C.map((_, k) => porComunidad(k));
    const mia = pc[ci].map((l, i) => [i, l.length]).sort((x, y) => y[1] - x[1])[0];
    dibujar("g-com", {
      type: "heatmap", locale: "es", format: "percent", x: "concesion", y: "comunidad", value: "parte",
      data: ordenCom.flatMap((i) => C.map((c, k) => ({ concesion: c.cod, comunidad: COM[i].t, parte: pc[k][i].length / C[k].n, "Artículos": `${c.nombre}: ${pc[k][i].length} de ${C[k].n}` }))),
      tooltip: ["Artículos"],
      title: `En ${nombre}, ${COM[mia[0]].t.toLowerCase()} reúne el ${pct(mia[1] / gs.length)} de los artículos`,
      subtitle: "% de los artículos de cada concesión en cada comunidad de contenido · las cinco, para comparar",
    });
    detalle("#d-com", `Las comunidades de ${esc(nombre)}`, ordenCom.filter((i) => pc[ci][i].length).map((i) => fila(`com|${ci}|${i}`, colorCom(i),
      `<b>${esc(COM[i].t)}</b>`, `${pc[ci][i].length} · ${pct(pc[ci][i].length / gs.length)}`,
      `<p class="quien">Por ejemplo: ${esc(COM[i].ej.join(" · "))}</p>${lista(pc[ci][i].slice().sort((x, y) => citasRec(y) - citasRec(x)), 12)}`)));

    // 2 · cómo se citan: curva de concentración de las citas recibidas
    const co = C.map((_, k) => concentracion(k));
    const specConc = {
      type: "line", locale: "es", x: "articulos", y: "citas", series: "concesion", format: "percent", yDomain: [0, 1], height: ALTO_G,
      data: [...C.flatMap((c, k) => co[k].curva.map(([p, v]) => ({ articulos: String(p), concesion: c.nombre, citas: v }))),
        ...PCTS.map((p) => ({ articulos: String(p), concesion: PAREJO, citas: p / 100 }))],
      colors: { ...COLORES, [PAREJO]: GRIS_PAREJO }, highlight: [nombre, PAREJO], legend: "top",
      xLabel: "% de los artículos, del más citado al menos",
      title: `En ${nombre}, el 10 % más citado recibe el ${pct(co[ci].top10)} de las citas`,
      subtitle: "% acumulado de las citas recibidas entre artículos · la diagonal sería un reparto parejo",
    };
    dibujar("g-conc", specConc);
    igualarAlto("g-conc", "g-com", specConc);           // la curva mide lo mismo que el mapa de calor de al lado
    detalle("#d-conc", "Concentración de las citas en cada concesión", C.map((c, k) => fila(`conc|${k}`, c.color, `<b>${esc(c.nombre)}</b>`,
      `10 % → ${pct(co[k].top10)} · Gini ${coma(co[k].gini)}`,
      `<p class="quien">${fmt(co[k].tot)} citas entre ${fmt(co[k].n)} artículos; ${fmt(co[k].sinCitas)} no reciben ninguna. Los más citados:</p>${lista(gsDe(k).sort((x, y) => citasRec(y) - citasRec(x)), 8)}`)));

    // 3 · cuánto se parecen: en cuántas de las otras concesiones tiene equivalente cada artículo
    const pl = C.map((_, k) => plantilla(k));
    dibujar("g-plantilla", {
      type: "bar", horizontal: true, stack: "percent", sort: "none", locale: "es", height: S.citas === "red" ? ALTO_PAR2 : ALTO_G, padding: [8, 16, 8, 12], legend: "top",
      data: C.map((c, k) => ({ concesion: c.nombre, ...Object.fromEntries(EN_OTRAS.map((e) => [e, pl[k][e].length])) })),
      x: "concesion", y: EN_OTRAS, colors: COLOR_OTRAS,
      title: `El ${pct(pl[ci]["En las otras cuatro"].length / gs.length)} de los artículos de ${nombre} tiene equivalente en las otras cuatro; el ${pct(pl[ci].Propio.length / gs.length)} es propio`,
      subtitle: "Artículos según en cuántas de las otras concesiones tienen un equivalente recíproco (φ ≥ 0,5)",
    });
    detalle("#d-plantilla", `Los artículos de ${esc(nombre)}, según sus equivalentes`, EN_OTRAS.filter((e) => pl[ci][e].length).map((e) => fila(`pl|${ci}|${e}`, COLOR_OTRAS[e],
      `<b>${esc(e === "Propio" ? "Propios de esta concesión" : `Con equivalente ${e.toLowerCase()}`)}</b>`, `${pl[ci][e].length} · ${pct(pl[ci][e].length / gs.length)}`,
      lista(pl[ci][e].slice().sort((x, y) => citasRec(y) - citasRec(x)), 14))));
  }

  // ---------- qué pasa cuando se modifica: qué artículos cambian (con los filtros de fase y tipo)
  function modificaciones() {
    const ci = S.conc, nombre = C[ci].nombre;
    const cambia = (g) => cuenta(g) > 0;
    // 1 · por comunidad: qué parte de sus artículos cambia, en cada concesión
    const pc = C.map((_, k) => porComunidad(k));
    // relativo: cuántas veces el promedio de su concesión (1× = igual que el resto de las Bases de esa concesión)
    const base = pc.map((x) => parte(x.flat(), cambia));
    const total = parte(pc.flat(2), cambia);
    const rel = (v, b) => (v == null || !b ? null : v / b);
    const veces = (v) => `${v.toFixed(1).replace(".", ",")}×`;
    const junta = ordenCom.map((i) => { const l = pc.flatMap((x) => x[i]); return [i, rel(parte(l, cambia), total), l.length]; }).filter(([, v, n]) => v != null && n >= 30).sort((a, b) => b[1] - a[1]);   // el titular, sin las comunidades chicas
    dibujar("g-mod-com", junta.length ? {
      type: "heatmap", locale: "es", format: veces, midpoint: 1, legend: false, x: "concesion", y: "comunidad", value: "relativo",
      data: ordenCom.flatMap((i) => C.map((c, k) => {
        const l = pc[k][i], n = l.filter(cambia).length;
        return { concesion: c.cod, comunidad: COM[i].t, relativo: l.length ? rel(n / l.length, base[k]) : null,
          "Artículos": `${c.nombre}: ${n} de ${l.length} con ${queCambios()} (${pct(l.length ? n / l.length : 0)}; en toda la concesión, ${pct(base[k] ?? 0)})` };
      })),
      tooltip: ["Artículos"], missing: "plain",
      title: `En las cinco, ${junta[0] ? COM[junta[0][0]].t.toLowerCase() : "—"} se modifica ${junta[0] ? veces(junta[0][1]) : ""} lo habitual y ${COM[junta[junta.length - 1][0]].t.toLowerCase()}, solo ${veces(junta[junta.length - 1][1])}`,
      subtitle: `Cuántas veces cambia cada comunidad respecto del promedio de su concesión: 1× es igual, rosado cambia más, azul cambia menos · el titular compara las comunidades con 30 artículos o más · un clic en una celda la resalta en el mapa`,
    } : { type: "kpi", items: [{ label: `Artículos con ${queCambios()}`, value: 0 }] });
    detalle("#d-mod-com", `Qué cambió en cada comunidad de ${esc(nombre)}`, ordenCom.filter((i) => pc[ci][i].length).map((i) => {
      const l = pc[ci][i], si = l.filter(cambia).sort((x, y) => cuenta(y) - cuenta(x));
      return fila(`mcom|${ci}|${i}|${S.fase}|${S.tipo}`, colorCom(i), `<b>${esc(COM[i].t)}</b>`, `${si.length} de ${l.length}${base[ci] ? ` · ${veces(si.length / l.length / base[ci])}` : ""}`,
        si.length ? si.map((g) => chipArt(g, ` · ${cuenta(g)}`)).join("") : `<span class="quien">Ninguno con ${esc(queCambios())}.</span>`);
    }));

    // 2 · por su lugar en las citas de las Bases originales: ¿cambian más los más citados?
    const qs = C.map((_, k) => cuartos(k));
    const juntos = CUARTOS.map((_, q) => parte(qs.flatMap((x) => x[q]), cambia) ?? 0);
    dibujar("g-mod-cent", {
      type: "bar", sort: "none", locale: "es", format: "percent", height: ALTO_G, padding: [8, 16, 8, 12], legend: "top",
      data: CUARTOS.map((t, q) => ({ cuarto: t, ...Object.fromEntries(C.map((c, k) => [c.nombre, parte(qs[k][q], cambia) ?? 0])) })),
      x: "cuarto", y: C.map((c) => c.nombre), colors: COLORES, highlight: nombre,
      title: juntos[0] > juntos[3]
        ? `Cambian más los más citados: el ${pct(juntos[0])} del cuarto más citado y el ${pct(juntos[3])} del menos citado, en las cinco`
        : `Los más citados no cambian más: el ${pct(juntos[0])} del cuarto más citado y el ${pct(juntos[3])} del menos citado, en las cinco`,
      subtitle: `% de los artículos con ${queCambios()}, por su lugar en las citas de las Bases originales (PageRank)`,
    });
    detalle("#d-mod-cent", `Qué cambió en ${esc(nombre)}, por su lugar en las citas`, CUARTOS.map((t, q) => {
      const l = qs[ci][q], si = l.filter(cambia).sort((x, y) => cuenta(y) - cuenta(x));
      return fila(`mcent|${ci}|${q}|${S.fase}|${S.tipo}`, null, `<b>${esc(t)}</b>`, `${si.length} de ${l.length} · ${pct(si.length / Math.max(1, l.length))}`,
        si.length ? si.map((g) => chipArt(g, ` · ${cuenta(g)}`)).join("") : `<span class="quien">Ninguno con ${esc(queCambios())}.</span>`);
    }));
  }

  // clics en los gráficos: leemos el primer renglón del data-tip de plotagents (o la clave de la leyenda)
  function clic(id, fn) {
    document.getElementById(id).addEventListener("click", (e) => {
      const key = e.target.closest(".pa-key[data-value]");
      const m = e.target.closest("[data-tip]");
      const lineas = m ? m.getAttribute("data-tip").split("\n") : [];
      const texto = e.target.closest("text")?.textContent?.trim();
      if (fn({ key: key?.getAttribute("data-value"), lineas, texto }) !== false) { e.stopPropagation(); e.preventDefault(); }
    }, true);
  }
  const verDetalle = (id) => document.getElementById(id).scrollIntoView({ behavior: "smooth", block: "nearest" });
  clic("g-anios", ({ key, lineas }) => {
    if (key && key in PORNOMBRE) return ponerConc(PORNOMBRE[key]);
    const t = lineas.find((l) => /^\d+$/.test(l.trim()));   // el año desde las Bases (0, 1, 2…)
    if (t == null) return false;
    const a = +t;
    S.verAnio = S.verAnio === a ? null : a;
    todo(); verDetalle("d-anios");
  });
  clic("g-fases", ({ key, lineas, texto }) => {
    if (key === LIC || key === CON) return ponerFase(key === LIC ? "lic" : "con");
    const ci = PORNOMBRE[lineas[0] ?? texto];
    if (ci == null) return false;
    if (lineas.length === 2) {                       // un tramo: concesión + fase
      S.fase = lineas[1].startsWith(LIC) ? "lic" : "con";
      S.conc = ci; S.verAnio = null;
      if (S.sel != null && !visible(S.sel)) { S.sel = null; S.cambio = null; }
      return todo();
    }
    return ponerConc(ci);
  });
  // un tramo de un ranking (artículo de la base + concesión) abre ese artículo; la barra entera, el que más pesa
  const clicRanking = (lista) => ({ lineas, texto }) => {
    const txt = (lineas[0] || texto || "").trim();
    if (!txt) return false;
    const base = txt.replace(/…$/, "");
    const k = lista().find((x) => rotuloBase(x) === txt) ?? lista().find((x) => rotuloBase(x).startsWith(base));
    if (k == null) return false;
    const ci = lineas.length === 2 ? PORNOMBRE[lineas[1].split(":")[0]] : undefined;
    const ms = B.m[k].filter(visible);
    const g = (ci != null ? ms.find((x) => A.c[x] === ci) : null) ?? ms.slice().sort((a, b) => cuenta(b) - cuenta(a))[0] ?? B.m[k][0];
    seleccionar(g); irAlMapa();
  };
  // antes y después: el rótulo es «num título» de un artículo de la concesión elegida
  const clicArt = (lista) => ({ lineas, texto }) => {
    const txt = (lineas[0] || texto || "").trim().replace(/…$/, "");
    if (!txt) return false;
    const g = lista().find((x) => `${A.num[x]} ${corto(A.t[x], 30)}`.startsWith(txt) || txt.startsWith(`${A.num[x]} `));
    if (g == null) return false;
    seleccionar(g); irAlMapa();
  };
  // un clic en una celda de comunidades (o en una serie de concesión) lleva a esa concesión y resalta la comunidad
  const nombreEn = (t, nombres) => nombres.filter((n) => t.includes(n)).sort((a, b) => b.length - a.length)[0];
  const clicConcCom = ({ key, lineas, texto }) => {
    const t = [key, ...lineas, texto].filter(Boolean).join("\n");
    const nc = nombreEn(t, Object.keys(PORNOMBRE)), nm = nombreEn(t, COM.map((c) => c.t));
    if (nc == null && nm == null) return false;
    if (nc != null && PORNOMBRE[nc] !== S.conc) { S.conc = PORNOMBRE[nc]; S.verAnio = null; if (S.sel != null && !visible(S.sel)) { S.sel = null; S.cambio = null; } }
    if (nm != null) { ponerCom(COM.findIndex((c) => c.t === nm), true); irAlMapa(); return; }
    todo();
  };
  clic("g-com", clicConcCom);
  clic("g-mod-com", clicConcCom);
  clic("g-conc", clicConcCom);
  clic("g-plantilla", clicConcCom);
  clic("g-mod-cent", clicConcCom);
  clic("g-ad-citas", clicArt(() => topAdC));
  clic("g-ad-texto", clicArt(() => topAdT));
  clic("g-citas", clicRanking(() => topCitG));

  // ---------- todo junto
  let tGraf = 0;
  function todo(conGraficos = true) {
    concs.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.c === S.conc)));
    for (const [id, v] of [["#modo-citas", S.citas], ["#conexiones", lineasEf()], ["#mapa-color", colorEf()], ["#mapa-vista", S.vista]]) {
      $(id).querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.k === v)));
    }
    // sin los cambios encima, el mapa no ofrece colores ni líneas que dependan de ellos
    $("#mapa-color").querySelectorAll("button").forEach((b) => (b.hidden = !conCambios() && !COLOR_BASES.has(b.dataset.k)));
    pintarActivos();
    pintarMapa();
    pintarFicha();
    if (conGraficos) graficos(); else { clearTimeout(tGraf); tGraf = setTimeout(graficos, 250); }
    escribirURL();
  }

  // la barra de controles es pegajosa y cambia de alto: la ficha se ubica justo debajo
  const barra = document.querySelector(".controles");
  new ResizeObserver(() => document.documentElement.style.setProperty("--alto-controles", `${barra.offsetHeight}px`)).observe(barra);

  function desdeURL() { leerURL(); todo(); }
  desdeURL();
})();
