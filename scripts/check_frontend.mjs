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
  if (["Runtime.consoleAPICalled", "Runtime.exceptionThrown", "Log.entryAdded", "Network.loadingFailed", "Network.responseReceived"].includes(message.method)) {
    events.push(message);
  }
});

function send(method, params = {}) {
  const id = ++nextId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

await send("Runtime.enable");
await send("Log.enable");
await send("Network.enable");
await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", {
  width: 1440, height: 900, deviceScaleFactor: 1, mobile: false,
});
await send("Page.reload", { ignoreCache: true });
await new Promise((resolve) => setTimeout(resolve, 4500));

const body = await send("Runtime.evaluate", {
  expression: "document.body.innerText",
  returnByValue: true,
});
const shot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
fs.writeFileSync("shots/frontend-home.png", Buffer.from(shot.data, "base64"));

const consoleMessages = events
  .filter((event) => event.method === "Runtime.consoleAPICalled")
  .map((event) => ({
    type: event.params.type,
    text: event.params.args.map((arg) => arg.value ?? arg.description ?? "").join(" "),
  }));
const exceptions = events
  .filter((event) => event.method === "Runtime.exceptionThrown")
  .map((event) => event.params.exceptionDetails.text + " " + (event.params.exceptionDetails.exception?.description ?? ""));
const failures = events
  .filter((event) => event.method === "Network.loadingFailed")
  .map((event) => ({ url: event.params.requestId, error: event.params.errorText }));
const badResponses = events
  .filter((event) => event.method === "Network.responseReceived" && event.params.response.status >= 400)
  .map((event) => ({ url: event.params.response.url, status: event.params.response.status }));

console.log(JSON.stringify({
  url: page.url,
  text: body.result.value.slice(0, 4000),
  consoleMessages,
  exceptions,
  failures,
  badResponses,
}, null, 2));
ws.close();
