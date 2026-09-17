import os
import json
import base64
import yaml
import difflib
import jinja2
import urllib.request
import subprocess
from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from .models import Device, GoldenConfig, TemplateModel

BASE_DIR = "/home/student/Desktop/lab1"
DATA_MODELS_DIR = os.path.join(BASE_DIR, "data_models")
GOLDEN_CONFIGS_DIR = os.path.join(BASE_DIR, "golden_configs")
ARISTA_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Arista")
NXOS_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Cisco_NXOS")
XRV_DIR = os.path.join(BASE_DIR, "Jinja2_templates_Cisco_XRv9k")
SONIC_DIR = os.path.join(BASE_DIR, "Jinja2_templates_SONiC")

def pull_live_config_from_node(device):
    """
    Pulls live running configuration from physical/container device.
    For Arista cEOS: uses eAPI over HTTP.
    For Linux containers: fetches active startup and network scripts.
    """
    name = device.name.lower()
    mgmt_ip = device.mgmt_ip.split('/')[0] if device.mgmt_ip else ""
    
    if device.vendor == 'arista':
        url = f"http://{mgmt_ip}/command-api"
        auth = base64.b64encode(b"admin:admin").decode("utf-8")
        payload = {
            "jsonrpc": "2.0",
            "method": "runCmds",
            "params": {
                "version": 1,
                "cmds": ["enable", "show running-config"],
                "format": "text"
            },
            "id": "nsot-pull"
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if "result" in res and len(res["result"]) > 1:
                    return True, res["result"][1]["output"]
        except Exception as e:
            # Fallback to local config file if eAPI timeout
            cfg_path = os.path.join(BASE_DIR, "configs", "ceos", f"{name}.cfg")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r") as f:
                    return True, f"! [Fallback from Local Storage]\n" + f.read()
            return False, f"Failed to pull live eAPI config: {str(e)}"
    
    elif device.vendor in ['cisco_nxos', 'cisco_xrv', 'sonic']:
        # Render simulated config from Jinja2 template
        template_file = device.template_name or "r1_r2.j2"
        tmpl_dir = ARISTA_DIR
        if device.vendor == 'cisco_nxos': tmpl_dir = NXOS_DIR
        elif device.vendor == 'cisco_xrv': tmpl_dir = XRV_DIR
        elif device.vendor == 'sonic': tmpl_dir = SONIC_DIR
        
        try:
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(tmpl_dir), trim_blocks=True, lstrip_blocks=True)
            template = env.get_template(template_file)
            data = yaml.safe_load(device.custom_config_yaml) if device.custom_config_yaml else {"hostname": device.name}
            rendered = template.render(data)
            return True, f"! [Simulated Running Config - {device.get_vendor_display()}]\n" + rendered
        except Exception as e:
            return False, f"Render error: {str(e)}"

    else:
        # Linux Hosts / NMAS / Web Server
        start_sh_path = os.path.join(BASE_DIR, "configs", name, "start.sh")
        if os.path.exists(start_sh_path):
            with open(start_sh_path, "r") as f:
                return True, f"#!/bin/bash\n# Live Container Startup Configuration for {name}\n\n" + f.read()
        return True, f"# Host/Server: {name}\n# IP: {device.private_ip}\n# Mgmt: {device.mgmt_ip}\n# Status: Online\n"

def dashboard_view(request):
    devices = Device.objects.all()
    device_type_filter = request.GET.get('type')
    vendor_filter = request.GET.get('vendor')
    search_query = request.GET.get('q')

    if device_type_filter:
        devices = devices.filter(device_type=device_type_filter)
    if vendor_filter:
        devices = devices.filter(vendor=vendor_filter)
    if search_query:
        devices = devices.filter(name__icontains=search_query)

    total_devices = Device.objects.count()
    online_count = Device.objects.filter(status='Online').count()
    golden_count = GoldenConfig.objects.count()
    template_count = TemplateModel.objects.count()

    context = {
        'devices': devices,
        'total_devices': total_devices,
        'online_count': online_count,
        'golden_count': golden_count,
        'template_count': template_count,
        'current_type': device_type_filter or 'all',
        'current_vendor': vendor_filter or 'all',
        'search_query': search_query or '',
    }
    return render(request, 'automation/dashboard.html', context)

