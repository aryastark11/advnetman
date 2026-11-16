// NetSleuth AI Frontend Controller

let currentTopology = null;
let selectedNode = null;
let selectedIncidentId = null;
let currentTransform = { x: 0, y: 0, scale: 0.95 };
let isDragging = false;
let dragStart = { x: 0, y: 0 };

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initTopology();
    initPathTracer();
    initChat();
    initDemoBar();

    // Polling cycles
    loadTopology();
    loadIncidents();
    setInterval(loadIncidents, 3000);
    setInterval(loadTopologyHealth, 5000);
});

// Tab Navigation
function initTabs() {
    const tabBtns = document.querySelectorAll(".tab-btn");
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            btn.classList.add("active");
            const target = document.getElementById(btn.dataset.target);
            if (target) target.classList.add("active");
        });
    });
}

function switchTab(tabId) {
    const btn = document.querySelector(`.tab-btn[data-target="${tabId}"]`);
    if (btn) btn.click();
}

// Topology Visualization (SVG)
function initTopology() {
    const svg = document.getElementById("topology-svg");
    
    // Pan & Zoom
    svg.addEventListener("mousedown", (e) => {
        if (e.target.tagName === "svg" || e.target.id === "topo-viewport") {
            isDragging = true;
            dragStart = { x: e.clientX - currentTransform.x, y: e.clientY - currentTransform.y };
            svg.style.cursor = "grabbing";
        }
    });

    window.addEventListener("mousemove", (e) => {
        if (isDragging) {
            currentTransform.x = e.clientX - dragStart.x;
            currentTransform.y = e.clientY - dragStart.y;
            updateTransform();
        }
    });

    window.addEventListener("mouseup", () => {
        isDragging = false;
        svg.style.cursor = "grab";
    });

    svg.addEventListener("wheel", (e) => {
        e.preventDefault();
        const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
        currentTransform.scale = Math.max(0.4, Math.min(2.5, currentTransform.scale * zoomFactor));
        updateTransform();
    });

    document.getElementById("btn-zoom-in").addEventListener("click", () => {
        currentTransform.scale = Math.min(2.5, currentTransform.scale * 1.15);
        updateTransform();
    });
    document.getElementById("btn-zoom-out").addEventListener("click", () => {
        currentTransform.scale = Math.max(0.4, currentTransform.scale * 0.85);
        updateTransform();
    });
    document.getElementById("btn-zoom-reset").addEventListener("click", () => {
        currentTransform = { x: 30, y: 10, scale: 0.9 };
        updateTransform();
    });
}

function updateTransform() {
    const viewport = document.getElementById("topo-viewport");
    if (viewport) {
        viewport.setAttribute("transform", `translate(${currentTransform.x}, ${currentTransform.y}) scale(${currentTransform.scale})`);
    }
}

async function loadTopology() {
    try {
        const res = await fetch("/api/topology");
        currentTopology = await res.json();
        renderTopology(currentTopology);
    } catch (e) {
        console.error("Failed to load topology:", e);
    }
}

async function loadTopologyHealth() {
    if (!currentTopology) return;
    try {
        const res = await fetch("/api/topology");
        const fresh = await res.json();
        // Update node health rings without full re-render
        fresh.nodes.forEach(n => {
            const circle = document.getElementById(`node-ring-${n.id}`);
            if (circle) {
                circle.setAttribute("stroke", getNodeColor(n.health));
                if (n.health === "critical") {
                    circle.setAttribute("filter", "url(#glow-critical)");
                } else {
                    circle.removeAttribute("filter");
                }
            }
        });
    } catch (e) {
        console.error("Health update error:", e);
    }
}

function getNodeColor(health) {
    if (health === "critical") return "#ef4444";
    if (health === "warning") return "#f59e0b";
    return "#10b981";
}

