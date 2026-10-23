// CogniShield protect page: three-step flow (upload → settings → result).
(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const PRESET_NAMES = { 4: "Subtle", 8: "Balanced", 14: "Strong" };
  const MAX_BYTES = 200 * 1024 * 1024;

  const state = { file: null, fileUrl: "", step: 1, maxStep: 1, busy: false, view: "wipe", result: null, sent: null };

  const els = {
    input: $("#image-input"),
    dropWrap: $("#drop-wrap"),
    dropzone: $("#dropzone"),
    dropEmpty: $("#drop-empty"),
    dropPreview: $("#drop-preview"),
    previewImage: $("#preview-image"),
    fileBar: $("#file-bar"),
    fileName: $("#file-name"),
    fileFacts: $("#file-facts"),
    settingsThumb: $("#settings-thumb"),
    settingsName: $("#settings-name"),
    form: $("#protection-form"),
    protectButton: $("#protect-button"),
    epsilon: $("#epsilon"),
    iterations: $("#iterations"),
    seed: $("#seed"),
    runModel: $("#run-model"),
    promptField: $("#prompt-field"),
    prompt: $("#prompt"),
    scanning: $("#scanning"),
    scanImage: $("#scan-image"),
    viewButtons: $$(".view-switch [data-view]"),
    wipe: $("#view-wipe"),
    wipeRange: $("#wipe-range"),
    wipeLegend: $("#wipe-legend"),
    report: $("#report"),
    toast: $("#toast"),
  };

  // ---------- Helpers ----------
  function h(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([key, value]) => {
      if (value === null || value === undefined) return;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else node.setAttribute(key, value);
    });
    children.flat().forEach((child) => {
      if (child === null || child === undefined) return;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    });
    return node;
  }

  function fmt(value, digits = 4) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
    return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  let toastTimer = 0;
  function toast(text, success = false) {
    els.toast.textContent = text;
    els.toast.className = `toast${success ? " is-success" : ""}`;
    els.toast.hidden = false;
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => { els.toast.hidden = true; }, 5000);
  }

  // ---------- Steps ----------
  function updateSteps() {
    $$(".step").forEach((button) => {
      const n = Number(button.dataset.go);
      button.disabled = n > state.maxStep || (state.busy && n !== 3);
      button.classList.toggle("is-done", n < state.step);
      if (n === state.step) button.setAttribute("aria-current", "step");
      else button.removeAttribute("aria-current");
    });
  }

  function go(step, { focus = true } = {}) {
    if (step > state.maxStep || (state.busy && step !== 3)) return;
    state.step = step;
    $$(".stage").forEach((stage) => { stage.hidden = Number(stage.dataset.stage) !== step; });
    updateSteps();
    window.scrollTo({ top: 0, behavior: reducedMotion.matches ? "auto" : "smooth" });
    if (focus) $(`.stage[data-stage="${step}"] [data-stage-title]`)?.focus({ preventScroll: true });
  }

  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-go]");
    if (target && !target.disabled) go(Number(target.dataset.go));
  });

  // ---------- Step 1: choose an image ----------
  function chooseFile(file) {
    if (!file || state.busy) return;
    if (!/^image\/(png|jpeg|webp)$/.test(file.type)) {
      toast("That file type isn't supported. Choose a PNG, JPG or WEBP image.");
      return;
    }
    if (file.size > MAX_BYTES) {
      toast("That image is larger than 200 MB. Choose a smaller file.");
      return;
    }
    if (state.fileUrl) URL.revokeObjectURL(state.fileUrl);
    state.file = file;
    state.fileUrl = URL.createObjectURL(file);

    els.previewImage.onload = () => {
      els.fileFacts.textContent = `${els.previewImage.naturalWidth} × ${els.previewImage.naturalHeight} px, ${formatBytes(file.size)}`;
    };
    els.previewImage.src = state.fileUrl;
    els.previewImage.alt = `Preview of ${file.name}`;
    els.settingsThumb.src = state.fileUrl;
    els.scanImage.src = state.fileUrl;
    els.fileName.textContent = file.name;
    els.settingsName.textContent = file.name;
    els.fileFacts.textContent = formatBytes(file.size);

    els.dropEmpty.hidden = true;
    els.dropPreview.hidden = false;
    els.dropzone.classList.add("has-image");
    els.dropzone.setAttribute("aria-label", `Replace ${file.name}`);
    els.fileBar.hidden = false;

    resetResult();
    state.maxStep = 2;
    updateSteps();
  }

  function clearFile() {
    if (state.fileUrl) URL.revokeObjectURL(state.fileUrl);
    state.file = null;
    state.fileUrl = "";
    els.input.value = "";
    els.previewImage.removeAttribute("src");
    els.dropEmpty.hidden = false;
    els.dropPreview.hidden = true;
    els.dropzone.classList.remove("has-image");
    els.dropzone.setAttribute("aria-label", "Choose an image to protect");
    els.fileBar.hidden = true;
    resetResult();
    state.maxStep = 1;
  }

  const openPicker = () => { if (!state.busy) els.input.click(); };
  $("#browse-button").addEventListener("click", (event) => { event.stopPropagation(); openPicker(); });
  $("#replace-image").addEventListener("click", openPicker);
  els.input.addEventListener("change", () => chooseFile(els.input.files[0]));
  els.dropzone.addEventListener("click", openPicker);
  els.dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openPicker(); }
  });
  ["dragenter", "dragover"].forEach((type) => els.dropzone.addEventListener(type, (event) => {
    event.preventDefault();
    els.dropWrap.classList.add("is-dragging");
  }));
  ["dragleave", "drop"].forEach((type) => els.dropzone.addEventListener(type, (event) => {
    event.preventDefault();
    els.dropWrap.classList.remove("is-dragging");
  }));
  els.dropzone.addEventListener("drop", (event) => chooseFile(event.dataTransfer.files[0]));

  // Paste an image from the clipboard while on the upload step.
  document.addEventListener("paste", (event) => {
    if (state.step !== 1 || state.busy) return;
    const file = Array.from(event.clipboardData?.files || []).find((item) => item.type.startsWith("image/"));
    if (!file) return;
    event.preventDefault();
    chooseFile(file.name && file.name !== "image.png" ? file : new File([file], "pasted-image.png", { type: file.type }));
  });

  // ---------- Step 2: settings ----------
  function syncRange(range) {
    const pct = ((range.value - range.min) / (range.max - range.min)) * 100;
    range.style.setProperty("--fill", `${pct}%`);
    const output = $(`#${range.id}-value`);
    if (output) output.value = range.value;
  }

  const presets = $$('input[name="preset"]');
  presets.forEach((radio) => radio.addEventListener("change", () => {
    els.epsilon.value = radio.value;
    syncRange(els.epsilon);
  }));
  els.epsilon.addEventListener("input", () => {
    syncRange(els.epsilon);
    presets.forEach((radio) => { radio.checked = radio.value === els.epsilon.value; });
  });
  els.iterations.addEventListener("input", () => syncRange(els.iterations));
  [els.epsilon, els.iterations].forEach(syncRange);

  const clampSeed = (value) => Math.max(0, Math.min(999999, Math.round(Number(value) || 0)));
  $$("[data-seed-step]").forEach((button) => button.addEventListener("click", () => {
    els.seed.value = clampSeed(Number(els.seed.value) + Number(button.dataset.seedStep));
  }));
  els.seed.addEventListener("change", () => { els.seed.value = clampSeed(els.seed.value); });

  els.runModel.addEventListener("change", () => { els.promptField.hidden = !els.runModel.checked; });

  // ---------- Step 3: protect and show the result ----------
  function showVerdict(kind) {
    ["working", "error", "done"].forEach((name) => { $(`#verdict-${name}`).hidden = name !== kind; });
  }

  function setView(view) {
    state.view = view;
    els.viewButtons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.view === view)));
    $$(".view").forEach((panel) => { panel.hidden = !state.result || state.busy || panel.dataset.viewPanel !== view; });
    els.wipeLegend.hidden = view !== "wipe" || !state.result || state.busy;
  }

  function setBusy(busy) {
    state.busy = busy;
    els.protectButton.disabled = busy;
    els.protectButton.textContent = busy ? "Protecting…" : "Protect image";
    els.scanning.hidden = !busy;
    els.scanning.classList.remove("is-stopped");
    els.viewButtons.forEach((button) => { button.disabled = busy || !state.result; });
    setView(state.view);
    updateSteps();
  }

  function resetResult() {
    state.result = null;
    els.report.hidden = true;
    showVerdict(null);
    els.scanning.hidden = true;
    setView("wipe");
    els.viewButtons.forEach((button) => { button.disabled = true; });
  }

  els.viewButtons.forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
  els.wipeRange.addEventListener("input", () => els.wipe.style.setProperty("--pos", `${els.wipeRange.value}%`));

  els.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (state.busy) return;
    if (!state.file) { go(1); toast("Choose an image first."); return; }

    const qualities = $$('input[name="qualities"]:checked').map((input) => input.value);
    const seed = clampSeed(els.seed.value);
    els.seed.value = seed;
    state.sent = { epsilon: Number(els.epsilon.value), qualities };

    const form = new FormData();
    form.append("image", state.file);
    form.append("epsilon", els.epsilon.value);
    form.append("iterations", els.iterations.value);
    form.append("seed", String(seed));
    form.append("run_model", String(els.runModel.checked));
    form.append("prompt", els.prompt.value);
    qualities.forEach((quality) => form.append("qualities", quality));

    state.result = null;
    els.report.hidden = true;
    $("#working-detail").textContent = els.runModel.checked
      ? "Generating the perturbation, testing JPEG compression, signing the result, then running SD-Turbo on both images. The model test can take a few minutes."
      : "Generating the perturbation, testing JPEG compression and signing the result. This usually takes a few seconds.";
    showVerdict("working");
    state.maxStep = 3;
    setBusy(true);
    go(3);

    try {
      let response;
      try {
        response = await fetch("/api/protect", { method: "POST", body: form });
      } catch (_) {
        throw new Error("Couldn't reach CogniShield. Check that app.py is still running, then try again.");
      }
      let data;
      try { data = await response.json(); } catch (_) {
        throw new Error(`The server sent an unexpected response (HTTP ${response.status}).`);
      }
      if (!response.ok) throw new Error(data.error || "The image couldn't be protected.");
      state.result = data;
      render(data);
      showVerdict("done");
      toast("Image protected and signed.", true);
    } catch (error) {
      $("#error-text").textContent = error.message;
      showVerdict("error");
    } finally {
      setBusy(false);
      if (!state.result) {
        els.scanning.hidden = false;
        els.scanning.classList.add("is-stopped");
      }
    }
  });

  function render(data) {
    $("#wipe-original").src = data.images.original;
    $("#wipe-protected").src = data.images.protected;
    $("#split-original").src = data.images.original;
    $("#split-protected").src = data.images.protected;
    $("#diff-image").src = data.images.difference;
    els.wipeRange.value = 50;
    els.wipe.style.setProperty("--pos", "50%");

    $("#download-protected").href = data.downloads.protected;
    $("#download-provenance").href = data.downloads.provenance;

    const valid = Boolean(data.provenance && data.provenance.valid);
    const sig = $("#sig-state");
    sig.textContent = valid ? "Signed and verified" : "Signature not verified";
    sig.className = `state ${valid ? "state-ok" : "state-warn"}`;

    const eps = state.sent.epsilon;
    $("#fact-strength").textContent = `${eps}/255${PRESET_NAMES[eps] ? ` ${PRESET_NAMES[eps]}` : ""}`;
    $("#fact-psnr").textContent = data.metrics.psnr === null ? "—" : `${fmt(data.metrics.psnr, 2)} dB`;
    $("#fact-ssim").textContent = fmt(data.metrics.ssim, 4);
    const ssims = (data.compression || []).map((row) => row.ssim).filter((v) => v !== null && v !== undefined);
    $("#fact-jpeg").textContent = ssims.length ? fmt(Math.min(...ssims), 4) : "—";

    // Quality
    const metrics = [
      ["PSNR", data.metrics.psnr, 2, "dB", "Above 40 dB is usually indistinguishable by eye."],
      ["SSIM", data.metrics.ssim, 4, "", "1.0 means structurally identical."],
      ["MSE", data.metrics.mse, 4, "", "Average squared pixel error. Lower is closer."],
      ["Mean change", data.metrics.mean_abs_delta, 4, "", "Average absolute change per pixel."],
      ["Max change", data.metrics.max_abs_delta, 4, "", "Largest single change. Capped by the budget."],
    ];
    $("#metrics-grid").replaceChildren(...metrics.map(([label, value, digits, unit, hint]) => h("div", { class: "metric" },
      h("span", { class: "metric-label", text: label }),
      h("span", { class: "metric-value" }, fmt(value, digits), unit && value !== null ? h("span", { class: "metric-unit", text: unit }) : null),
      h("span", { class: "metric-hint", text: hint }),
    )));

    // JPEG tests
    const rows = data.compression || [];
    $("#compression-body").replaceChildren(...(rows.length ? rows.map((row) => h("tr", {},
      h("td", { text: `Q${row.quality}` }),
      h("td", { text: row.psnr === null ? "—" : `${fmt(row.psnr, 2)} dB` }),
      h("td", {}, fmt(row.ssim, 4), h("span", { class: "bar", "aria-hidden": "true" },
        h("span", { style: `width:${Math.max(0, Math.min(1, Number(row.ssim) || 0)) * 100}%` }))),
      h("td", { text: fmt(row.mse, 4) }),
    )) : [h("tr", {}, h("td", { colspan: "4", text: "No JPEG tests were selected." }))]));

    // Inspection images
    const inspect = [
      { url: data.images.difference, caption: "Difference ×12", alt: "Difference image magnified twelve times" },
      { url: data.images.noise, caption: "Noise pattern", alt: "Noise pattern preview" },
      ...(data.jpeg_images || []).map((item) => ({ url: item.url, caption: `Protected, JPEG Q${item.quality}`, alt: `Protected image saved as JPEG at quality ${item.quality}` })),
    ];
    $("#inspection-grid").replaceChildren(...inspect.map((item) => h("figure", {},
      h("a", { href: item.url, target: "_blank", rel: "noopener" }, h("img", { src: item.url, alt: item.alt, loading: "lazy" })),
      h("figcaption", { text: item.caption }),
    )));

    // Provenance
    const status = $("#provenance-status");
    status.textContent = valid ? "Signature verified" : "Signature not verified";
    status.className = `state ${valid ? "state-ok" : "state-warn"}`;
    $("#provenance-reason").textContent = data.provenance.reason || "";
    $("#provenance-hash").textContent = data.provenance.hash || "No hash available";

    // SD-Turbo
    const modelTab = $("#tab-model");
    const modelBox = $("#model-result");
    if (data.model) {
      modelTab.hidden = false;
      modelBox.replaceChildren(
        h("div", { class: "model-head" }, h("h3", { text: "What SD-Turbo made of each image" }), h("span", { text: data.model.device })),
        h("p", { class: "panel-help", text: "Both images went through the same prompt, seed and settings. The more the two outputs differ, the more the protection disrupted the model." }),
        h("div", { class: "model-pair" },
          h("figure", {}, h("img", { src: data.model.original_url, alt: "SD-Turbo output from the original image" }), h("figcaption", { text: "From the original" })),
          h("figure", {}, h("img", { src: data.model.protected_url, alt: "SD-Turbo output from the protected image" }), h("figcaption", { text: "From the protected image" })),
        ),
      );
    } else if (data.model_error) {
      modelTab.hidden = false;
      modelBox.replaceChildren(
        h("div", { class: "model-head" }, h("h3", { text: "SD-Turbo test didn't run" })),
        h("p", { class: "model-error", text: data.model_error }),
      );
    } else {
      modelTab.hidden = true;
      modelBox.replaceChildren();
    }

    els.report.hidden = false;
    selectTab($("#tab-quality"));
  }

  // ---------- Tabs ----------
  const tabs = $$('[role="tab"]');
  function selectTab(tab, focus = false) {
    tabs.forEach((t) => {
      const selected = t === tab;
      t.setAttribute("aria-selected", String(selected));
      t.tabIndex = selected ? 0 : -1;
      $(`#${t.getAttribute("aria-controls")}`).hidden = !selected;
    });
    if (focus) tab.focus();
  }
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => selectTab(tab));
    tab.addEventListener("keydown", (event) => {
      const visible = tabs.filter((t) => !t.hidden);
      const i = visible.indexOf(tab);
      const next = {
        ArrowRight: visible[(i + 1) % visible.length],
        ArrowLeft: visible[(i - 1 + visible.length) % visible.length],
        Home: visible[0],
        End: visible[visible.length - 1],
      }[event.key];
      if (next) { event.preventDefault(); selectTab(next, true); }
    });
  });

  // ---------- Result actions ----------
  $("#check-chatgpt").addEventListener("click", () => {
    const href = $("#download-protected").getAttribute("href");
    if (!href) { toast("Protect an image before testing it in ChatGPT."); return; }
    const prompt = "I am testing a protected image created by CogniShield. Analyze the uploaded image, then generate a photorealistic recreation that preserves the same subject, composition, lighting, colours, and background. After generating it, briefly describe any visible differences between the uploaded protected image and your generated result.";
    window.open("https://chatgpt.com/", "_blank", "noopener");
    const link = h("a", { href, download: "cognishield_protected.png" });
    document.body.append(link);
    link.click();
    link.remove();
    navigator.clipboard?.writeText(prompt).catch(() => {});
    toast("Protected image downloaded and test prompt copied. In ChatGPT, click +, upload the image, then paste the prompt.", true);
  });

  $("#start-over").addEventListener("click", () => {
    clearFile();
    go(1);
  });

  resetResult();
  updateSteps();
})();
