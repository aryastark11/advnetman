from django.db import models
import json

class Device(models.Model):
    DEVICE_TYPES = [
        ('router', 'Router'),
        ('switch', 'Switch'),
        ('host', 'Host'),
        ('nmas', 'NMAS Station'),
        ('server', 'Internet Web Server'),
        ('backup', 'Backup Node'),
    ]

    VENDORS = [
        ('arista', 'Arista cEOS'),
        ('cisco_nxos', 'Cisco NX-OS 9000v'),
        ('cisco_xrv', 'Cisco IOS-XRv 9000'),
        ('sonic', 'SONiC VS (sonic-vs)'),
        ('linux', 'Linux Host / Server'),
    ]

    TIERS = [
        ('distribution', 'Tier 1: Distribution Routers (R1-R2)'),
        ('asbr', 'Tier 2: ASBR Core Routers (R3-R4)'),
        ('pe_router', 'Tier 3: PE WAN Gateway (R5)'),
        ('access_switch', 'Tier 4: Access Switches (S1-S2)'),
        ('core_switch', 'Tier 5: Core Backbone Switches (S3-S4)'),
        ('host', 'End Host (H1-H4)'),
        ('management', 'Management & Automation'),
    ]

    name = models.CharField(max_length=64, unique=True, verbose_name="Hostname / Device Name")
    device_type = models.CharField(max_length=32, choices=DEVICE_TYPES, default='router')
    vendor = models.CharField(max_length=64, choices=VENDORS, default='arista')
    tier = models.CharField(max_length=64, choices=TIERS, default='distribution')
    role = models.CharField(max_length=255, blank=True, verbose_name="Deployment Role")
    
    # IP Addressing
    public_ip = models.CharField(max_length=64, blank=True, null=True, verbose_name="Public / WAN IP")
    private_ip = models.CharField(max_length=64, blank=True, null=True, verbose_name="Private IP")
    mgmt_ip = models.CharField(max_length=64, blank=True, null=True, verbose_name="Management IP")
    status = models.CharField(max_length=32, default='Online')

    # Device Specific Configuration
    routing_protocols = models.CharField(max_length=128, blank=True, default="OSPF", verbose_name="Routing Protocol(s)")
    bgp_asn = models.IntegerField(blank=True, null=True, verbose_name="BGP Local ASN")
    router_id = models.CharField(max_length=64, blank=True, null=True, verbose_name="Router ID")
    interface_ips = models.TextField(blank=True, verbose_name="Interface IPs / Descriptions")
    vlans = models.CharField(max_length=128, blank=True, verbose_name="VLANs (e.g. 10,20,30)")

    # Data Model & Configuration
    custom_config_yaml = models.TextField(blank=True, verbose_name="YAML Data Model")
    running_config = models.TextField(blank=True, verbose_name="Live Running Configuration")
    template_name = models.CharField(max_length=128, blank=True, default="r1_r2.j2", verbose_name="Jinja2 Template File")

    # File Uploads
    uploaded_config_file = models.FileField(upload_to='uploaded_configs/', blank=True, null=True, verbose_name="Uploaded Running Config File")
    uploaded_template_file = models.FileField(upload_to='uploaded_templates/', blank=True, null=True, verbose_name="Uploaded Jinja2 Template File")

    last_config_pulled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_device_type_display()} - {self.get_vendor_display()})"


class GoldenConfig(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='golden_configs')
    version_tag = models.CharField(max_length=64)
    timestamp = models.DateTimeField(auto_now_add=True)
    config_content = models.TextField()
    change_summary = models.CharField(max_length=255, default="Baseline Golden Config Snapshot")
    created_by = models.CharField(max_length=64, default="Network Automation Engine")

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.device.name} - {self.version_tag} ({self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"


class TemplateModel(models.Model):
    name = models.CharField(max_length=128, unique=True)
    vendor = models.CharField(max_length=64)
    tier = models.CharField(max_length=64)
    content = models.TextField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['vendor', 'tier', 'name']

    def __str__(self):
        return f"[{self.vendor}] {self.name} ({self.tier})"
