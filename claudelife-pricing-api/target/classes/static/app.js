// Talks to the Spring API. Same origin, so paths are relative.
// If you serve this page from anywhere other than :8080, set API to
// "http://localhost:8080" and enable CORS on the Java side.
const API = "";

const $ = (id) => document.getElementById(id);
const money = (n) =>
    Number(n).toLocaleString("en-GB", { style: "currency", currency: "GBP" });
const date = (iso) =>
    new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

let quoteId = null;
let policyId = null;
let claimId = null;

// ---------------------------------------------------------------- request

/**
 * One place for every call. Returns { ok, status, body } rather than
 * throwing, because a 409 decline is a real answer, not a failure.
 */
async function call(method, path, body) {
  try {
    const res = await fetch(API + path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });

    const text = await res.text();
    const parsed = text ? JSON.parse(text) : null;
    return { ok: res.ok, status: res.status, body: parsed };
  } catch (err) {
    return { ok: false, status: 0, body: { message: err.message } };
  }
}

// ---------------------------------------------------------------- notices

function notice(el, kind, heading, message, list) {
  el.className = "notice" + (kind === "refused" ? " refused" : "");
  el.innerHTML =
      `<h4>${heading}</h4><p>${message}</p>` +
      (list ? `<ul>${list.map((i) => `<li>${i}</li>`).join("")}</ul>` : "");
  el.hidden = false;
}

/** Turns any non-2xx response into something a person can act on. */
function explain(el, res) {
  if (res.status === 0) {
    notice(el, "refused", "No response from the API",
        "Nothing is listening on port 8080. Start it with mvn spring-boot:run.");
    return;
  }

  const b = res.body || {};

  if (res.status === 422 && b.fields) {
    notice(el, "refused", "Check these fields",
        "The request did not pass validation.",
        Object.entries(b.fields).map(([f, m]) => `<strong>${f}</strong> ${m}`));
    return;
  }

  if (res.status === 409 && b.code === "DECLINED") {
    notice(el, "refused", "Declined", b.message +
        ". The quote is still recorded, with no premium against it.");
    return;
  }

  notice(el, "refused", b.code || `Error ${res.status}`,
      b.message || "The request could not be completed.");
}

function openStage(id) {
  $(id).classList.add("is-open");
}

function completeStage(id) {
  $(id).classList.add("is-done");
}

// ------------------------------------------------------------- BMI hint

const bmiInput = $("bmi");

function describeBmi() {
  const bmi = parseFloat(bmiInput.value);
  const hint = $("bmi-band");

  if (isNaN(bmi)) { hint.textContent = ""; return; }
  if (bmi >= 45) { hint.textContent = "45 and over falls outside the limits"; return; }
  if (bmi >= 35) { hint.textContent = "35 and over carries a 1.6 loading"; return; }
  if (bmi >= 30) { hint.textContent = "30 to 34.9 carries a 1.25 loading"; return; }
  hint.textContent = "Standard, no loading";
}

bmiInput.addEventListener("input", describeBmi);
describeBmi();

// --------------------------------------------------------------- presets

const PRESETS = {
  standard: { age: 35, sex: "M", smoker: false, bmi: 26.0, sumAssured: 250000, termYears: 25 },
  smoker:   { age: 35, sex: "M", smoker: true,  bmi: 26.0, sumAssured: 250000, termYears: 25 },
  loaded:   { age: 42, sex: "F", smoker: false, bmi: 32.4, sumAssured: 400000, termYears: 20 },
  declined: { age: 62, sex: "M", smoker: false, bmi: 28.0, sumAssured: 250000, termYears: 25 },
};

document.querySelectorAll(".preset").forEach((btn) => {
  btn.addEventListener("click", () => {
    const p = PRESETS[btn.dataset.preset];
    $("age").value = p.age;
    $("sex").value = p.sex;
    $("smoker").checked = p.smoker;
    $("bmi").value = p.bmi;
    $("sumAssured").value = p.sumAssured;
    $("termYears").value = p.termYears;
    describeBmi();
  });
});

// ------------------------------------------------------- 1. get a quote