function renderTopology(data) {
    const viewport = document.getElementById("topo-viewport");
    viewport.innerHTML = "";

    // 1. Defs & Filters for Glow effects
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    defs.innerHTML = `
      <filter id="glow-critical" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="8" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
      <filter id="glow-cyan" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="5" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    `;
    viewport.appendChild(defs);

    // Group for Edges
    const edgesGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
    edgesGroup.id = "edges-group";
    viewport.appendChild(edgesGroup);

    // Group for Nodes
    const nodesGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
    nodesGroup.id = "nodes-group";
    viewport.appendChild(nodesGroup);

    // Node lookup
    const nodeMap = {};
    data.nodes.forEach(n => { nodeMap[n.id] = n; });

    // Render Edges
    data.edges.forEach(e => {
        const u = nodeMap[e.source];
        const v = nodeMap[e.target];
        if (!u || !v) return;

        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("id", `edge-${e.id}`);
        line.setAttribute("x1", u.x);
        line.setAttribute("y1", u.y);
        line.setAttribute("x2", v.x);
        line.setAttribute("y2", v.y);
        line.setAttribute("stroke", e.health === "critical" ? "#ef4444" : "#2a3b5c");
        line.setAttribute("stroke-width", e.type === "core" ? "3" : "2");
        line.setAttribute("stroke-dasharray", e.type === "mgmt" ? "4,4" : "none");
        edgesGroup.appendChild(line);

        // Protocol badge on edge midpoint
        if (e.protocol && !e.protocol.includes("Access")) {
            const mx = (u.x + v.x) / 2;
            const my = (u.y + v.y) / 2;
            const badge = document.createElementNS("http://www.w3.org/2000/svg", "text");
            badge.setAttribute("x", mx);
            badge.setAttribute("y", my - 4);
            badge.setAttribute("fill", "#64748b");
            badge.setAttribute("font-size", "9px");
            badge.setAttribute("font-weight", "600");
            badge.setAttribute("text-anchor", "middle");
            badge.textContent = e.protocol.split(" ")[0];
            edgesGroup.appendChild(badge);
        }
    });

    // Render Nodes
    data.nodes.forEach(n => {
        const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
        g.setAttribute("class", "topo-node");
        g.setAttribute("transform", `translate(${n.x}, ${n.y})`);
        g.style.cursor = "pointer";

        // Outer health ring
        const ring = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        ring.setAttribute("id", `node-ring-${n.id}`);
        ring.setAttribute("r", n.role === "router" ? 22 : 18);
        ring.setAttribute("fill", "#111827");
        ring.setAttribute("stroke", getNodeColor(n.health));
        ring.setAttribute("stroke-width", "3");
        if (n.health === "critical") ring.setAttribute("filter", "url(#glow-critical)");
        g.appendChild(ring);

        // Inner shape icon / symbol
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("y", 4);
        label.setAttribute("fill", "#ffffff");
        label.setAttribute("font-size", "11px");
        label.setAttribute("font-weight", "700");
        label.setAttribute("text-anchor", "middle");
        label.textContent = n.label;
        g.appendChild(label);

        // Subtitle (IP address)
        const sub = document.createElementNS("http://www.w3.org/2000/svg", "text");
        sub.setAttribute("y", n.role === "router" ? 34 : 30);
        sub.setAttribute("fill", "#94a3b8");
        sub.setAttribute("font-size", "9px");
        sub.setAttribute("text-anchor", "middle");
        sub.textContent = n.ip || "";
        g.appendChild(sub);

        // Node click -> open Evidence Panel
        g.addEventListener("click", () => {
            selectNode(n.id);
        });

        nodesGroup.appendChild(g);
    });

    updateTransform();
}

async function selectNode(nodeId) {
    selectedNode = nodeId;
    switchTab("tab-evidence");
    document.getElementById("evidence-node-name").textContent = `Node Evidence: ${nodeId}`;
    document.getElementById("evidence-content").innerHTML = `<div style="color:var(--accent-cyan);">Querying eAPI for live telemetry on ${nodeId}...</div>`;

    try {
        const res = await fetch(`/api/nodes/${nodeId}/evidence`);
        const ev = await res.json();
        renderEvidencePanel(ev);
    } catch (e) {
        document.getElementById("evidence-content").innerHTML = `<div style="color:var(--status-red);">eAPI Connection Error: ${e}</div>`;
    }
}

