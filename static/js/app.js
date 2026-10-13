const $ = (selector) => document.querySelector(selector);
const fileInput = $("#image-input");
const dropzone = $("#dropzone");
const protectButton = $("#protect-button");
const message = $("#upload-message");
let selectedFile = null;

function sound(kind = "click") {
  try {
    const context = new (window.AudioContext || window.webkitAudioContext)();
    const osc = context.createOscillator();
    const gain = context.createGain();
    osc.type = kind === "success" ? "sine" : "triangle";
    osc.frequency.value = kind === "success" ? 660 : 390;
    gain.gain.setValueAtTime(.035, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(.001, context.currentTime + .09);
    osc.connect(gain).connect(context.destination); osc.start(); osc.stop(context.currentTime + .1);
  } catch (_) { /* Sound is an optional progressive enhancement. */ }
}

function setRange(range) {
  const value = range.value;
  const percentage = ((value - range.min) / (range.max - range.min)) * 100;
  range.style.setProperty("--fill", `${percentage}%`);
  $(`#${range.id}-value`).value = value;
}

document.querySelectorAll(".range").forEach((range) => { setRange(range); range.addEventListener("input", () => setRange(range)); });
document.addEventListener("mousemove", (event) => { document.body.style.setProperty("--x", `${event.clientX}px`); document.body.style.setProperty("--y", `${event.clientY}px`); });
document.querySelectorAll("button, a, input, label, .dropzone").forEach((element) => { element.addEventListener("mouseenter", () => document.body.classList.add("cursor-hover")); element.addEventListener("mouseleave", () => document.body.classList.remove("cursor-hover")); });

$("#theme-toggle").addEventListener("click", () => {
  const light = document.body.dataset.theme === "light";
  document.body.dataset.theme = light ? "dark" : "light";
  $("#theme-toggle").setAttribute("aria-pressed", String(!light));
  $("#theme-toggle").setAttribute("aria-label", light ? "Switch to light mode" : "Switch to dark mode");
  localStorage.setItem("cognishield-theme", document.body.dataset.theme); sound();
});
const savedTheme = localStorage.getItem("cognishield-theme");
if (savedTheme === "light") { document.body.dataset.theme = "light"; $("#theme-toggle").setAttribute("aria-pressed", "true"); }

$("#run-model").addEventListener("change", (event) => { $("#prompt-wrap").hidden = !event.target.checked; });
document.querySelectorAll(".number-button").forEach((button) => button.addEventListener("click", () => { const seed = $("#seed"); seed.value = Math.max(0, Math.min(999999, Number(seed.value || 0) + Number(button.dataset.step))); sound(); }));

function showToast(text, success = false) { const toast = $("#toast"); toast.textContent = text; toast.className = `toast${success ? " success" : ""}`; toast.hidden = false; window.setTimeout(() => { toast.hidden = true; }, 4500); }
function chooseFile(file) {
  if (!file) return;
  if (!/^image\/(png|jpeg|webp)$/.test(file.type)) return showToast("Please choose a PNG, JPG, or WEBP image.");
  if (file.size > 200 * 1024 * 1024) return showToast("That image is larger than 200 MB.");
  selectedFile = file; $("#preview-image").src = URL.createObjectURL(file); $("#file-name").textContent = file.name;
  $("#upload-empty").hidden = true; $("#upload-preview").hidden = false; protectButton.disabled = false; message.textContent = "Image ready. Review the protection settings, then continue."; sound();
}
$("#browse-button").addEventListener("click", () => fileInput.click()); $("#change-image").addEventListener("click", () => fileInput.click()); fileInput.addEventListener("change", () => chooseFile(fileInput.files[0]));
dropzone.addEventListener("click", (event) => { if (!event.target.closest("button")) fileInput.click(); });
dropzone.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); fileInput.click(); } });
["dragenter", "dragover"].forEach((type) => dropzone.addEventListener(type, (event) => { event.preventDefault(); dropzone.classList.add("dragging"); }));
["dragleave", "drop"].forEach((type) => dropzone.addEventListener(type, (event) => { event.preventDefault(); dropzone.classList.remove("dragging"); }));
dropzone.addEventListener("drop", (event) => chooseFile(event.dataTransfer.files[0]));

