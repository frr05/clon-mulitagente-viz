// Barra y pie comunes del sitio. Se incluye al final del <body> con <script src=".../nav.js"></script> y su nav.css.
// - Barra (arriba, fija al hacer scroll): la marca y las secciones del tablero (Mapa, La licitación, Cuando se modifica,
//   Antes y después) más la página de temas de RITP. En el tablero, las secciones hacen scroll sin tocar el #hash
//   (el tablero guarda ahí su estado: #c=CN&f=lic&art=…) y la sección visible queda marcada. Desde otra página,
//   llevan a index.html?ir=<sección> (en la query, porque el tablero reescribe el hash al abrir).
// - Pie: logos de CATLEC y del Departamento de Ingeniería Industrial UdeC, los mismos enlaces y, si la página tiene
//   un <footer class="pie">, su texto (fuente de los datos, fecha), que se mueve adentro.
// Las rutas se resuelven desde la ubicación de este archivo: sirve igual en visor/ y en visor/matriz/, con o sin servidor.
(function () {
  const base = new URL(".", document.currentScript.src);
  const url = p => new URL(p, base).href;
  const SECCIONES = [            // [id del ancla en index.html, texto]
    ["el-mapa", "Mapa"],
    ["licitacion", "La licitación"],
    ["modifica", "Cuando se modifica"],
    ["antes-despues", "Antes y después"],
  ];
  const PAGINAS = [{ id: "temas", href: "matriz/index.html", t: "Temas de RITP" }];

  const limpia = s => decodeURI(new URL(s, location.href).pathname).replace(/index\.html$/, "");
  const enTablero = limpia(location.href) === limpia(url("index.html"));
  const actual = PAGINAS.find(p => limpia(url(p.href)) === limpia(location.href));
  const hrefSec = id => enTablero ? `#${id}` : `${url("index.html")}?ir=${id}`;

  const enlaces = cls => SECCIONES.map(([id, t]) => `<li><a class="${cls}" href="${hrefSec(id)}" data-sec="${id}">${t}</a></li>`).join("")
    + PAGINAS.map(p => `<li class="${cls}-pag"><a class="${cls}" href="${url(p.href)}"${p === actual ? ' aria-current="page"' : ""}>${p.t}</a></li>`).join("");

  // ---------- barra
  const nav = document.createElement("nav");
  nav.className = "sn";
  nav.setAttribute("aria-label", "Secciones del sitio");
  nav.innerHTML = `<a class="sn-marca" href="${url("index.html")}">Bases de Licitación <span>· cinco concesiones viales</span></a>
    <ul class="sn-lista">${enlaces("sn-a")}</ul>`;
  document.body.prepend(nav);

  // ---------- pie
  const pie = document.createElement("footer");
  pie.className = "sp";
  pie.innerHTML = `<div class="sp-marcas">
      <a href="https://catlec.cl/" target="_blank" rel="noopener"><img src="${url("logos/catlec.png")}" alt="CATLEC, Centro Avanzado de Transporte, Logística y Competitividad Económica" height="40" class="sp-catlec"></a>
      <a href="https://fi.udec.cl/facultad/departamentos/industrial/" target="_blank" rel="noopener"><img src="${url("logos/dii-udec.svg")}" alt="Departamento de Ingeniería Industrial, Universidad de Concepción" height="46" class="sp-dii"></a>
    </div>
    <div class="sp-texto">
      <p class="sp-quien"><b>Bases de Licitación · cinco concesiones viales</b><br>Centro Avanzado de Transporte, Logística y Competitividad Económica (CATLEC) y Departamento de Ingeniería Industrial, Universidad de Concepción.</p>
      <ul class="sp-lista" aria-label="Secciones">${enlaces("sp-a")}</ul>
      <p class="sp-fuente"></p>
    </div>`;
  const viejo = document.querySelector("footer.pie");
  if (viejo) { pie.querySelector(".sp-fuente").append(...viejo.childNodes); viejo.remove(); }
  else pie.querySelector(".sp-fuente").remove();
  document.body.append(pie);

  // si el body ya tiene margen lateral propio (el tablero), barra y pie no agregan otro;
  // si tiene margen arriba o abajo, la barra sube hasta el borde de la ventana y el pie baja hasta el final
  const cs = getComputedStyle(document.body);
  if (parseFloat(cs.paddingLeft) >= 16) { nav.style.setProperty("--sn-pad", "0px"); pie.style.setProperty("--sn-pad", "0px"); }
  if (parseFloat(cs.paddingTop) > 0) { nav.style.marginTop = `-${cs.paddingTop}`; nav.style.marginBottom = cs.paddingTop; }
  if (parseFloat(cs.paddingBottom) > 0) pie.style.marginBottom = `-${cs.paddingBottom}`;
  const alto = () => nav.offsetHeight;
  document.documentElement.style.setProperty("--sn-h", `${alto()}px`);

  if (!enTablero) return;

  // ---------- secciones del tablero: scroll sin tocar el hash, y la visible queda marcada
  const secs = SECCIONES.map(([id]) => document.getElementById(id)).filter(Boolean);
  const fijo = () => {                          // alto de lo que queda pegado arriba: la barra y los controles del tablero
    const c = document.querySelector(".controles");
    return alto() + (c && getComputedStyle(c).position === "sticky" ? c.offsetHeight : 0);
  };
  const ir = (id, suave = true) => {
    const el = document.getElementById(id); if (!el) return;
    const y = el.getBoundingClientRect().top + scrollY - fijo() - 12;
    scrollTo({ top: Math.max(0, y), behavior: suave && !matchMedia("(prefers-reduced-motion: reduce)").matches ? "smooth" : "auto" });
  };
  document.addEventListener("click", ev => {
    const a = ev.target.closest("a[data-sec]");
    if (!a || ev.metaKey || ev.ctrlKey || ev.shiftKey) return;
    ev.preventDefault(); ir(a.dataset.sec);
  });
  const marcar = () => {
    const lim = fijo() + Math.min(260, innerHeight * .3);   // la sección cuenta como visible si su título pasa este nivel
    let cur = null;
    for (const s of secs) if (s.getBoundingClientRect().top <= lim) cur = s.id;
    if (innerHeight + scrollY >= document.documentElement.scrollHeight - 4 && secs.length) cur = secs[secs.length - 1].id;
    nav.querySelectorAll("a[data-sec]").forEach(a => a.classList.toggle("on", a.dataset.sec === cur));
  };
  addEventListener("scroll", marcar, { passive: true });
  addEventListener("resize", marcar);
  marcar();

  // llegada desde otra página: index.html?ir=<sección>. Se quita de la URL y se salta a la sección.
  const q = new URLSearchParams(location.search), dest = q.get("ir");
  if (dest) {
    q.delete("ir");
    const h = q.toString();
    history.replaceState(null, "", location.pathname + (h ? `?${h}` : "") + location.hash);
    // espera a que los gráficos tomen su alto antes de saltar
    requestAnimationFrame(() => setTimeout(() => ir(dest, false), 150));
  }
})();