function renderEvidencePanel(ev) {
    const container = document.getElementById("evidence-content");
    container.innerHTML = "";

    // 1. Device Info Header
    const driftBadge = ev.drift && ev.drift.has_drift 
        ? `<span class="stat-badge badge-amber">CONFIG DRIFT</span>` 
        : `<span class="stat-badge badge-green">GOLDEN BASELINE</span>`;

    let html = `
      <div class="evidence-section">
        <div class="section-title">
          <span>${ev.device} (${ev.mgmt_ip})</span>
          ${driftBadge}
        </div>
        <div style="font-size:11px; color:var(--text-secondary);">eAPI Protocol: HTTP Port 80 | Vault Path: network/devices/${ev.device}</div>
      </div>
    `;

    // 2. Interfaces Status
    const statuses = ev.interfaces ? ev.interfaces.statuses : {};
    let intfRows = "";
    for (const [name, st] of Object.entries(statuses || {})) {
        const isUp = (st.lineProtocolStatus === "up" || st.interfaceStatus === "connected");
        const statusBadge = isUp 
            ? `<span style="color:var(--status-green);">● UP</span>` 
            : `<span style="color:var(--status-red);">● DOWN</span>`;
        intfRows += `
          <div style="display:flex; justify-content:space-between; font-size:11px; padding:3px 0; border-bottom:1px solid #1f293d;">
            <span><b>${name}</b> (${st.description || "N/A"})</span>
            <span>${st.bandwidth ? (st.bandwidth/1000000000 + "G") : ""} ${statusBadge}</span>
          </div>
        `;
    }

    html += `
      <div class="evidence-section">
        <div class="section-title">Interfaces & Line Protocols</div>
        <div style="max-height:140px; overflow-y:auto;">${intfRows || "No interfaces found"}</div>
      </div>
    `;

    // 3. Routing Adjacencies (OSPF, BGP, RIP, VARP)
    if (ev.ospf && ev.ospf.length > 0) {
        let ospfRows = ev.ospf.map(n => `
          <div style="font-size:11px; padding:3px 0; display:flex; justify-content:space-between;">
            <span>Neighbor <b>${n.router_id}</b> (${n.interface})</span>
            <span style="color:${n.state==='full'?'var(--status-green)':'var(--status-amber)'}; font-weight:600;">${n.state.toUpperCase()} (Area ${n.area})</span>
          </div>
        `).join("");
        html += `
          <div class="evidence-section">
            <div class="section-title">OSPF Neighbor Adjacencies</div>
            ${ospfRows}
          </div>
        `;
    }

    if (ev.bgp && ev.bgp.length > 0) {
        let bgpRows = ev.bgp.map(p => `
          <div style="font-size:11px; padding:3px 0; display:flex; justify-content:space-between;">
            <span>Peer <b>${p.peer_ip}</b> (AS ${p.asn})</span>
            <span style="color:${p.state==='Established'?'var(--status-green)':'var(--status-red)'}; font-weight:600;">${p.state} (${p.prefixes_received} pfx)</span>
          </div>
        `).join("");
        html += `
          <div class="evidence-section">
            <div class="section-title">BGP Summary (eBGP AS 65005 &harr; 65001)</div>
            ${bgpRows}
          </div>
        `;
    }

    if (ev.rip && ev.rip.length > 0) {
        let ripRows = ev.rip.slice(0, 5).map(r => `
          <div style="font-size:11px; padding:2px 0;">
            <span>Route: <b>${r.network}</b> via ${r.next_hop} (${r.interface})</span>
          </div>
        `).join("");
        html += `
          <div class="evidence-section">
            <div class="section-title">RIPv2 Route Database</div>
            ${ripRows}
          </div>
        `;
    }

    if (ev.varp && ev.varp.vrrp && ev.varp.vrrp.length > 0) {
        let vrrpRows = ev.varp.vrrp.map(vr => `
          <div style="font-size:11px; padding:3px 0; display:flex; justify-content:space-between;">
            <span>Group ${vr.groupId} (${vr.interface}): ${vr.virtualIp || vr.virtualIpv6}</span>
            <span style="color:var(--status-green); font-weight:bold;">${vr.state.toUpperCase()}</span>
          </div>
        `).join("");
        html += `
          <div class="evidence-section">
            <div class="section-title">VARP Active-Active Gateway</div>
            <div style="font-size:11px; margin-bottom:4px; color:var(--accent-cyan);">Virtual MAC: ${ev.varp.varp.virtualMac || "00:1c:73:00:00:01"}</div>
            ${vrrpRows}
          </div>
        `;
    }

    // 4. Syslog Terminal
    const syslogLines = ev.syslog || [];
    html += `
      <div class="evidence-section">
        <div class="section-title">Recent System Logs (eAPI)</div>
        <div class="terminal-box">${syslogLines.join("<br>") || "No recent error events."}</div>
      </div>
    `;

    container.innerHTML = html;
}

