# Implementation Prompt: Vault-based credential management + rotation + MFA on NMAS
<!-- Paste everything below the line into Gemini CLI (running on the NMAS host).
     It is written to be executed in phases — do not skip verification steps. -->

---

You are implementing the **Permissions objective of CSCI 5840 Lab 4/5 (IaC Part 2)** for a
containerlab network. Work in phases, verify each phase before starting the next, and never
invent credentials — ask me for any secret you need instead of hardcoding or guessing one.

## Environment (facts — do not change these)

- NMAS host: Ubuntu cloud VM, Docker + Docker Compose available, on management net 10.99.0.0/24.
- Network devices — **ALL Arista cEOS. There are no Cisco devices in this topology:**
  - R1 (10.99.0.11), R2 (10.99.0.12), R3 (10.99.0.13), R4 (10.99.0.14),
    R5 (10.99.0.15), SW1 (10.99.0.21), SW2 (10.99.0.22)
- IPAM: CSV files in git (`ipam/devices.csv` has columns
  `hostname,mgmt_ip,platform,role,username,vault_path`; every row is `arista_eos`).
  Passwords are NEVER in the CSV — only a `vault_path` pointer.
- Automation language: Python 3.12. All device changes go through **Arista eAPI (pyeapi)**
  — there is no Netmiko/Cisco path in this build.
- Constraints: 100% open source. Everything reproducible from git. No secrets in git, in
  shell history, or in CI logs. Every step documented for a lab write-up and demo video.

## Tool choice

Use **HashiCorp Vault (open source)** as the password manager. It is the correct tool here
(not Bitwarden/Vaultwarden, which are human password managers): Vault gives us versioned
KV storage, fine-grained policies, MFA enforcement, AppRole for machine auth, and an audit
device — exactly what the IaC "Permissions" objective needs.

## Phase 1 — Vault on NMAS

1. Write `vault/docker-compose.yml` + `vault/config/vault.hcl`: Vault 1.1x server, Raft
   integrated storage (single node is fine for the lab), TLS enabled (use `mkcert` or a
   self-signed CA for the lab; document that production would use a real CA), UI enabled,
   `api_addr`/`cluster_addr` set correctly.
2. Document init + unseal: `vault operator init -key-shares=3 -key-threshold=2`. Unseal keys
   and the root token are written down OFFLINE (document where — never in git, never in chat).
3. Enable two **separate** KV-v2 mounts:
   - `network/` — device credentials: `network/devices/<hostname>` = {username, password}
   - `nmas-admin/` — NMAS host credentials, cloud credentials, CI tokens. Separate mount =
     separate vault for the NMAS credentials, as required.
4. Auth methods: `userpass` for the human operator; `approle` for automation (CI runner and
   the rotation script).
5. Policies (write them as HCL files in git):
   - `network-operator`: read/write on `network/*`, **explicit deny on `nmas-admin/*`**
   - `automation` (bound to the AppRole): read/write on `network/devices/*` only, explicit
     deny on `nmas-admin/*`, short TTLs
   - `admin`: full access, but only usable with MFA (Phase 2)
6. Import the CURRENT device credentials into `network/devices/*`. Ask me for them through a
   secure channel — do not invent placeholder passwords and call it done.
7. Verification: `vault kv get network/devices/R1` works with the operator token; the same
   token gets **denied** on `nmas-admin/`; the AppRole token can read `network/devices/*`
   but is denied on `nmas-admin/*`. Show me all three results.

## Phase 2 — MFA (TOTP), enforced where it matters

Architecture note (implement exactly this — it is what Vault OSS actually supports):
- Require **TOTP MFA for the human `userpass` auth method** via `sys/mfa` enforcement.
  Any human login to Vault then requires password + TOTP, which covers access to the
  `nmas-admin/` vault.
- Automation keeps using AppRole **without** MFA, but with tight CIDR binding (NMAS only),
  short secret-id TTLs, and a policy that can never read `nmas-admin/`.

Steps:
1. `vault write sys/mfa/method/totp/...` — configure a TOTP method; enroll the operator and
   show the enrollment flow (QR/URI) without pasting the secret into the repo.
2. `vault write sys/mfa/enforcement/...` — enforce the TOTP method on the `userpass` auth
   mount for all logins.
3. Populate `nmas-admin/` with the NMAS credentials (ask me for them securely).
4. Negative tests (show me): login WITHOUT TOTP → denied; login WITH TOTP → allowed;
   AppRole token → `network/devices/*` OK, `nmas-admin/*` denied.
5. Document recovery: what happens if the TOTP device is lost (unseal-key holders can reset
   the MFA method — write the exact procedure).

## Phase 3 — Automatic credential rotation (the "changed on a regular basis" requirement)

Write `scripts/rotate_passwords.py` with this exact safety contract:

1. Reads `ipam/devices.csv`; per device generates a 24+ character password with Python
   `secrets`.
2. Pushes the new credential to the device via **eAPI/pyeapi**
   (`username <user> secret <new-password>` — confirm the exact EOS syntax for the running
   version, including privilege-15 / enable-password handling, before writing the script).
3. **Ordering (non-negotiable):** change on the device FIRST → verify with a brand-new
   eAPI/SSH login using the new credential → ONLY THEN write to Vault (KV-v2 versions the
   old secret, so rollback is possible). On any failure: abort that device, keep old
   credentials everywhere, log the failure, continue with the next device. Vault and the
   device must never disagree.
4. CLI: `--dry-run` (default safe), `--device R1` (targeted), `--stagger SECONDS` (don't
   rotate everything at once).
5. Scheduling: a systemd timer on NMAS (weekly) AND callable from the GitHub Actions
   `rotate-credentials` workflow (monthly cron + manual dispatch).
6. Audit: enable Vault's file audit device; forward rotation-script logs to syslog so they
   flow into the Lab 2 monitoring pipeline.
7. Verification for the video: rotate R1, show old password rejected / new accepted, show
   `vault kv get -version` history, show the audit log entry, show a `--dry-run` first.

## Phase 4 — 2FA for actual device logins (lab extra credit)

Honest architecture: per-login TOTP on a switch CLI is done with **RADIUS + privacyIDEA**,
not inside Vault. Implement in this order, and do not start until Phases 1–3 are green:

1. Deploy **privacyIDEA** (open source) as a container on NMAS; create the operator realm
   and enroll a TOTP token.
2. Deploy **FreeRADIUS** with privacyIDEA's `rlm_perl` plugin on NMAS (this is privacyIDEA's
   documented RADIUS integration).
3. Point the Arista devices at it:
   `radius-server host 10.99.0.x key <key>` +
   `aaa authentication login default group radius local`.
   **Keep `local` fallback and prove fallback works by stopping FreeRADIUS — do not lock
   yourself out.**
4. Demo: SSH to R1 with `password+OTP` concatenated; wrong OTP → rejected.
5. Document rollback (remove the RADIUS lines) in the write-up.

## What you deliver to me

1. `vault/` — compose, config, policies (HCL), MFA setup scripts. No secrets.
2. `scripts/rotate_passwords.py` + systemd unit/timer (eAPI/pyeapi only — no Cisco code paths).
3. `radius/` — FreeRADIUS + privacyIDEA compose and config (Phase 4).
4. Device config snippet for RADIUS (single Jinja2 template — Arista only).
5. A write-up section I can paste into the lab report, in my voice (concise, technical).
6. A verification checklist mapping every demo step to exact commands for the video,
   with secrets redacted.
7. A list of anything you need from me (current credentials, NMAS IP, domain) — ask,
   don't invent.
