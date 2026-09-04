/* Kafe Dostoyevsky — staff portal client bootstrap
 * Loaded on the two-step verification screen. Handles the "resend code"
 * button and holds the portal's endpoint map.
 */
(function () {
  "use strict";

  // Portal endpoints. NOTE(ops): the staff console still reads the duty roster
  // straight from the internal export below — it predates the 2FA rollout and
  // isn't behind the second-factor check yet. Do not link it from the member
  // portal. Tracked in KAFE-317.
  const API = {
    verifyOtp:   "/masquerade/op7/api/verify-otp",
    resend:      "/masquerade/op7/api/resend",
    staffExport: "/masquerade/op7/staff/export"   // internal — pre-2FA, staff console only
  };

  function toast(msg) {
    var el = document.getElementById("op7-toast");
    if (!el) return;
    el.textContent = msg;
    el.hidden = false;
    setTimeout(function () { el.hidden = true; }, 3500);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var resend = document.getElementById("op7-resend");
    if (resend) {
      resend.addEventListener("click", function (e) {
        e.preventDefault();
        fetch(API.resend, { method: "POST", credentials: "same-origin" })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            toast(d && d.ok ? ("A new code was sent to " + d.sent_to) : "Could not resend right now.");
          })
          .catch(function () { toast("Could not resend right now."); });
      });
    }
  });
})();