function number(value) { return value === null || value === undefined ? "—" : Number(value).toLocaleString(undefined, { maximumFractionDigits: 6 }); }
function metric(label, value) { return `<div class="metric"><span>${label}</span><strong>${number(value)}</strong></div>`; }
function renderResult(data) {
  $("#result-empty").hidden = true; $("#result-content").hidden = false; $("#details").hidden = false;
  $("#result-original").src = data.images.original; $("#result-protected").src = data.images.protected;
  $("#download-protected").href = data.downloads.protected; $("#download-provenance").href = data.downloads.provenance;
  $("#protection-detail").textContent = data.provenance.reason;
  $("#metrics-grid").innerHTML = metric("PSNR", data.metrics.psnr) + metric("SSIM", data.metrics.ssim) + metric("MSE", data.metrics.mse) + metric("Mean abs delta", data.metrics.mean_abs_delta) + metric("Max abs delta", data.metrics.max_abs_delta);
  $("#compression-body").innerHTML = data.compression.map((item) => `<tr><td>${item.quality}</td><td>${number(item.psnr)}</td><td>${number(item.ssim)}</td><td>${number(item.mse)}</td></tr>`).join("");
  $("#inspection-grid").innerHTML = `<figure><img src="${data.images.difference}" alt="Difference image magnified twelve times"><figcaption>Difference ×12</figcaption></figure><figure><img src="${data.images.noise}" alt="Noise preview"><figcaption>Noise preview</figcaption></figure>` + data.jpeg_images.map((item) => `<figure><img src="${item.url}" alt="Protected JPEG at quality ${item.quality}"><figcaption>JPEG ${item.quality}</figcaption></figure>`).join("");
  $("#provenance-status").textContent = data.provenance.valid ? "Verified" : "Not verified"; $("#provenance-reason").textContent = data.provenance.reason; $("#provenance-hash").textContent = data.provenance.hash || "No hash available";
  const model = $("#model-result");
  if (data.model) { model.hidden = false; model.innerHTML = `<div class="panel-heading"><h2>SD-Turbo target test</h2><span>${data.model.device}</span></div><div class="image-comparison"><figure><figcaption>Original through SD-Turbo</figcaption><img src="${data.model.original_url}" alt="Original SD-Turbo output"></figure><figure><figcaption>Protected through SD-Turbo</figcaption><img src="${data.model.protected_url}" alt="Protected SD-Turbo output"></figure></div>`; }
  else if (data.model_error) { model.hidden = false; model.innerHTML = `<div class="panel-heading"><h2>SD-Turbo target test</h2><span>Unavailable</span></div><p>${data.model_error}</p>`; } else { model.hidden = true; }
}

$("#check-chatgpt").addEventListener("click", () => {
  const protectedDownload = $("#download-protected").getAttribute("href");
  if (!protectedDownload) return showToast("Protect an image before opening ChatGPT.");
  const prompt = "I am testing a protected image created by CogniShield. Analyze the uploaded image, then generate a photorealistic recreation that preserves the same subject, composition, lighting, colours, and background. After generating it, briefly describe any visible differences between the uploaded protected image and your generated result.";
  window.open("https://chatgpt.com/", "_blank", "noopener");
  const download = document.createElement("a");
  download.href = protectedDownload;
  download.download = "cognishield_protected.png";
  document.body.appendChild(download);
  download.click();
  download.remove();
  navigator.clipboard?.writeText(prompt).catch(() => {});
  sound("success");
  showToast("Protected image downloaded and comparison prompt copied. In ChatGPT, click +, upload the image, then paste the prompt.", true);
});

protectButton.addEventListener("click", async () => {
  if (!selectedFile) return showToast("Choose an image first.");
  const form = new FormData(); form.append("image", selectedFile); form.append("epsilon", $("#epsilon").value); form.append("iterations", $("#iterations").value); form.append("seed", $("#seed").value); form.append("run_model", $("#run-model").checked); form.append("prompt", $("#prompt").value);
  document.querySelectorAll('input[name="qualities"]:checked').forEach((input) => form.append("qualities", input.value));
  protectButton.disabled = true; protectButton.innerHTML = "<span>◌</span> Protecting…"; $("#result-state").textContent = "Processing"; $("#result-state").className = "result-state processing"; message.textContent = "Creating and signing your protected image…";
  try { const response = await fetch("/api/protect", { method: "POST", body: form }); const data = await response.json(); if (!response.ok) throw new Error(data.error || "Unable to protect this image."); renderResult(data); $("#result-state").textContent = "Complete"; $("#result-state").className = "result-state done"; message.textContent = "Protection complete. Your downloads are ready."; sound("success"); $("#result-content").scrollIntoView({ behavior: "smooth", block: "center" }); }
  catch (error) { $("#result-state").textContent = "Try again"; $("#result-state").className = "result-state"; message.textContent = "Protection did not complete."; showToast(error.message); }
  finally { protectButton.disabled = false; protectButton.innerHTML = "<span>⌬</span> Protect image"; }
});
