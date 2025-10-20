// blog_src/assets/js/custom/accordion.js
// Аккордеон секций поста из H2 + последующих узлов.
// Полная версия без “кракозябр”, UTF-8 (без BOM).

document.addEventListener("DOMContentLoaded", function () {
  const postContent = document.querySelector(".post-content");
  if (!postContent) return;

  // Собираем секции: H2 + тело до следующего H2
  const nodes = Array.from(postContent.children);
  const sections = [];
  let cur = null;

  nodes.forEach(node => {
    if (node.tagName === "H2") {
      if (cur) sections.push(cur);
      cur = { h: node, body: [] };
    } else if (cur) {
      cur.body.push(node);
    }
  });
  if (cur) sections.push(cur);
  if (sections.length < 2) return;

  // Очищаем и будем рендерить аккордеон
  postContent.innerHTML = "";

  // Настройки
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const SCROLL_OFFSET = parseInt(
    getComputedStyle(document.documentElement).getPropertyValue("--accordion-offset")
  ) || 96;

  // Утилиты
  const badge = (status) => {
    // Возвращаем span с иконкой и текстом статуса
    const span = document.createElement("span");
    span.className = "read-badge" + (status === "reading" ? " active" : "");
    if (status === "reading") {
      span.innerHTML =
        '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8"></circle></svg>READING';
    } else if (status === "toread") {
      span.innerHTML =
        '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="2"></rect></svg>NEXT';
    } else {
      span.innerHTML =
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>READ';
    }
    return span;
  };

  const openSection = (wrapper, content, header) => {
    wrapper.classList.add("open");
    wrapper.dataset.status = "reading";
    header.dataset.status = "reading";
    header.setAttribute("aria-expanded", "true");

    // Пересчёт высоты с анимацией (или без)
    if (prefersReduced) {
      content.style.maxHeight = content.scrollHeight + "px";
      wrapper.scrollIntoView({ behavior: "instant", block: "start" });
    } else {
      content.style.maxHeight = "0px";
      // force reflow
      // eslint-disable-next-line no-unused-expressions
      content.offsetHeight;
      content.style.maxHeight = content.scrollHeight + "px";
      const scrollAfter = () =>
        wrapper.scrollIntoView({ behavior: "smooth", block: "start" });
      content.addEventListener("transitionend", scrollAfter, { once: true });
    }
  };

  const closeSection = (wrapper) => {
    wrapper.classList.remove("open");
    wrapper.dataset.status = "read";
    const c = wrapper.querySelector(".accordion-content");
    const hdr = wrapper.querySelector(".accordion-header");
    if (c) c.style.maxHeight = "0px";
    if (hdr) {
      hdr.dataset.status = "read";
      hdr.setAttribute("aria-expanded", "false");
    }
  };

  // Рендер секций
  sections.forEach((sec, idx) => {
    // Генерируем section
    const wrapper = document.createElement("section");
    wrapper.className = "accordion-section" + (idx === 0 ? " open" : "");
    wrapper.dataset.status = idx === 0 ? "reading" : "toread";
    wrapper.style.scrollMarginTop = SCROLL_OFFSET + "px";

    // Заголовок-кнопка
    const header = document.createElement("button");
    header.type = "button";
    header.className = "accordion-header";
    header.setAttribute("aria-expanded", idx === 0 ? "true" : "false");
    header.dataset.status = wrapper.dataset.status;

    // Бейдж + текст заголовка
    header.appendChild(badge(wrapper.dataset.status));

    const title = document.createElement("span");
    title.className = "accordion-title";
    title.textContent = sec.h.textContent;
    header.appendChild(title);

    // Контент
    const content = document.createElement("div");
    content.className = "accordion-content";
    content.style.overflow = "hidden";
    content.style.transition = "max-height 320ms cubic-bezier(.2,.7,.3,1)";
    content.style.maxHeight = "0px";
    sec.body.forEach(el => content.appendChild(el));

    // Вставка рекламного блока сразу после первой секции (отключено)
    // if (idx === 0) {
    //   const aff = document.createElement("div");
    //   aff.innerHTML = `
    //     <div data-aff-rotator
    //          data-json="/aff/aff-cards.json"
    //          data-img-base="/aff/img/88"
    //          data-img-base2x="/aff/img/176"
    //          data-mode="random"
    //          data-count="1"></div>
    //   `;
    //   content.appendChild(aff);

    //   // Инициализация ротатора
    //   const runAff = () => {
    //     if (window.affRotatorRun) window.affRotatorRun();
    //     else if (window.runAffRotator) window.runAffRotator();
    //     else {
    //       const script = document.createElement("script");
    //       script.src = new URL("/aff/aff-rotator.js", window.location.origin).href;
    //       script.async = true;
    //       script.onload = () => {
    //         if (window.affRotatorRun) window.affRotatorRun();
    //         else if (window.runAffRotator) window.runAffRotator();
    //       };
    //       document.body.appendChild(script);
    //     }
    //   };
    //   try { runAff(); } catch (e) { /* no-op */ }

    //   // Страховочный пересчёт высоты, пока баннер дорисовывается (отключён)
    //   // const fixHeight = setInterval(() => {
    //   //   if (wrapper.classList.contains("open")) {
    //   //     const h = content.scrollHeight;
    //   //     if (h > parseInt(content.style.maxHeight || "0", 10)) {
    //   //       content.style.maxHeight = h + "px";
    //   //     }
    //   //   }
    //   // }, 300);
    //   // setTimeout(() => clearInterval(fixHeight), 3000);
    // }


    // Начальное открытие первой секции
    requestAnimationFrame(() => {
      if (idx === 0) {
        wrapper.classList.add("open");
        content.style.maxHeight = content.scrollHeight + "px";
      }
    });

    // Обработчик клика
    header.addEventListener("click", () => {
      const willOpen = !wrapper.classList.contains("open");

      // Закрыть все прочие
      postContent.querySelectorAll(".accordion-section.open").forEach(secEl => {
        if (secEl !== wrapper) closeSection(secEl);
      });

      // Обновить бейджи на всех хедерах
      postContent.querySelectorAll(".accordion-header").forEach(hdr => {
        const b = hdr.querySelector(".read-badge");
        const st = hdr.dataset.status;
        if (!b) return;
        // перерисуем бейдж
        const replacement = badge(st || "read");
        b.replaceWith(replacement);
      });

      if (willOpen) {
        openSection(wrapper, content, header);
        // Бейдж активного
        const b = header.querySelector(".read-badge");
        if (b) b.replaceWith(badge("reading"));
      } else {
        closeSection(wrapper);
        const b = header.querySelector(".read-badge");
        if (b) b.replaceWith(badge("read"));
      }
    });

    // Наблюдатель за изменением размеров (изображения, ротатор, таблицы и т.п.)
    const ro = new ResizeObserver(() => {
      if (!wrapper.classList.contains("open")) return;
      content.style.maxHeight = content.scrollHeight + "px";
    });
    ro.observe(content);

    // Собираем DOM
    wrapper.appendChild(header);
    wrapper.appendChild(content);
    postContent.appendChild(wrapper);
  });

  // Deep-link: если #hash указывает на id H2 — откроем её секцию
  if (location.hash) {
    const id = decodeURIComponent(location.hash.slice(1));
    if (id) {
      const targetH2 = postContent.querySelector(`h2#${CSS.escape(id)}`);
      if (targetH2) {
        const targetSection = targetH2.closest(".accordion-section") ||
                              targetH2.parentElement; // на всякий случай
        const header = targetSection?.querySelector(".accordion-header");
        const content = targetSection?.querySelector(".accordion-content");
        if (targetSection && header && content) {
          // Закрыть прочие
          postContent.querySelectorAll(".accordion-section.open").forEach(secEl => {
            if (secEl !== targetSection) closeSection(secEl);
          });
          openSection(targetSection, content, header);
          const b = header.querySelector(".read-badge");
          if (b) b.replaceWith(badge("reading"));
        }
      }
    }
  }
});
