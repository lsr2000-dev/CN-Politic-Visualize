import fs from "node:fs";

const CDP = "http://127.0.0.1:9222";
const pages = await (await fetch(`${CDP}/json/list`)).json();
const page = pages.find((item) => item.type === "page" && item.url.includes("127.0.0.1:5173"));
if (!page) throw new Error("Vite page not found");

const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  ws.addEventListener("open", resolve, { once: true });
  ws.addEventListener("error", reject, { once: true });
});
let nextId = 0;
const pending = new Map();
const events = [];
ws.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.id) {
    const handler = pending.get(message.id);
    if (handler) {
      pending.delete(message.id);
      message.error ? handler.reject(new Error(message.error.message)) : handler.resolve(message.result);
    }
    return;
  }
  events.push(message);
});
function send(method, params = {}) {
  const id = ++nextId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
await send("Runtime.enable");
await send("Network.enable");
await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

async function evaluate(expression) {
  const result = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  return result.result?.value;
}

async function clickText(text) {
  const result = await evaluate(`(() => {
    const nodes = [...document.querySelectorAll('button, a, [role="button"], .team-card, .central-team')];
    const target = nodes.find((node) => (node.innerText || '').trim().startsWith(${JSON.stringify(text)}));
    if (!target) return { clicked: false, candidates: nodes.slice(0, 30).map((n) => (n.innerText || '').trim().slice(0, 60)) };
    target.click();
    return { clicked: true, tag: target.tagName, text: (target.innerText || '').trim().slice(0, 80) };
  })()`);
  await sleep(2500);
  return result;
}

async function screenshot(name) {
  const shot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
  fs.writeFileSync(`shots/${name}.png`, Buffer.from(shot.data, "base64"));
}

await send("Page.navigate", { url: "http://127.0.0.1:5173/?date=2026-10-29&region=110000&view=sidebar" });
await sleep(4000);
console.log("click", await clickText("党中央"));
console.log("body", (await evaluate("document.body.innerText")).slice(0, 3000));
await screenshot("frontend-central-party-2026");
console.log("buttons", await evaluate(`[...document.querySelectorAll('button')].map((n) => (n.innerText||'').trim()).filter(Boolean).slice(0, 40)`));
console.log("exceptions", events.filter((e) => e.method === "Runtime.exceptionThrown").map((e) => e.params.exceptionDetails.text));
console.log("bad", events.filter((e) => e.method === "Network.responseReceived" && e.params.response.status >= 400).map((e) => [e.params.response.status, e.params.response.url]));
ws.close();