$("get-quote").addEventListener("click", async () => {
  $("quote-notice").hidden = true;

  const res = await call("POST", "/quotes", {
    age: Number($("age").value),
    sex: $("sex").value,
    smoker: $("smoker").checked,
    bmi: Number($("bmi").value),
    sumAssured: Number($("sumAssured").value),
    termYears: Number($("termYears").value),
  });

  if (!res.ok) {
    $("quote-result").hidden = true;
    $("accept-quote").disabled = true;
    quoteId = null;
    explain($("quote-notice"), res);
    return;
  }

  const q = res.body;
  quoteId = q.quoteId;

  $("annual-premium").textContent = money(q.annualPremium);
  $("monthly-premium").textContent = money(q.monthlyPremium);
  $("quote-status").innerHTML = `<span class="tag-live">${q.status}</span>`;
  $("quote-expiry").textContent = date(q.expiresAt);
  $("quote-id").textContent = q.quoteId;
  $("quote-result").hidden = false;

  completeStage("stage-quote");
  openStage("stage-policy");
  $("accept-quote").disabled = false;
});

// ---------------------------------------------------- 2. accept a quote

$("accept-quote").addEventListener("click", async () => {
  $("policy-notice").hidden = true;

  const res = await call("POST", `/quotes/${quoteId}/accept`);

  if (!res.ok) { explain($("policy-notice"), res); return; }

  const p = res.body;
  policyId = p.id;

  $("policy-number").textContent = p.policyNumber;
  $("policy-start").textContent = date(p.startDate);
  $("policy-end").textContent = date(p.endDate);
  $("policy-status").innerHTML = `<span class="tag-live">${p.status}</span>`;
  $("policy-result").hidden = false;

  $("quote-status").innerHTML = `<span class="tag-live">ACCEPTED</span>`;
  $("accept-quote").disabled = true;

  completeStage("stage-policy");
  openStage("stage-claim");
  $("file-claim").disabled = false;
  $("eventDate").value = new Date().toISOString().slice(0, 10);
});

// ----------------------------------------------------- 3. file a claim

$("file-claim").addEventListener("click", async () => {
  $("claim-notice").hidden = true;

  const res = await call("POST", `/policies/${policyId}/claims`, {
    eventDate: $("eventDate").value,
    amount: Number($("claimAmount").value),
  });

  if (!res.ok) { explain($("claim-notice"), res); return; }

  const c = res.body;
  claimId = c.id;

  $("claim-id").textContent = c.id;
  $("claim-amount").textContent = money(c.amount);
  $("claim-status").innerHTML = `<span class="tag-pending">${c.status}</span>`;
  $("claim-result").hidden = false;

  $("file-claim").disabled = true;
  completeStage("stage-claim");
  openStage("stage-settle");
  $("pay-claim").disabled = false;
  $("reject-claim").disabled = false;
});

// -------------------------------------------------- 4. settle the claim

async function settle(status) {
  $("settle-notice").hidden = true;

  const res = await call("PATCH", `/claims/${claimId}`, { status });

  if (!res.ok) { explain($("settle-notice"), res); return; }

  const paid = status === "PAID";

  $("claim-status").innerHTML =
      `<span class="${paid ? "tag-live" : "tag-refused"}">${res.body.status}</span>`;

  if (paid) {
    $("policy-status").innerHTML = `<span class="tag-refused">CLAIMED</span>`;
    notice($("settle-notice"), "ok", "Claim paid",
        "Cover has come to an end and the policy is marked claimed.");
  } else {
    notice($("settle-notice"), "ok", "Claim rejected",
        "The claim is closed. Cover remains in force.");
  }

  $("pay-claim").disabled = true;
  $("reject-claim").disabled = true;
  completeStage("stage-settle");
}

$("pay-claim").addEventListener("click", () => settle("PAID"));
$("reject-claim").addEventListener("click", () => settle("REJECTED"));

// ----------------------------------------------------- loss ratio report

$("load-report").addEventListener("click", async () => {
  const res = await call("GET", "/reports/loss-ratio");
  const el = $("report");
  el.hidden = false;

  if (!res.ok) {
    el.innerHTML = `<p class="stage-note">Report failed: ${res.status}</p>`;
    return;
  }

  if (!res.body || res.body.length === 0) {
    el.innerHTML = `<p class="stage-note">Nothing to report yet. Take a policy on risk first.</p>`;
    return;
  }

  el.innerHTML = `
    <table>
      <thead>
        <tr><th>Segment</th><th>Age band</th><th>Premium</th><th>Paid claims</th><th>Loss ratio</th></tr>
      </thead>
      <tbody>
        ${res.body.map((r) => `
          <tr>
            <td>${r.segment}</td>
            <td>${r.ageBand}</td>
            <td>${money(r.premium)}</td>
            <td>${money(r.paidClaims)}</td>
            <td>${(Number(r.lossRatio) * 100).toFixed(1)}%</td>
          </tr>`).join("")}
      </tbody>
    </table>`;
});