// Incidents List & Deep Dive
async function loadIncidents() {
    try {
        const res = await fetch("/api/incidents");
        const incidents = await res.json();
        renderIncidentList(incidents);

        const openCount = incidents.filter(i => i.status === "open" || i.status === "investigating").length;
        const badge = document.getElementById("header-incident-badge");
        if (openCount > 0) {
            badge.className = "stat-badge badge-red";
            badge.textContent = `${openCount} INCIDENT${openCount>1?'S':''} ACTIVE`;
        } else {
            badge.className = "stat-badge badge-green";
            badge.textContent = "NETWORK HEALTHY";
        }
    } catch (e) {
        console.error("Failed to load incidents:", e);
    }
}

function renderIncidentList(incidents) {
    const list = document.getElementById("incident-list");
    if (incidents.length === 0) {
        list.innerHTML = `<div style="font-size:12px; color:var(--text-muted); text-align:center; padding:20px;">No active incidents. Network operating nominally.</div>`;
        return;
    }

    list.innerHTML = incidents.map(inc => {
        const isCritical = inc.severity === "critical";
        const hostsCount = (inc.blast_radius_hosts || []).length;
        return `
          <div class="incident-card ${inc.severity} ${selectedIncidentId === inc.id ? 'active' : ''}" onclick="selectIncident('${inc.id}')">
            <div class="incident-card-header">
              <span class="incident-id">${inc.id}</span>
              <span class="stat-badge ${isCritical ? 'badge-red' : 'badge-amber'}">${inc.severity.toUpperCase()}</span>
            </div>
            <div class="incident-title">${inc.title}</div>
            <div class="incident-meta">
              <span>Device: <b>${inc.root_cause_device}</b></span>
              <span class="blast-chip">${hostsCount} Hosts Impacted</span>
            </div>
          </div>
        `;
    }).join("");
}

async function selectIncident(incId) {
    selectedIncidentId = incId;
    switchTab("tab-incident");
    document.getElementById("incident-deep-dive").innerHTML = `<div style="color:var(--accent-cyan);">Loading incident analysis & evidence...</div>`;

    try {
        const res = await fetch(`/api/incidents/${incId}`);
        const inc = await res.json();
        renderIncidentDeepDive(inc);
    } catch (e) {
        document.getElementById("incident-deep-dive").innerHTML = `<div style="color:var(--status-red);">Error loading incident: ${e}</div>`;
    }
}