def device_detail_view(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    golden_configs = device.golden_configs.all()[:10]
    
    context = {
        'device': device,
        'golden_configs': golden_configs,
    }
    return render(request, 'automation/device_detail.html', context)

def pull_device_config_view(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    success, config_output = pull_live_config_from_node(device)
    
    if success:
        device.running_config = config_output
        device.last_config_pulled_at = datetime.now()
        device.status = 'Online'
        device.save()
        messages.success(request, f"Successfully pulled live running configuration from {device.name.upper()}!")
    else:
        messages.error(request, f"Could not pull configuration from {device.name}: {config_output}")

    return redirect('device_detail', device_id=device.id)

def pull_all_configs_view(request):
    devices = Device.objects.all()
    success_count = 0
    for device in devices:
        success, config_output = pull_live_config_from_node(device)
        if success:
            device.running_config = config_output
            device.last_config_pulled_at = datetime.now()
            device.status = 'Online'
            device.save()
            success_count += 1

    messages.success(request, f"Batch operation complete: Pulled running configs for {success_count}/{devices.count()} devices.")
    return redirect('dashboard')

def save_golden_config_view(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    if not device.running_config:
        success, config_output = pull_live_config_from_node(device)
        if success:
            device.running_config = config_output
            device.save()
    
    now = datetime.now()
    tag = f"v{now.strftime('%Y%m%d_%H%M%S')}"
    note = request.POST.get('change_summary', f"Golden baseline snapshot created at {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    gc = GoldenConfig.objects.create(
        device=device,
        version_tag=tag,
        config_content=device.running_config or "! Empty running config",
        change_summary=note,
        created_by="Network Automation GUI"
    )

    # Also save to disk
    os.makedirs(GOLDEN_CONFIGS_DIR, exist_ok=True)
    disk_file = os.path.join(GOLDEN_CONFIGS_DIR, f"{device.name}_{tag}.cfg")
    with open(disk_file, "w") as f:
        f.write(gc.config_content)

    messages.success(request, f"Saved Golden Configuration snapshot for {device.name.upper()} ({tag}) to Source of Truth & disk.")
    return redirect('device_detail', device_id=device.id)

def add_device_view(request):
    templates = TemplateModel.objects.all()
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        device_type = request.POST.get('device_type', 'router')
        vendor = request.POST.get('vendor', 'arista')
        tier = request.POST.get('tier', 'distribution')
        role = request.POST.get('role', '')
        public_ip = request.POST.get('public_ip', '').strip() or None
        private_ip = request.POST.get('private_ip', '').strip() or None
        mgmt_ip = request.POST.get('mgmt_ip', '').strip() or None
        
        routing_protocols = request.POST.get('routing_protocols', '')
        bgp_asn = request.POST.get('bgp_asn', '')
        bgp_asn = int(bgp_asn) if bgp_asn.isdigit() else None
        router_id = request.POST.get('router_id', '').strip() or None
        interface_ips = request.POST.get('interface_ips', '')
        vlans = request.POST.get('vlans', '')
        template_name = request.POST.get('template_name', '')
        custom_yaml = request.POST.get('custom_config_yaml', '')

        if not name:
            messages.error(request, "Device name is required.")
            return render(request, 'automation/add_device.html', {'templates': templates})

        device = Device(
            name=name,
            device_type=device_type,
            vendor=vendor,
            tier=tier,
            role=role,
            public_ip=public_ip,
            private_ip=private_ip,
            mgmt_ip=mgmt_ip,
            routing_protocols=routing_protocols,
            bgp_asn=bgp_asn,
            router_id=router_id,
            interface_ips=interface_ips,
            vlans=vlans,
            template_name=template_name,
            custom_config_yaml=custom_yaml
        )

        if 'uploaded_config_file' in request.FILES:
            device.uploaded_config_file = request.FILES['uploaded_config_file']
            uploaded_text = device.uploaded_config_file.read().decode('utf-8', errors='ignore')
            device.running_config = uploaded_text

        if 'uploaded_template_file' in request.FILES:
            device.uploaded_template_file = request.FILES['uploaded_template_file']

        device.save()

        # Save initial YAML model if provided
        if custom_yaml:
            y_path = os.path.join(DATA_MODELS_DIR, f"{name}.yml")
            try:
                with open(y_path, "w") as f:
                    f.write(custom_yaml)
            except Exception:
                pass

        messages.success(request, f"New device {name.upper()} successfully provisioned into Network Source of Truth!")
        return redirect('device_detail', device_id=device.id)

    return render(request, 'automation/add_device.html', {'templates': templates})

def edit_device_view(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    templates = TemplateModel.objects.all()

    if request.method == 'POST':
        device.device_type = request.POST.get('device_type', device.device_type)
        device.vendor = request.POST.get('vendor', device.vendor)
        device.tier = request.POST.get('tier', device.tier)
        device.role = request.POST.get('role', device.role)
        device.public_ip = request.POST.get('public_ip', '').strip() or None
        device.private_ip = request.POST.get('private_ip', '').strip() or None
        device.mgmt_ip = request.POST.get('mgmt_ip', '').strip() or None
        device.routing_protocols = request.POST.get('routing_protocols', device.routing_protocols)
        
        bgp_asn = request.POST.get('bgp_asn', '')
        device.bgp_asn = int(bgp_asn) if bgp_asn.isdigit() else None
        device.router_id = request.POST.get('router_id', '').strip() or None
        device.interface_ips = request.POST.get('interface_ips', device.interface_ips)
        device.vlans = request.POST.get('vlans', device.vlans)
        device.template_name = request.POST.get('template_name', device.template_name)
        device.custom_config_yaml = request.POST.get('custom_config_yaml', device.custom_config_yaml)
        
        if 'uploaded_config_file' in request.FILES:
            device.uploaded_config_file = request.FILES['uploaded_config_file']
            device.running_config = device.uploaded_config_file.read().decode('utf-8', errors='ignore')

        device.save()
        messages.success(request, f"Device {device.name.upper()} configuration updated successfully.")
        return redirect('device_detail', device_id=device.id)

    return render(request, 'automation/edit_device.html', {'device': device, 'templates': templates})

def delete_device_view(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    name = device.name
    device.delete()
    messages.info(request, f"Device {name.upper()} was removed from the Network Source of Truth.")
    return redirect('dashboard')

def golden_configs_list_view(request):
    golden_configs = GoldenConfig.objects.select_related('device').all()
    selected_gc = None
    diff_output = None
    
    gc_id = request.GET.get('id')
    compare_id = request.GET.get('compare')
    
    if gc_id:
        selected_gc = get_object_or_404(GoldenConfig, id=gc_id)
        if compare_id:
            compare_gc = get_object_or_404(GoldenConfig, id=compare_id)
            lines1 = selected_gc.config_content.splitlines(keepends=True)
            lines2 = compare_gc.config_content.splitlines(keepends=True)
            diff = difflib.unified_diff(
                lines1, lines2,
                fromfile=f"{selected_gc.device.name}_{selected_gc.version_tag}",
                tofile=f"{compare_gc.device.name}_{compare_gc.version_tag}"
            )
            diff_output = "".join(diff)

    context = {
        'golden_configs': golden_configs,
        'selected_gc': selected_gc,
        'diff_output': diff_output,
    }
    return render(request, 'automation/golden_configs.html', context)

def templates_list_view(request):
    templates = TemplateModel.objects.all()
    vendor_filter = request.GET.get('vendor')
    if vendor_filter:
        templates = templates.filter(vendor=vendor_filter)

    context = {
        'templates': templates,
        'vendor_filter': vendor_filter or 'all',
    }
    return render(request, 'automation/templates_list.html', context)

def render_template_view(request):
    templates = TemplateModel.objects.all()
    devices = Device.objects.all()
    rendered_output = None
    error_msg = None
    
    selected_template_name = request.POST.get('template_name') or request.GET.get('template') or 'r1_r2.j2'
    selected_device_id = request.POST.get('device_id') or request.GET.get('device')
    yaml_input = request.POST.get('yaml_data', '')

    if not yaml_input and selected_device_id:
        dev = Device.objects.filter(id=selected_device_id).first()
        if dev and dev.custom_config_yaml:
            yaml_input = dev.custom_config_yaml

    if request.method == 'POST' or request.GET.get('auto_render'):
        try:
            # Search across all template directories
            tmpl_obj = TemplateModel.objects.filter(name=selected_template_name).first()
            if tmpl_obj:
                tmpl_content = tmpl_obj.content
            else:
                tmpl_content = ""
                for t_dir in [ARISTA_DIR, NXOS_DIR, XRV_DIR, SONIC_DIR]:
                    p = os.path.join(t_dir, selected_template_name)
                    if os.path.exists(p):
                        with open(p, "r") as f:
                            tmpl_content = f.read()
                        break
            
            if not tmpl_content:
                error_msg = f"Template {selected_template_name} not found."
            else:
                env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
                template = env.from_string(tmpl_content)
                data = yaml.safe_load(yaml_input) if yaml_input else {}
                rendered_output = template.render(data)
        except Exception as e:
            error_msg = f"Rendering error: {str(e)}"

    context = {
        'templates': templates,
        'devices': devices,
        'selected_template_name': selected_template_name,
        'selected_device_id': int(selected_device_id) if selected_device_id and str(selected_device_id).isdigit() else None,
        'yaml_input': yaml_input,
        'rendered_output': rendered_output,
        'error_msg': error_msg,
    }
    return render(request, 'automation/render_template.html', context)

def api_devices_view(request):
    devices = list(Device.objects.values('id', 'name', 'device_type', 'vendor', 'tier', 'role', 'public_ip', 'private_ip', 'mgmt_ip', 'status', 'routing_protocols', 'bgp_asn'))
    return JsonResponse({'status': 'success', 'count': len(devices), 'devices': devices})
