#!/usr/bin/env python3
"""
Generates the Grafana NMAS Network Operations Dashboard with Device Dropdown (Template Variable).
Allows selecting devices individually (r1-r7, s1-s4, All) to display their respective metrics.
"""

import json
import os

true = True
false = False
null = None

DASHBOARD_FILE = "/home/student/Desktop/lab1/configs/grafana/dashboards/nmas_network_operations.json"

dashboard = {
  "annotations": {
    "list": [
      {
        "builtIn": 1,
        "datasource": "-- Grafana --",
        "enable": true,
        "hide": true,
        "name": "Annotations & Alerts",
        "type": "dashboard"
      }
    ]
  },
  "editable": true,
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
  "refresh": "5s",
  "schemaVersion": 38,
  "style": "dark",
  "tags": [
    "nmas",
    "telegraf",
    "influxdb",
    "snmp",
    "ztp",
    "multi-device"
  ],
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "timepicker": {
    "refresh_intervals": [
      "5s",
      "10s",
      "30s",
      "1m",
      "5m",
      "15m",
      "30m",
      "1h",
      "2h",
      "1d"
    ]
  },
  "timezone": "browser",
  "title": "NMAS Network Operations & Data Lake Dashboard",
  "uid": "nmas-noc-master",
  "version": 5,
  "templating": {
    "list": [
      {
        "allValue": ".*",
        "current": {
          "selected": True,
          "text": "All",
          "value": "$__all"
        },
        "description": "Select an individual device to view respective metrics",
        "hide": 0,
        "includeAll": True,
        "label": "Device",
        "multi": False,
        "name": "device",
        "options": [
          {"selected": True, "text": "All", "value": "$__all"},
          {"selected": False, "text": "r1", "value": "r1"},
          {"selected": False, "text": "r2", "value": "r2"},
          {"selected": False, "text": "r3", "value": "r3"},
          {"selected": False, "text": "r4", "value": "r4"},
          {"selected": False, "text": "r5", "value": "r5"},
          {"selected": False, "text": "r6", "value": "r6"},
          {"selected": False, "text": "r7", "value": "r7"},
          {"selected": False, "text": "s1", "value": "s1"},
          {"selected": False, "text": "s2", "value": "s2"},
          {"selected": False, "text": "s3", "value": "s3"},
          {"selected": False, "text": "s4", "value": "s4"}
        ],
        "query": "r1,r2,r3,r4,r5,r6,r7,s1,s2,s3,s4",
        "queryValue": "",
        "skipUrlSync": False,
        "type": "custom"
      }
    ]
  },
  "panels": [
    {
      "id": 999,
      "title": "",
      "type": "text",
      "gridPos": {"h": 2, "w": 24, "x": 0, "y": 0},
      "options": {
        "mode": "html",
        "content": "<div style=\"display:flex; justify-content:space-between; align-items:center; background:linear-gradient(90deg, #0b1120, #131d31); border:1px solid #27354f; border-radius:8px; padding:10px 20px;\"><div style=\"display:flex; align-items:center; gap:12px;\"><div style=\"background:linear-gradient(135deg, #06b6d4, #3b82f6); width:32px; height:32px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-weight:bold; color:#fff;\">RC</div><div><span style=\"font-size:16px; font-weight:700; color:#f1f5f9;\">NMAS Telemetry & Network Observability Operations</span><br/><span style=\"font-size:11px; color:#94a3b8;\">Telegraf & InfluxDB Data Lake Engine • Per-Device Interactive Filtering</span></div></div><div><a href=\"http://localhost:8000\" target=\"_self\" style=\"display:inline-flex; align-items:center; gap:8px; background:linear-gradient(135deg, #06b6d4, #3b82f6); color:#ffffff; font-weight:600; font-size:13px; padding:8px 18px; border-radius:6px; text-decoration:none; box-shadow:0 4px 12px rgba(6,182,212,0.35);\"><span>🏠 Back to Django NSoT GUI</span></a></div></div>"
      },
      "transparent": True
    },
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
      "gridPos": {"h": 4, "w": 4, "x": 0, "y": 3},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT count(last) FROM (SELECT last(cpu_utilization) FROM telegraf_snmp WHERE $timeFilter AND hostname =~ /^$device$/ GROUP BY hostname)",
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
      "gridPos": {"h": 4, "w": 4, "x": 4, "y": 3},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT count(cpu_utilization) FROM telegraf_snmp WHERE $timeFilter AND hostname =~ /^$device$/",
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
      "gridPos": {"h": 4, "w": 4, "x": 8, "y": 3},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT count(ifInOctets) FROM telegraf_interface_stats WHERE $timeFilter AND hostname =~ /^$device$/",
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
      "gridPos": {"h": 4, "w": 4, "x": 12, "y": 3},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT count(result_code) FROM device_ping WHERE $timeFilter AND hostname =~ /^$device$/",
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
      "gridPos": {"h": 4, "w": 4, "x": 16, "y": 3},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT last(cpu_utilization)*0 + 7 AS \"Retention\" FROM telegraf_snmp WHERE $timeFilter",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "thresholds": {"mode": "absolute", "steps": [{"color": "teal", "value": None}]},
          "unit": "d"
        }
      },
      "options": {
        "colorMode": "value",
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
      "gridPos": {"h": 4, "w": 4, "x": 20, "y": 3},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT count(uptime) FROM telegraf_snmp WHERE time > now() - 1m AND hostname =~ /^$device$/",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "thresholds": {
            "mode": "absolute",
            "steps": [{"color": "red", "value": None}, {"color": "green", "value": 1}]
          },
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
    {
      "collapsed": False,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 7},
      "id": 200,
      "title": "Device Health, CPU & Resource Monitoring ($device)",
      "type": "row"
    },
    {
      "id": 7,
      "title": "Real-Time Device CPU Load (%) - $device",
      "type": "gauge",
      "gridPos": {"h": 6, "w": 6, "x": 0, "y": 8},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT last(cpu_utilization) FROM telegraf_snmp WHERE $timeFilter AND hostname =~ /^$device$/ GROUP BY hostname",
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
      "id": 501,
      "title": "Live CPU & Memory Usage (%) - $device",
      "type": "gauge",
      "gridPos": {"h": 6, "w": 6, "x": 6, "y": 8},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT last(cpu_utilization) AS \"CPU Utilization\" FROM device_telemetry WHERE hostname =~ /^$device$/",
          "rawQuery": True,
          "refId": "A"
        },
        {
          "query": "SELECT last(mem_pct) AS \"Memory Utilization\" FROM device_telemetry WHERE hostname =~ /^$device$/",
          "rawQuery": True,
          "refId": "B"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "min": 0,
          "max": 100,
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
      "title": "CPU Load History ($device)",
      "type": "timeseries",
      "gridPos": {"h": 6, "w": 8, "x": 12, "y": 8},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT mean(cpu_utilization) FROM telegraf_snmp WHERE $timeFilter AND hostname =~ /^$device$/ GROUP BY time($__interval), hostname fill(linear)",
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
      "title": "Device System Uptime - $device",
      "type": "bargauge",
      "gridPos": {"h": 6, "w": 4, "x": 20, "y": 8},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT last(uptime)/100 FROM telegraf_snmp WHERE $timeFilter AND hostname =~ /^$device$/ GROUP BY hostname",
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
      "title": "Interface Traffic (Inbound / Outbound bps) - $device",
      "type": "timeseries",
      "gridPos": {"h": 7, "w": 24, "x": 0, "y": 14},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT non_negative_derivative(mean(ifInOctets), 1s) * 8 AS \"Inbound bps\", non_negative_derivative(mean(ifOutOctets), 1s) * 8 AS \"Outbound bps\" FROM telegraf_interface_stats WHERE $timeFilter AND hostname =~ /^$device$/ AND ifDescr =~ /Ethernet|Management|Tunnel/ GROUP BY time($__interval), hostname, ifDescr fill(null)",
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
    {
      "collapsed": False,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 21},
      "id": 300,
      "title": "ICMP Reachability & Firmware System Overview ($device)",
      "type": "row"
    },
    {
      "id": 11,
      "title": "ICMP Ping Response Latency - $device",
      "type": "timeseries",
      "gridPos": {"h": 6, "w": 12, "x": 0, "y": 22},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT mean(average_response_ms) FROM device_ping WHERE $timeFilter AND hostname =~ /^$device$/ GROUP BY time($__interval), hostname fill(null)",
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
      "title": "Device Firmware & System Overview - $device",
      "type": "table",
      "gridPos": {"h": 6, "w": 12, "x": 12, "y": 22},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT last(sys_descr) AS \"OS Version\", last(uptime)/8640000 AS \"Uptime Days\", last(cpu_utilization) AS \"CPU %\" FROM telegraf_snmp WHERE $timeFilter AND hostname =~ /^$device$/ GROUP BY hostname",
          "rawQuery": True,
          "refId": "A"
        }
      ]
    },
    {
      "collapsed": False,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 28},
      "id": 400,
      "title": "Live Interface Counters, Error Rates & Discards ($device)",
      "type": "row"
    },
    {
      "id": 13,
      "title": "Live Interface Counters & Port Statistics Table - $device",
      "type": "table",
      "gridPos": {"h": 8, "w": 14, "x": 0, "y": 29},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT last(ifOperStatus) AS \"Status\", last(ifInOctets) AS \"Inbound (Bytes)\", last(ifOutOctets) AS \"Outbound (Bytes)\", last(ifInErrors) AS \"In Errors\", last(ifOutErrors) AS \"Out Errors\", last(ifInDiscards) AS \"In Discards\", last(ifOutDiscards) AS \"Out Discards\" FROM telegraf_interface_stats WHERE $timeFilter AND hostname =~ /^$device$/ AND ifDescr =~ /Ethernet|Management|Tunnel/ GROUP BY hostname, ifDescr",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "custom": {"align": "auto", "displayMode": "auto"}
        },
        "overrides": [
          {
            "matcher": {"id": "byName", "options": "Status"},
            "properties": [
              {
                "id": "mappings",
                "value": [
                  {"options": {"1": {"color": "green", "index": 0, "text": "UP"}}, "type": "value"},
                  {"options": {"2": {"color": "red", "index": 1, "text": "DOWN"}}, "type": "value"}
                ]
              }
            ]
          }
        ]
      }
    },
    {
      "id": 14,
      "title": "Real-Time Interface Error & Discard Counter Trends - $device",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 10, "x": 14, "y": 29},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT non_negative_derivative(mean(ifInErrors), 10s) AS \"In Errors\", non_negative_derivative(mean(ifOutErrors), 10s) AS \"Out Errors\", non_negative_derivative(mean(ifInDiscards), 10s) AS \"In Discards\", non_negative_derivative(mean(ifOutDiscards), 10s) AS \"Out Discards\" FROM telegraf_interface_stats WHERE $timeFilter AND hostname =~ /^$device$/ AND ifDescr =~ /Ethernet|Management|Tunnel/ GROUP BY time($__interval), hostname fill(0)",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "custom": {"drawStyle": "line", "lineWidth": 2},
          "unit": "short"
        }
      }
    },
    {
      "collapsed": False,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 37},
      "id": 500,
      "title": "Control Plane, Routing & Telemetry Deep-Dive ($device)",
      "type": "row"
    },
    {
      "id": 502,
      "title": "Control Plane: OSPF Adjacency & Route Capacity - $device",
      "type": "stat",
      "gridPos": {"h": 6, "w": 6, "x": 0, "y": 38},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": 'SELECT last(ospf_neighbors) AS "OSPF Neighbors" FROM device_telemetry WHERE hostname =~ /^$device$/',
          "rawQuery": True,
          "refId": "A"
        },
        {
          "query": 'SELECT last(route_entries) AS "Active Routes (RIB)" FROM device_telemetry WHERE hostname =~ /^$device$/',
          "rawQuery": True,
          "refId": "B"
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
      "id": 503,
      "title": "Real-Time CPU & Memory Utilization History - $device",
      "type": "timeseries",
      "gridPos": {"h": 6, "w": 18, "x": 6, "y": 38},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT mean(cpu_utilization) AS \"CPU %\" FROM device_telemetry WHERE $timeFilter AND hostname =~ /^$device$/ GROUP BY time($__interval), hostname fill(linear)",
          "rawQuery": True,
          "refId": "A"
        },
        {
          "query": "SELECT mean(mem_pct) AS \"Memory %\" FROM device_telemetry WHERE $timeFilter AND hostname =~ /^$device$/ GROUP BY time($__interval), hostname fill(linear)",
          "rawQuery": True,
          "refId": "B"
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
      "id": 504,
      "title": "Live Port Statistics & Line Protocol Status - $device",
      "type": "table",
      "gridPos": {"h": 8, "w": 24, "x": 0, "y": 44},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT last(oper_status) AS \"Status\", last(in_octets) AS \"Inbound (Bytes)\", last(out_octets) AS \"Outbound (Bytes)\", last(in_errors) AS \"In Errors\", last(out_errors) AS \"Out Errors\" FROM device_interface_counters WHERE $timeFilter AND hostname =~ /^$device$/ GROUP BY hostname, interface",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "custom": {"align": "auto", "displayMode": "auto"}
        },
        "overrides": [
          {
            "matcher": {"id": "byName", "options": "Status"},
            "properties": [
              {
                "id": "mappings",
                "value": [
                  {"options": {"1": {"color": "green", "index": 0, "text": "UP"}}, "type": "value"},
                  {"options": {"2": {"color": "red", "index": 1, "text": "DOWN"}}, "type": "value"}
                ]
              }
            ]
          }
        ]
      }
    },
    {
      "id": 505,
      "title": "OSPF Neighbor Adjacency Matrix - $device",
      "type": "table",
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 52},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT last(neighbor_router_id) AS \"Neighbor Router ID\", last(interface) AS \"Interface\", last(area) AS \"OSPF Area\", last(dr_state) AS \"DR State\", last(status) AS \"Adjacency State\" FROM device_ospf_neighbors WHERE $timeFilter AND hostname =~ /^$device$/ GROUP BY hostname, neighbor_ip",
          "rawQuery": True,
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "custom": {"align": "auto", "displayMode": "auto"}
        },
        "overrides": [
          {
            "matcher": {"id": "byName", "options": "Adjacency State"},
            "properties": [
              {
                "id": "mappings",
                "value": [
                  {"options": {"FULL": {"color": "green", "index": 0, "text": "FULL"}}, "type": "value"},
                  {"options": {"2WAYS": {"color": "blue", "index": 1, "text": "2WAY"}}, "type": "value"},
                  {"options": {"DOWN": {"color": "red", "index": 2, "text": "DOWN"}}, "type": "value"}
                ]
              }
            ]
          }
        ]
      }
    },
    {
      "id": 506,
      "title": "Routing Information Base (RIB) Entries & Next-Hops - $device",
      "type": "table",
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 52},
      "datasource": "NMAS Data Lake (InfluxDB)",
      "targets": [
        {
          "query": "SELECT last(nexthop) AS \"Next-Hop Address\", last(protocol) AS \"Protocol / Type\", last(interface) AS \"Outgoing Interface\", last(metric) AS \"Metric\" FROM device_route_entries WHERE $timeFilter AND hostname =~ /^$device$/ GROUP BY hostname, destination",
          "rawQuery": True,
          "refId": "A"
        }
      ]
    }
  ]
}

with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
    json.dump(dashboard, f, indent=2)

print(f"[✓] Successfully generated Grafana dashboard with Device dropdown at: {DASHBOARD_FILE}")
print(f"    Total Panels: {len(dashboard['panels'])}")
print(f"    Variables: {[v['name'] for v in dashboard['templating']['list']]}")