function renderIncidentDeepDive(inc) {
    const container = document.getElementById("incident-deep-dive");
    const blastHosts = inc.blast_radius_hosts || [];
    const blastSvcs = inc.blast_radius_services || [];
    const hypotheses = inc.hypotheses || [];
    const fix = inc.proposed_fix || {};
    const timeline = inc.timeline || [];

    let hypHtml = hypotheses.map((h, i) => `
      <div class="hypothesis-card">
        <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:700;">
          <span style="color:var(--accent-cyan);">Hypothesis #${i+1} (${Math.round(h.confidence*100)}% Confidence)</span>
          <span style="font-size:10px; color:var(--text-muted);">Citing: ${(h.evidence_ids||[]).join(", ")}</span>
        </div>
        <div style="font-size:12px; margin:4px 0;">${h.cause}</div>
        <div class="confidence-bar">
          <div class="confidence-fill" style="width:${Math.round(h.confidence*100)}%;"></div>
        </div>
        <div style="font-size:11px; color:var(--text-secondary);"><b>Next Test:</b> ${h.next_test}</div>
      </div>
    `).join("");

    let timelineHtml = timeline.map(t => `
      <div class="timeline-entry">
        <div class="timeline-dot"></div>
        <div class="timeline-time">${new Date(t.timestamp*1000).toLocaleTimeString()}</div>
        <div class="timeline-desc"><b>[${t.event_type.toUpperCase()}]</b> ${t.description}</div>
      </div>
    `).join("");

    const fixCmds = (fix.commands || []).join("\n");

    container.innerHTML = `
      <div class="evidence-section">
        <div class="section-title">
          <span>${inc.id}: ${inc.title}</span>
          <span class="stat-badge ${inc.status==='resolved'?'badge-green':(inc.status==='rollback'?'badge-amber':'badge-red')}">${inc.status.toUpperCase()}</span>
        </div>
        <div style="font-size:12px; line-height:1.4; margin-bottom:8px;">${inc.hypotheses[0]?.cause || inc.title}</div>
        <div style="font-size:11px; color:var(--text-secondary);">
          <div><b>Root-Cause Device:</b> ${inc.root_cause_device} | <b>Category:</b> ${inc.category}</div>
          <div style="margin-top:4px;"><b>Blast Radius Hosts:</b> ${blastHosts.join(", ") || "None"}</div>
          <div><b>Affected Services:</b> ${blastSvcs.join("; ") || "Local only"}</div>
        </div>
      </div>

      <div class="evidence-section">
        <div class="section-title">
          <span>Root-Cause Hypotheses (LLM Diagnosis)</span>
          <button class="btn-secondary" style="font-size:10px; padding:2px 8px;" onclick="reDiagnoseIncident('${inc.id}')">Re-Diagnose</button>
        </div>
        ${hypHtml || "<div>Running deterministic hypothesis builder...</div>"}
      </div>

      <div class="evidence-section">
        <div class="section-title">Proposed Closed-Loop Remediation</div>
        <div style="font-size:12px; color:var(--text-secondary);">${fix.description || "Restore nominal configuration state"}</div>
        <div class="code-box">${fixCmds || "! No configuration change required"}</div>
        <div style="font-size:11px; color:var(--text-muted); margin-bottom:10px;">
          Risk Level: <b style="color:var(--status-green);">${(fix.risk||"low").toUpperCase()}</b> | Pre-Verification Snapshot & Auto-Rollback Enabled
        </div>
        ${inc.status !== 'resolved' ? `
          <button class="btn-approve" onclick="approveRemediation('${inc.id}')">
            ✓ APPROVE & APPLY REMEDIATION (eAPI)
          </button>
        ` : `
          <div style="color:var(--status-green); font-weight:600; text-align:center; padding:8px; background:rgba(16,185,129,0.1); border-radius:6px;">
            ✓ REMEDIATION APPLIED & VERIFIED
          </div>
        `}
      </div>

      <div class="evidence-section">
        <div class="section-title">Incident Event Timeline</div>
        <div class="timeline-stream">${timelineHtml || "<div>No timeline events logged.</div>"}</div>
      </div>
    `;
}

async function reDiagnoseIncident(incId) {
    const btn = event.target;
    btn.textContent = "Analyzing...";
    try {
        const res = await fetch(`/api/incidents/${incId}/diagnose`, { method: "POST" });
        await selectIncident(incId);
    } catch (e) {
        alert("Diagnosis error: " + e);
    }
}

