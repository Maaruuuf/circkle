// Load test with k6 (https://k6.io). Run against a TEST environment, never production:
//
//   docker run --rm -i --network host -e BASE_URL=http://localhost:8001 \
//     grafana/k6 run - < loadtests/k6/smoke.js
//
// Start the API with RATE_LIMIT_ENABLED=false, otherwise the app (correctly) answers 429.
// Needs the seed data:  python -m scripts.seed
import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8001";
const PASSWORD = __ENV.SEED_PASSWORD || "Circkle#Dev2026";
const USERS = ["ada", "grace", "linus", "margaret", "alan", "tim", "radia", "ken", "barbara", "dennis"];

export const options = {
  stages: [
    { duration: "30s", target: 50 }, // ramp up
    { duration: "1m", target: 50 }, // steady
    { duration: "15s", target: 0 }, // ramp down
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"], // < 1% errors
    "http_req_duration{kind:read}": ["p(95)<200"], // non-functional goal: p95 < 200 ms
  },
};

export default function () {
  const name = USERS[(__VU - 1) % USERS.length];

  // Log in once per virtual user (argon2 is deliberately slow, so we do not repeat it).
  if (__ITER === 0) {
    const login = http.post(
      `${BASE_URL}/api/v1/auth/login`,
      JSON.stringify({ email: `${name}@example.com`, password: PASSWORD }),
      { headers: { "Content-Type": "application/json" } },
    );
    check(login, { "login ok": (r) => r.status === 200 });
  }

  const tags = { tags: { kind: "read" } };
  const feed = http.get(`${BASE_URL}/api/v1/posts/feed?limit=20`, tags);
  check(feed, { "feed ok": (r) => r.status === 200 });

  const explore = http.get(`${BASE_URL}/api/v1/posts/explore?limit=20`, tags);
  check(explore, { "explore ok": (r) => r.status === 200 });

  const profile = http.get(`${BASE_URL}/api/v1/users/${name}`, tags);
  check(profile, { "profile ok": (r) => r.status === 200 });

  sleep(1);
}
