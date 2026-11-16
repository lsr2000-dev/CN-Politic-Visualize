import fs from "node:fs";
const CDP = "http://127.0.0.1:9222";
const pages = await (await fetch(`${CDP}/json/list`)).json();
const page = pages.find((item) => item.type === "page" && item.url.includes("127.0.0.1:5173"));
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve, reject) => { ws.addEventListener("open", resolve, { once: true }); ws.addEventListener("error", reject, { once: true }); });
let nextId = 0; const pending = new Map();
ws.addEventListener("message", (event) => { const m = JSON.parse(event.data); if (m.id) { const h = pending.get(m.id); if (h) { pending.delete(m.id); m.error ? h.reject(new Error(m.error.message)) : h.resolve(m.result); } } });
const send = (method, params = {}) => new Promise((resolve, reject) => { const id = ++nextId; pending.set(id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params })); });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
await send("Page.enable"); await send("Runtime.enable");
for (const [width, height] of [[1024, 768], [768, 1024]]) {
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: "http://127.0.0.1:5173/?date=2026-10-29&region=310000&view=sidebar" });
  await sleep(3500);
  const metrics = await send("Runtime.evaluate", { expression: "({inner: innerWidth, scroll: document.documentElement.scrollWidth, body: document.body.scrollWidth})", returnByValue: true });
  const shot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
  fs.writeFileSync(`shots/frontend-${width}x${height}.png`, Buffer.from(shot.data, "base64"));
  console.log(width, height, metrics.result.value);
}
ws.close();