async function approveRemediation(incId) {
    const btn = event.target;
    btn.textContent = "Applying & Verifying via eAPI...";
    btn.disabled = true;

    try {
        const res = await fetch(`/api/incidents/${incId}/remediate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ operator: "student_netops" })
        });
        const result = await res.json();
        await selectIncident(incId);
        loadIncidents();
        loadTopology();
        alert(result.message);
    } catch (e) {
        alert("Remediation execution error: " + e);
    }
}

// Path Tracer Widget
function initPathTracer() {
    const btn = document.getElementById("btn-trace-path");
    btn.addEventListener("click", runPathTrace);
}

async function runPathTrace() {
    const select = document.getElementById("tracer-host-select");
    const host = select.value;
    const container = document.getElementById("hops-container");
    container.innerHTML = `<div style="color:var(--accent-cyan); font-size:12px;">Tracing hops to Web Server...</div>`;

    try {
        const res = await fetch(`/api/path?source=${host}&target=web-server`);
        const data = await res.json();
        renderPathTrace(data);
    } catch (e) {
        container.innerHTML = `<div style="color:var(--status-red); font-size:12px;">Trace failed: ${e}</div>`;
    }
}

function renderPathTrace(data) {
    const container = document.getElementById("hops-container");
    container.innerHTML = "";

    const hops = data.hops || [];
    hops.forEach(h => {
        const isFailed = (h.status === "failed");
        const isUnreachable = (h.status === "unreachable");

        let icon = "✓";
        let color = "var(--status-green)";
        if (isFailed) { icon = "✗"; color = "var(--status-red)"; }
        else if (isUnreachable) { icon = "⊘"; color = "var(--text-muted)"; }

        const div = document.createElement("div");
        div.className = `hop-item ${isFailed ? 'hop-failed' : ''}`;
        div.innerHTML = `
          <div class="hop-num" style="border:1px solid ${color}; color:${color};">${h.hop_number}</div>
          <div class="hop-nodes">
            <div>${h.node} &rarr; ${h.next_node}</div>
            <div style="font-size:10px; color:var(--text-muted); font-weight:normal;">${h.interface} &bull; ${h.reason}</div>
          </div>
          <div class="hop-status-icon" style="color:${color}; font-weight:bold;">${icon}</div>
        `;
        container.appendChild(div);
    });
}

// AI Copilot Chat Dock
function initChat() {
    const input = document.getElementById("chat-input");
    const sendBtn = document.getElementById("chat-send-btn");

    sendBtn.addEventListener("click", () => sendChatMessage());
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendChatMessage();
    });

    document.querySelectorAll(".quick-prompt-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            input.value = btn.dataset.prompt;
            sendChatMessage();
        });
    });
}

async function sendChatMessage() {
    const input = document.getElementById("chat-input");
    const msg = input.value.trim();
    if (!msg) return;

    input.value = "";
    appendChatBubble("user", msg);

    const msgsContainer = document.getElementById("chat-messages");
    const loadingBubble = appendChatBubble("bot", "Analyzing telemetry & calling read-only tools...");

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: msg,
                incident_id: selectedIncidentId,
                node: selectedNode
            })
        });
        const data = await res.json();
        loadingBubble.innerHTML = formatMarkdown(data.response);
        msgsContainer.scrollTop = msgsContainer.scrollHeight;
    } catch (e) {
        loadingBubble.innerHTML = `<span style="color:var(--status-red);">Chat error: ${e}</span>`;
    }
}

function appendChatBubble(sender, text) {
    const container = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = `chat-bubble ${sender}`;
    div.innerHTML = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
}

function formatMarkdown(text) {
    if (!text) return "";
    return text
        .replace(/\n/g, "<br>")
        .replace(/\*\*(.*?)\*\*/g, "<b>$1</b>")
        .replace(/`(.*?)`/g, "<code style='background:rgba(255,255,255,0.1); padding:2px 4px; border-radius:3px;'>$1</code>")
        .replace(/\[(EVID-[a-zA-Z0-9_-]+)\]/g, "<span class='stat-badge badge-cyan' style='cursor:pointer;'>$1</span>");
}

// Demo Bar
function initDemoBar() {
    document.querySelectorAll(".demo-btn[data-scenario]").forEach(btn => {
        btn.addEventListener("click", async () => {
            const sc = btn.dataset.scenario;
            btn.style.opacity = "0.5";
            try {
                await fetch("/api/demo/inject", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ scenario: sc })
                });
                await loadIncidents();
                await loadTopology();
                switchTab("tab-incident");
            } catch (e) {
                alert("Injection failed: " + e);
            } finally {
                btn.style.opacity = "1.0";
            }
        });
    });

    document.getElementById("btn-clear-demo").addEventListener("click", async () => {
        const btn = document.getElementById("btn-clear-demo");
        btn.textContent = "Resetting...";
        try {
            await fetch("/api/demo/clear", { method: "POST" });
            await loadIncidents();
            await loadTopology();
            btn.textContent = "✓ Reset Done";
            setTimeout(() => { btn.textContent = "🔄 Reset Network"; }, 2000);
        } catch (e) {
            alert("Clear failed: " + e);
        }
    });

    document.getElementById("btn-scan-health").addEventListener("click", async () => {
        const btn = document.getElementById("btn-scan-health");
        btn.textContent = "Scanning...";
        await fetch("/api/engine/scan", { method: "POST" });
        await loadIncidents();
        await loadTopology();
        btn.textContent = "Scan Health";
    });
}
