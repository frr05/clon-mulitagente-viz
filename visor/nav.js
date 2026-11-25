// nav.js: barra superior y pie comunes a todas las páginas del visor (va con nav.css).
// Se carga al final del <body>. Arma:
//   · una barra fija de 48 px con la marca, las secciones del tablero (Mapa, La licitación, Cuando se modifica,
//     Antes y después) y la página «Temas de RITP»;
//   · un pie con los logos de CATLEC y del DII UdeC, los mismos enlaces y el texto del <footer class="pie"> de la
//     página (si existe), que se traslada adentro.
// En el tablero (index.html) los enlaces de sección hacen scroll sin tocar el #hash, porque ahí el tablero guarda su
// estado, y la sección visible queda marcada. En las demás páginas apuntan a index.html?ir=<sección>.
// Todas las rutas se calculan desde la carpeta de este archivo, así funciona en visor/ y en visor/matriz/.
(function () {
  "use strict";

  const raiz = new URL("./", document.currentScript.src);
  const enRaiz = ruta => new URL(ruta, raiz).href;

  const SECCIONES = [
    { id: "el-mapa", texto: "Mapa" },
    { id: "licitacion", texto: "La licitación" },
    { id: "modifica", texto: "Cuando se modifica" },
    { id: "antes-despues", texto: "Antes y después" },
  ];
  const PAGINAS = [{ id: "temas", ruta: "matriz/index.html", texto: "Temas de RITP" }];

  // compara rutas sin query ni hash y tratando «carpeta/» igual que «carpeta/index.html»
  const rutaComparable = href => decodeURI(new URL(href, location.href).pathname).replace(/index\.html$/, "");
  const aqui = rutaComparable(location.href);
  const esTablero = aqui === rutaComparable(enRaiz("index.html"));
  const paginaActual = PAGINAS.find(p => rutaComparable(enRaiz(p.ruta)) === aqui) || null;

  const destinoSeccion = id => (esTablero ? "#" + id : enRaiz("index.html") + "?ir=" + encodeURIComponent(id));

  function listaEnlaces(clase) {
    const secs = SECCIONES.map(s =>
      `<li><a class="${clase}" href="${destinoSeccion(s.id)}" data-sec="${s.id}">${s.texto}</a></li>`);
    const pags = PAGINAS.map(p => {
      const actual = p === paginaActual ? ' aria-current="page"' : "";
      return `<li class="${clase}-pag"><a class="${clase}" href="${enRaiz(p.ruta)}"${actual}>${p.texto}</a></li>`;
    });
    return secs.concat(pags).join("");
  }

  // ---------------------------------------------------------------- barra
  const barra = document.createElement("nav");
  barra.className = "sn";
  barra.setAttribute("aria-label", "Secciones del sitio");
  barra.innerHTML =
    `<a class="sn-marca" href="${enRaiz("index.html")}">Bases de Licitación <span>· cinco concesiones viales</span></a>` +
    `<ul class="sn-lista">${listaEnlaces("sn-a")}</ul>`;
  document.body.insertBefore(barra, document.body.firstChild);

  // ---------------------------------------------------------------- pie
  const pie = document.createElement("footer");
  pie.className = "sp";
  pie.innerHTML =
    `<div class="sp-marcas">` +
      `<a href="https://catlec.cl/" target="_blank" rel="noopener">` +
        `<img class="sp-catlec" src="${enRaiz("logos/catlec.png")}" height="40" ` +
        `alt="CATLEC, Centro Avanzado de Transporte, Logística y Competitividad Económica"></a>` +
      `<a href="https://fi.udec.cl/facultad/departamentos/industrial/" target="_blank" rel="noopener">` +
        `<img class="sp-dii" src="${enRaiz("logos/dii-udec.svg")}" height="46" ` +
        `alt="Departamento de Ingeniería Industrial, Universidad de Concepción"></a>` +
    `</div>` +
    `<div class="sp-texto">` +
      `<p class="sp-quien"><b>Bases de Licitación · cinco concesiones viales</b><br>` +
      `Centro Avanzado de Transporte, Logística y Competitividad Económica (CATLEC) y Departamento de Ingeniería ` +
      `Industrial, Universidad de Concepción.</p>` +
      `<ul class="sp-lista" aria-label="Secciones">${listaEnlaces("sp-a")}</ul>` +
      `<p class="sp-fuente"></p>` +
    `</div>`;

  const fuente = pie.querySelector(".sp-fuente");
  const pieDePagina = document.querySelector("footer.pie");
  if (pieDePagina) {
    while (pieDePagina.firstChild) fuente.appendChild(pieDePagina.firstChild);   // conserva nodos (p. ej. #generado)
    pieDePagina.parentNode.removeChild(pieDePagina);
  } else {
    fuente.parentNode.removeChild(fuente);
  }
  document.body.appendChild(pie);

  // Ajuste al margen del body: si ya trae margen lateral (el tablero), barra y pie no suman otro;
  // si trae margen arriba/abajo, la barra se pega al borde superior y el pie al inferior.
  const estiloBody = getComputedStyle(document.body);
  const px = v => parseFloat(v) || 0;
  if (px(estiloBody.paddingLeft) >= 16) {
    barra.style.setProperty("--sn-pad", "0px");
    pie.style.setProperty("--sn-pad", "0px");
  }
  if (px(estiloBody.paddingTop) > 0) {
    barra.style.marginTop = "-" + estiloBody.paddingTop;
    barra.style.marginBottom = estiloBody.paddingTop;
  }
  if (px(estiloBody.paddingBottom) > 0) pie.style.marginBottom = "-" + estiloBody.paddingBottom;

  const altoBarra = () => barra.offsetHeight;
  document.documentElement.style.setProperty("--sn-h", altoBarra() + "px");

  if (!esTablero) return;

  // ---------------------------------------------------------------- solo en el tablero
  const anclas = SECCIONES.map(s => document.getElementById(s.id)).filter(Boolean);

  // lo que queda pegado arriba: la barra y, si es sticky, la fila de controles del tablero
  function altoFijo() {
    const ctl = document.querySelector(".controles");
    const extra = ctl && getComputedStyle(ctl).position === "sticky" ? ctl.offsetHeight : 0;
    return altoBarra() + extra;
  }

  function irA(id, suave) {
    const destino = document.getElementById(id);
    if (!destino) return;
    const y = window.scrollY + destino.getBoundingClientRect().top - altoFijo() - 12;
    const animar = suave !== false && !matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: Math.max(0, y), behavior: animar ? "smooth" : "auto" });
  }

  document.addEventListener("click", ev => {
    if (ev.metaKey || ev.ctrlKey || ev.shiftKey) return;   // abrir en otra pestaña sigue funcionando
    const a = ev.target.closest && ev.target.closest("a[data-sec]");
    if (!a) return;
    ev.preventDefault();
    irA(a.getAttribute("data-sec"));
  });

  function marcarVisible() {
    // una sección está «activa» desde que su título cruza esta línea
    const linea = altoFijo() + Math.min(260, window.innerHeight * 0.3);
    let activa = null;
    anclas.forEach(el => { if (el.getBoundingClientRect().top <= linea) activa = el.id; });
    const alFinal = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4;
    if (alFinal && anclas.length) activa = anclas[anclas.length - 1].id;
    barra.querySelectorAll("a[data-sec]").forEach(a =>
      a.classList.toggle("on", a.getAttribute("data-sec") === activa));
  }
  window.addEventListener("scroll", marcarVisible, { passive: true });
  window.addEventListener("resize", marcarVisible);
  marcarVisible();

  // llegada desde otra página con ?ir=<sección>: se limpia la query y se salta sin animación
  const params = new URLSearchParams(location.search);
  const pedida = params.get("ir");
  if (pedida) {
    params.delete("ir");
    const resto = params.toString();
    history.replaceState(null, "", location.pathname + (resto ? "?" + resto : "") + location.hash);
    // se da un momento para que los gráficos del tablero tomen su alto
    // y se marca la sección enseguida, sin esperar al evento de scroll
    requestAnimationFrame(() => setTimeout(() => { irA(pedida, false); marcarVisible(); }, 150));
  }
})();
