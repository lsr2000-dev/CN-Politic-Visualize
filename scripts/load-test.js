import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8000/api/v1";
const DATES = __ENV.DATES
  ? __ENV.DATES.split(",")
  : ["2012-11-08", "2013-03-05", "2017-10-25", "2018-03-05", "2022-10-16", "2023-03-05", "2025-06-30"];

export const options = {
  scenarios: {
    snapshot: {
      executor: "ramping-vus",
      startVUs: 5,
      stages: [
        { duration: "20s", target: 50 },
        { duration: "40s", target: 50 },
        { duration: "10s", target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<300"],
  },
};

export default function () {
  const date = DATES[Math.floor(Math.random() * DATES.length)];
  const res = http.get(`${BASE}/map/snapshot?date=${date}`, {
    headers: { Accept: "application/json" },
    tags: { endpoint: "snapshot" },
  });
  check(res, {
    "status 200/304": (r) => r.status === 200 || r.status === 304,
    "has 31 regions": (r) => r.status !== 200 || JSON.parse(r.body).regions.length === 31,
  });
  sleep(0.2 + Math.random() * 0.6);
}
