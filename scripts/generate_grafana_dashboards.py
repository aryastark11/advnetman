#!/usr/bin/env python3
import json
import os

DASHBOARD_DIR = "/home/student/Desktop/lab1/configs/grafana/dashboards"
os.makedirs(DASHBOARD_DIR, exist_ok=True)

dashboard = {
  "annotations": {
    "list": [
      {
        "builtIn": 1,
        "datasource": "-- Grafana --",
        "enable": True,
        "hide": True,
        "name": "Annotations & Alerts",
        "type": "dashboard"
      }
    ]
  },
  "editable": True,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 1,
  "id": None,
  "links": [
    {
      "asDropdown": False,
      "icon": "external link",
      "includeVars": False,
      "keepTime": False,
      "tags": [],
      "targetBlank": False,
      "title": "🏠 Back to Django NSoT GUI",
      "tooltip": "Navigate back to Django NSoT Network Management Portal (http://localhost:8000)",
      "type": "link",
      "url": "http://localhost:8000"
    }
  ],
  "liveNow": True,
  "panels": [
    {
      "id": 999,
      "title": "",
      "type": "text",
      "gridPos": {"h": 2, "w": 24, "x": 0, "y": 0},
      "options": {
        "mode": "html",
        "content": "<div style=\"display:flex; justify-content:space-between; align-items:center; background:linear-gradient(90deg, #0b1120, #131d31); border:1px solid #27354f; border-radius:8px; padding:10px 20px;\"><div style=\"display:flex; align-items:center; gap:12px;\"><div style=\"background:linear-gradient(135deg, #06b6d4, #3b82f6); width:32px; height:32px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-weight:bold; color:#fff;\">RC</div><div><span style=\"font-size:16px; font-weight:700; color:#f1f5f9;\">NMAS Telemetry & Network Observability Operations</span><br/><span style=\"font-size:11px; color:#94a3b8;\">Telegraf & InfluxDB Data Lake Engine</span></div></div><div><a href=\"http://localhost:8000\" target=\"_self\" style=\"display:inline-flex; align-items:center; gap:8px; background:linear-gradient(135deg, #06b6d4, #3b82f6); color:#ffffff; font-weight:600; font-size:13px; padding:8px 18px; border-radius:6px; text-decoration:none; box-shadow:0 4px 12px rgba(6,182,212,0.35);\"><span>🏠 Back to Django NSoT GUI</span></a></div></div>"
      },
      "transparent": True
    },
    # Header Banner / KPI Stat Panels
    {
      "collapsed": False,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 2},
      "id": 100,
      "title": "NMAS InfluxDB & Telegraf Infrastructure Summary",
      "type": "row"
    },
    {
      "id": 1,
      "title": "Active Monitored Nodes",
      "type": "stat",
      "gridPos": {"h": 4, "w": 4, "x": 0, "y": 1},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT count(distinct(hostname)) FROM telegraf_snmp WHERE $timeFilter",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "thresholds": {"mode": "absolute", "steps": [{"color": "blue", "value": None}]},
          "unit": "short"
        }
      },
      "options": {
        "colorMode": "value",
        "graphMode": "area",
        "justifyMode": "center",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "values": False}
      }
    },
    {
      "id": 2,
      "title": "Telegraf SNMP Metrics Ingested",
      "type": "stat",
      "gridPos": {"h": 4, "w": 4, "x": 4, "y": 1},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT count(cpu_utilization) FROM telegraf_snmp WHERE $timeFilter",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
          "unit": "short"
        }
      },
      "options": {
        "colorMode": "value",
        "graphMode": "area",
        "justifyMode": "center",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "values": False}
      }
    },
    {
      "id": 3,
      "title": "Interface Metrics Polled",
      "type": "stat",
      "gridPos": {"h": 4, "w": 4, "x": 8, "y": 1},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT count(ifInOctets) FROM telegraf_interface_stats WHERE $timeFilter",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "thresholds": {"mode": "absolute", "steps": [{"color": "purple", "value": None}]},
          "unit": "short"
        }
      },
      "options": {
        "colorMode": "value",
        "graphMode": "area",
        "justifyMode": "center",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "values": False}
      }
    },
    {
      "id": 4,
      "title": "ICMP Device Ping Checks",
      "type": "stat",
      "gridPos": {"h": 4, "w": 4, "x": 12, "y": 1},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT count(result_code) FROM device_ping WHERE $timeFilter",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "thresholds": {"mode": "absolute", "steps": [{"color": "orange", "value": None}]},
          "unit": "short"
        }
      },
      "options": {
        "colorMode": "value",
        "graphMode": "area",
        "justifyMode": "center",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "values": False}
      }
    },
    {
      "id": 5,
      "title": "InfluxDB 7-Day Retention",
      "type": "stat",
      "gridPos": {"h": 4, "w": 4, "x": 16, "y": 1},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT 7 FROM telegraf_snmp LIMIT 1",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
          "unit": "d"
        }
      },
      "options": {
        "colorMode": "background",
        "graphMode": "none",
        "justifyMode": "center",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "values": False}
      }
    },
    {
      "id": 6,
      "title": "Collector Engine Status",
      "type": "stat",
      "gridPos": {"h": 4, "w": 4, "x": 20, "y": 1},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT count(uptime) FROM telegraf_snmp WHERE time > now() - 1m",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "thresholds": {"mode": "absolute", "steps": [{"color": "teal", "value": None}]},
          "unit": "short"
        }
      },
      "options": {
        "colorMode": "background",
        "graphMode": "none",
        "justifyMode": "center",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "values": False}
      }
    },

    # Row 2: Telegraf SNMP Monitoring
    {
      "collapsed": False,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 5},
      "id": 200,
      "title": "Telegraf SNMP Monitoring & Device Health (Routers R1-R5, Switches S1-S4)",
      "type": "row"
    },
    {
      "id": 7,
      "title": "Real-Time Device CPU Load (%)",
      "type": "gauge",
      "gridPos": {"h": 6, "w": 8, "x": 0, "y": 6},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT last(cpu_utilization) FROM telegraf_snmp WHERE $timeFilter GROUP BY hostname",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "max": 100,
          "min": 0,
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {"color": "green", "value": None},
              {"color": "yellow", "value": 60},
              {"color": "red", "value": 85}
            ]
          },
          "unit": "percent"
        }
      },
      "options": {
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "values": False},
        "showThresholdLabels": False,
        "showThresholdMarkers": True
      }
    },
    {
      "id": 8,
      "title": "CPU Load History (Telegraf SNMP Timeseries)",
      "type": "timeseries",
      "gridPos": {"h": 6, "w": 10, "x": 8, "y": 6},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT mean(cpu_utilization) FROM telegraf_snmp WHERE $timeFilter GROUP BY time($__interval), hostname fill(linear)",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "custom": {
            "drawStyle": "line",
            "lineInterpolation": "smooth",
            "lineWidth": 2,
            "showPoints": "auto",
            "fillOpacity": 15
          },
          "unit": "percent",
          "min": 0,
          "max": 100
        }
      }
    },
    {
      "id": 9,
      "title": "Device System Uptime (Days / Hours)",
      "type": "bargauge",
      "gridPos": {"h": 6, "w": 6, "x": 18, "y": 6},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT last(uptime)/100 FROM telegraf_snmp WHERE $timeFilter GROUP BY hostname",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "palette-classic"},
          "unit": "s"
        }
      },
      "options": {
        "displayMode": "gradient",
        "orientation": "horizontal",
        "reduceOptions": {"calcs": ["lastNotNull"], "values": False}
      }
    },
    {
      "id": 10,
      "title": "Telegraf Interface Traffic (Inbound / Outbound bps)",
      "type": "timeseries",
      "gridPos": {"h": 6, "w": 24, "x": 0, "y": 12},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT non_negative_derivative(mean(ifInOctets), 1s) * 8 AS \"Inbound bps\", non_negative_derivative(mean(ifOutOctets), 1s) * 8 AS \"Outbound bps\" FROM telegraf_interface_stats WHERE $timeFilter AND ifDescr =~ /Ethernet/ GROUP BY time($__interval), hostname, ifDescr fill(null)",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "custom": {
            "drawStyle": "line",
            "lineInterpolation": "smooth",
            "lineWidth": 2,
            "fillOpacity": 10
          },
          "unit": "bps"
        }
      }
    },

    # Row 3: Reachability & InfluxDB Status
    {
      "collapsed": False,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 18},
      "id": 300,
      "title": "ICMP Device Reachability & Status Table",
      "type": "row"
    },
    {
      "id": 11,
      "title": "ICMP Ping Response Latency",
      "type": "timeseries",
      "gridPos": {"h": 6, "w": 12, "x": 0, "y": 19},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT mean(average_response_ms) FROM device_ping WHERE $timeFilter GROUP BY time($__interval), url fill(null)",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "custom": {
            "drawStyle": "line",
            "lineWidth": 2
          },
          "unit": "ms"
        }
      }
    },
    {
      "id": 12,
      "title": "Device Firmware & System Overview",
      "type": "table",
      "gridPos": {"h": 6, "w": 12, "x": 12, "y": 19},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT last(sys_descr) AS \"OS Version\", last(uptime)/8640000 AS \"Uptime Days\", last(cpu_utilization) AS \"CPU %\" FROM telegraf_snmp WHERE $timeFilter GROUP BY hostname",
          "rawQuery": True,
          "refId": "A"
        }
      ]
    }
  ],
  "refresh": "5s",
  "schemaVersion": 38,
  "style": "dark",
  "tags": ["nmas", "telegraf", "influxdb", "snmp"],
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "timepicker": {
    "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"]
  },
  "timezone": "browser",
  "title": "NMAS Network Operations & Data Lake Dashboard",
  "uid": "nmas-noc-master",
  "version": 2
}

with open(os.path.join(DASHBOARD_DIR, "nmas_network_operations.json"), "w", encoding="utf-8") as f:
    json.dump(dashboard, f, indent=2, ensure_ascii=False)

print("Grafana dashboard updated for Telegraf & InfluxDB architecture.")
