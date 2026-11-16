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
for (const date of ["2012-11-08", "2018-04-01", "2026-10-29"]) {
  await send("Page.navigate", { url: `http://127.0.0.1:5173/?date=${date}&region=110000&view=sidebar` });
  await sleep(3000);
  const text = (await send("Runtime.evaluate", { expression: "document.body.innerText", returnByValue: true })).result.value;
  const matches = text.split("\n").filter((line) => /undefined|politburo_|secretariat_|discipline_|theater_|departmental|term_ended|active/.test(line));
  console.log(date, JSON.stringify(matches));
}
ws.close();
