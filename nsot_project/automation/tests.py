import os
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.db.utils import IntegrityError

from automation.models import Device, GoldenConfig, TemplateModel, MaintenanceLog


class DeviceModelTests(TestCase):
    """Unit tests for the Device model, testing CRUD operations and constraints."""

    def setUp(self):
        self.device_data = {
            'name': 'test-r1',
            'device_type': 'router',
            'vendor': 'arista',
            'tier': 'distribution',
            'role': 'Distribution Router',
            'public_ip': '198.51.100.1',
            'private_ip': '10.10.10.1',
            'mgmt_ip': '172.20.20.11',
            'status': 'Online',
            'routing_protocols': 'OSPF, BGP',
            'bgp_asn': 65001,
            'router_id': '10.10.10.1',
            'interface_ips': 'Ethernet1: 10.0.0.1/24',
            'vlans': '10,20,30',
            'custom_config_yaml': 'hostname: test-r1\ninterfaces:\n  - name: Ethernet1\n',
            'template_name': 'r1_r2.j2'
        }

    def test_device_creation_positive(self):
        """Positive Test: Verify creating a Device with valid attributes succeeds."""
        device = Device.objects.create(**self.device_data)
        self.assertIsNotNone(device.id)
        self.assertEqual(device.name, 'test-r1')
        self.assertEqual(device.device_type, 'router')
        self.assertEqual(device.vendor, 'arista')
        self.assertEqual(device.bgp_asn, 65001)
        self.assertIn('test-r1', str(device))
        self.assertIn('Router', str(device))

    def test_device_unique_name_constraint_negative(self):
        """Negative Test: Verify creating duplicate device name raises IntegrityError."""
        Device.objects.create(**self.device_data)
        with self.assertRaises(IntegrityError):
            Device.objects.create(**self.device_data)

    def test_device_default_values_positive(self):
        """Positive Test: Verify default values are correctly populated on minimal creation."""
        minimal_dev = Device.objects.create(name='min-r2')
        self.assertEqual(minimal_dev.device_type, 'router')
        self.assertEqual(minimal_dev.vendor, 'arista')
        self.assertEqual(minimal_dev.status, 'Online')
        self.assertEqual(minimal_dev.template_name, 'r1_r2.j2')


class GoldenConfigModelTests(TestCase):
    """Unit tests for GoldenConfig baseline snapshots."""

    def setUp(self):
        self.device = Device.objects.create(
            name='r1',
            device_type='router',
            vendor='arista',
            mgmt_ip='172.20.20.11'
        )

    def test_golden_config_creation_positive(self):
        """Positive Test: Verify creating a GoldenConfig linked to a Device."""
        gc = GoldenConfig.objects.create(
            device=self.device,
            version_tag='v20261020_001',
            config_content='! Sample Golden Configuration\nhostname r1\n',
            change_summary='Initial Golden Baseline',
            created_by='Test Runner'
        )
        self.assertIsNotNone(gc.id)
        self.assertEqual(gc.device, self.device)
        self.assertEqual(gc.version_tag, 'v20261020_001')
        self.assertIn('r1', str(gc))
        self.assertIn('v20261020_001', str(gc))

    def test_golden_config_cascade_delete_positive(self):
        """Positive Test: Verify cascading deletion of golden configs when device is deleted."""
        GoldenConfig.objects.create(
            device=self.device,
            version_tag='v1',
            config_content='config'
        )
        self.assertEqual(GoldenConfig.objects.filter(device=self.device).count(), 1)
        self.device.delete()
        self.assertEqual(GoldenConfig.objects.count(), 0)

    def test_golden_config_null_device_negative(self):
        """Negative Test: Verify creating a GoldenConfig without a foreign key device raises IntegrityError."""
        with self.assertRaises(IntegrityError):
            GoldenConfig.objects.create(
                device=None,
                version_tag='v_invalid',
                config_content='config'
            )


class TemplateAndMaintenanceModelTests(TestCase):
    """Unit tests for TemplateModel and MaintenanceLog models."""

    def test_template_model_positive(self):
        """Positive Test: Create and read TemplateModel with valid attributes."""
        tmpl = TemplateModel.objects.create(
            name='custom_r1.j2',
            vendor='arista',
            tier='distribution',
            content='hostname {{ hostname }}',
            description='Test Arista Template'
        )
        self.assertIsNotNone(tmpl.id)
        self.assertIn('custom_r1.j2', str(tmpl))
        self.assertIn('arista', str(tmpl))

    def test_template_model_unique_name_negative(self):
        """Negative Test: Verify duplicate template names violate unique constraint."""
        TemplateModel.objects.create(name='dup.j2', vendor='arista', tier='distribution', content='x')
        with self.assertRaises(IntegrityError):
            TemplateModel.objects.create(name='dup.j2', vendor='arista', tier='distribution', content='y')

    def test_maintenance_log_creation_positive(self):
        """Positive Test: Verify creating and reading MaintenanceLog entries."""
        log = MaintenanceLog.objects.create(
            stage='Stage 1',
            action='drain_r1',
            target_device='R1',
            api_endpoint='http://172.20.20.11/command-api',
            api_command='router ospf 1\nmax-metric router-lsa',
            active_path='R2 (Failover Core)',
            ping_status='0% Loss',
            latency_ms=1.45,
            proof_message='OSPF cost adjusted successfully'
        )
        self.assertIsNotNone(log.id)
        self.assertEqual(log.target_device, 'R1')
        self.assertIn('drain_r1', str(log))
        self.assertIn('R2 (Failover Core)', str(log))


class DashboardViewTests(TestCase):
    """Unit tests for the NSoT Dashboard View (`/`)."""

    def setUp(self):
        self.client = Client()
        self.r1 = Device.objects.create(
            name='R1', device_type='router', vendor='arista',
            tier='distribution', mgmt_ip='172.20.20.11', status='Online'
        )
        self.s1 = Device.objects.create(
            name='S1', device_type='switch', vendor='arista',
            tier='access_switch', mgmt_ip='172.20.20.21', status='Online'
        )
        self.h1 = Device.objects.create(
            name='H1', device_type='host', vendor='linux',
            tier='host', mgmt_ip='172.20.20.101', status='Online'
        )

    @patch('automation.views.check_device_live_status', return_value='Online')
    def test_dashboard_get_positive(self, mock_status):
        """Positive Test: GET `/` returns HTTP 200 with dashboard context."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'automation/dashboard.html')
        self.assertEqual(response.context['total_devices'], 2)  # Filters router and switch
        self.assertEqual(response.context['online_count'], 2)
        self.assertContains(response, 'R1')
        self.assertContains(response, 'S1')

    @patch('automation.views.check_device_live_status', return_value='Online')
    def test_dashboard_filter_by_type_positive(self, mock_status):
        """Positive Test: GET `/?type=router` filters only router devices."""
        response = self.client.get(reverse('dashboard') + '?type=router')
        self.assertEqual(response.status_code, 200)
        devices = response.context['devices']
        self.assertEqual(devices.count(), 1)
        self.assertEqual(devices.first().name, 'R1')

    @patch('automation.views.check_device_live_status', return_value='Online')
    def test_dashboard_filter_by_vendor_positive(self, mock_status):
        """Positive Test: GET `/?vendor=arista` returns devices matching vendor."""
        response = self.client.get(reverse('dashboard') + '?vendor=arista')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['devices'].count(), 2)

    @patch('automation.views.check_device_live_status', return_value='Online')
    def test_dashboard_search_positive(self, mock_status):
        """Positive Test: GET `/?q=R1` returns matching device R1."""
        response = self.client.get(reverse('dashboard') + '?q=R1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['devices'].count(), 1)
        self.assertEqual(response.context['devices'].first().name, 'R1')

    @patch('automation.views.check_device_live_status', return_value='Online')
    def test_dashboard_search_negative(self, mock_status):
        """Negative Test: GET `/?q=NONEXISTENT_DEVICE` returns 200 with zero devices."""
        response = self.client.get(reverse('dashboard') + '?q=NONEXISTENT_DEVICE_XYZ')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['devices'].count(), 0)


class DeviceCRUDViewTests(TestCase):
    """Unit tests for adding, viewing, editing, and deleting devices in NSoT."""

    def setUp(self):
        self.client = Client()
        self.r1 = Device.objects.create(
            name='R1', device_type='router', vendor='arista',
            tier='distribution', mgmt_ip='172.20.20.11', status='Online',
            custom_config_yaml='hostname: R1'
        )

    def test_add_device_get_positive(self):
        """Positive Test: GET `/device/add/` returns HTTP 200 form."""
        response = self.client.get(reverse('add_device'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'automation/add_device.html')

    def test_add_device_post_valid_positive(self):
        """Positive Test: POST `/device/add/` with valid parameters creates device and redirects."""
        payload = {
            'name': 'R6',
            'device_type': 'router',
            'vendor': 'arista',
            'tier': 'distribution',
            'mgmt_ip': '172.20.20.16',
            'routing_protocols': 'OSPF',
            'bgp_asn': '65001',
            'router_id': '10.10.10.6',
            'custom_config_yaml': 'hostname: R6'
        }
        response = self.client.post(reverse('add_device'), data=payload)
        self.assertEqual(response.status_code, 302)
        created_dev = Device.objects.filter(name='R6').first()
        self.assertIsNotNone(created_dev)
        self.assertEqual(created_dev.bgp_asn, 65001)

    def test_add_device_post_missing_name_negative(self):
        """Negative Test: POST `/device/add/` with empty name fails validation and re-renders form."""
        payload = {
            'name': '',
            'device_type': 'router',
            'vendor': 'arista'
        }
        response = self.client.post(reverse('add_device'), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'automation/add_device.html')
        self.assertFalse(Device.objects.filter(name='').exists())

    @patch('automation.views.check_device_live_status', return_value='Online')
    def test_device_detail_get_positive(self, mock_status):
        """Positive Test: GET `/device/<id>/` for existing device returns HTTP 200 with details."""
        response = self.client.get(reverse('device_detail', kwargs={'device_id': self.r1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'automation/device_detail.html')
        self.assertEqual(response.context['device'], self.r1)

    def test_device_detail_get_nonexistent_negative(self):
        """Negative Test: GET `/device/99999/` for non-existent device returns HTTP 404."""
        response = self.client.get(reverse('device_detail', kwargs={'device_id': 99999}))
        self.assertEqual(response.status_code, 404)

    def test_edit_device_get_positive(self):
        """Positive Test: GET `/device/<id>/edit/` returns HTTP 200 with existing device values."""
        response = self.client.get(reverse('edit_device', kwargs={'device_id': self.r1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'automation/edit_device.html')
        self.assertEqual(response.context['device'], self.r1)

    def test_edit_device_post_valid_positive(self):
        """Positive Test: POST `/device/<id>/edit/` updates device fields and redirects."""
        payload = {
            'device_type': 'router',
            'vendor': 'arista',
            'tier': 'distribution',
            'mgmt_ip': '172.20.20.99',
            'routing_protocols': 'OSPF, BGP',
            'bgp_asn': '65099',
            'router_id': '10.99.99.1'
        }
        response = self.client.post(reverse('edit_device', kwargs={'device_id': self.r1.id}), data=payload)
        self.assertEqual(response.status_code, 302)
        self.r1.refresh_from_db()
        self.assertEqual(self.r1.mgmt_ip, '172.20.20.99')
        self.assertEqual(self.r1.bgp_asn, 65099)

    def test_edit_device_nonexistent_negative(self):
        """Negative Test: POST `/device/99999/edit/` returns HTTP 404."""
        response = self.client.post(reverse('edit_device', kwargs={'device_id': 99999}), data={})
        self.assertEqual(response.status_code, 404)

    def test_delete_device_positive(self):
        """Positive Test: GET/POST `/device/<id>/delete/` removes device from NSoT and redirects."""
        dev_id = self.r1.id
        response = self.client.post(reverse('delete_device', kwargs={'device_id': dev_id}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Device.objects.filter(id=dev_id).exists())

    def test_delete_device_nonexistent_negative(self):
        """Negative Test: Attempting to delete non-existent device returns HTTP 404."""
        response = self.client.post(reverse('delete_device', kwargs={'device_id': 99999}))
        self.assertEqual(response.status_code, 404)


class ConfigPullAndGoldenArchiveViewTests(TestCase):
    """Unit tests for eAPI config pulling, batch operations, and Golden Config snapshots."""

    def setUp(self):
        self.client = Client()
        self.r1 = Device.objects.create(
            name='R1', device_type='router', vendor='arista',
            mgmt_ip='172.20.20.11', status='Online', running_config='! Old Config'
        )

    @patch('automation.views.pull_live_config_from_node', return_value=(True, 'hostname R1\nrouter ospf 1'))
    @patch('automation.views.check_device_live_status', return_value='Online')
    def test_pull_device_config_success_positive(self, mock_status, mock_pull):
        """Positive Test: Successfully pulling live eAPI config updates database and redirects."""
        response = self.client.get(reverse('pull_device_config', kwargs={'device_id': self.r1.id}))
        self.assertEqual(response.status_code, 302)
        self.r1.refresh_from_db()
        self.assertEqual(self.r1.running_config, 'hostname R1\nrouter ospf 1')
        self.assertEqual(self.r1.status, 'Online')

    @patch('automation.views.pull_live_config_from_node', return_value=(False, 'Connection Timeout'))
    def test_pull_device_config_failure_negative(self, mock_pull):
        """Negative Test: Failed eAPI pull marks device as Offline and handles error gracefully."""
        response = self.client.get(reverse('pull_device_config', kwargs={'device_id': self.r1.id}))
        self.assertEqual(response.status_code, 302)
        self.r1.refresh_from_db()
        self.assertEqual(self.r1.status, 'Offline')

    def test_pull_device_config_nonexistent_negative(self):
        """Negative Test: Pull config on non-existent device returns HTTP 404."""
        response = self.client.get(reverse('pull_device_config', kwargs={'device_id': 99999}))
        self.assertEqual(response.status_code, 404)

    @patch('automation.views.pull_live_config_from_node', return_value=(True, '! Pulled Batch Config'))
    @patch('automation.views.check_device_live_status', return_value='Online')
    def test_pull_all_configs_positive(self, mock_status, mock_pull):
        """Positive Test: Batch pull across all inventory devices returns 302 with success message."""
        response = self.client.get(reverse('pull_all_configs'))
        self.assertEqual(response.status_code, 302)
        self.r1.refresh_from_db()
        self.assertEqual(self.r1.running_config, '! Pulled Batch Config')

    @patch('automation.views.pull_live_config_from_node', return_value=(True, '! Golden Baseline Running'))
    def test_save_golden_config_positive(self, mock_pull):
        """Positive Test: Saving golden baseline creates a GoldenConfig database record."""
        payload = {'change_summary': 'Audited Golden Config'}
        response = self.client.post(reverse('save_golden_config', kwargs={'device_id': self.r1.id}), data=payload)
        self.assertEqual(response.status_code, 302)
        gc = GoldenConfig.objects.filter(device=self.r1).first()
        self.assertIsNotNone(gc)
        self.assertEqual(gc.change_summary, 'Audited Golden Config')

    def test_save_golden_config_nonexistent_negative(self):
        """Negative Test: Saving golden config for non-existent device returns HTTP 404."""
        response = self.client.post(reverse('save_golden_config', kwargs={'device_id': 99999}), data={})
        self.assertEqual(response.status_code, 404)

    def test_golden_configs_list_view_positive(self):
        """Positive Test: GET `/golden-configs/` loads snapshot repository successfully."""
        gc1 = GoldenConfig.objects.create(device=self.r1, version_tag='v1', config_content='line1\nline2\n')
        gc2 = GoldenConfig.objects.create(device=self.r1, version_tag='v2', config_content='line1\nline2_modified\n')

        # Test listing
        response = self.client.get(reverse('golden_configs'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'automation/golden_configs.html')

        # Test selecting single snapshot
        response_sel = self.client.get(reverse('golden_configs') + f'?id={gc1.id}')
        self.assertEqual(response_sel.status_code, 200)
        self.assertEqual(response_sel.context['selected_gc'], gc1)

        # Test comparing two snapshots (Unified Diff)
        response_diff = self.client.get(reverse('golden_configs') + f'?id={gc1.id}&compare={gc2.id}')
        self.assertEqual(response_diff.status_code, 200)
        self.assertIsNotNone(response_diff.context['diff_output'])
        self.assertIn('-line2', response_diff.context['diff_output'])
        self.assertIn('+line2_modified', response_diff.context['diff_output'])

    def test_golden_configs_invalid_id_negative(self):
        """Negative Test: GET `/golden-configs/?id=99999` returns HTTP 404."""
        response = self.client.get(reverse('golden_configs') + '?id=99999')
        self.assertEqual(response.status_code, 404)


class TemplateAndStudioViewTests(TestCase):
    """Unit tests for Multi-Vendor Jinja2 Template Gallery and In-Browser Studio."""

    def setUp(self):
        self.client = Client()
        self.t1 = TemplateModel.objects.create(
            name='r1_r2.j2', vendor='arista', tier='distribution',
            content='hostname {{ hostname }}\nrouter ospf {{ ospf_id | default(1) }}\n'
        )
        self.t2 = TemplateModel.objects.create(
            name='cisco_s1.j2', vendor='cisco_nxos', tier='access_switch',
            content='hostname {{ hostname }}\nfeature interface-vlan\n'
        )

    def test_templates_list_positive(self):
        """Positive Test: GET `/templates/` renders template catalog."""
        response = self.client.get(reverse('templates_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'automation/templates_list.html')
        self.assertEqual(response.context['templates'].count(), 2)

    def test_templates_list_vendor_filter_positive(self):
        """Positive Test: GET `/templates/?vendor=arista` filters by vendor."""
        response = self.client.get(reverse('templates_list') + '?vendor=arista')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['templates'].count(), 1)
        self.assertEqual(response.context['templates'].first().name, 'r1_r2.j2')

    def test_templates_list_nonexistent_vendor_negative(self):
        """Negative Test: GET `/templates/?vendor=unknown` returns empty list."""
        response = self.client.get(reverse('templates_list') + '?vendor=unknown_vendor')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['templates'].count(), 0)

    def test_render_template_get_positive(self):
        """Positive Test: GET `/templates/render/` renders live renderer interface."""
        response = self.client.get(reverse('render_template'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'automation/render_template.html')

    def test_render_template_post_valid_positive(self):
        """Positive Test: POST valid template name and YAML renders expected configuration."""
        payload = {
            'template_name': 'r1_r2.j2',
            'yaml_data': 'hostname: Router-Alpha\nospf_id: 10\n'
        }
        response = self.client.post(reverse('render_template'), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn('hostname Router-Alpha', response.context['rendered_output'])
        self.assertIn('router ospf 10', response.context['rendered_output'])
        self.assertIsNone(response.context['error_msg'])

    def test_render_template_missing_template_negative(self):
        """Negative Test: POST with non-existent template returns error message."""
        payload = {
            'template_name': 'nonexistent_template.j2',
            'yaml_data': 'hostname: test'
        }
        response = self.client.post(reverse('render_template'), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['error_msg'])
        self.assertIn('not found', response.context['error_msg'])

    def test_render_template_malformed_yaml_negative(self):
        """Negative Test: POST with invalid/malformed YAML syntax returns rendering error."""
        payload = {
            'template_name': 'r1_r2.j2',
            'yaml_data': 'invalid_yaml: [unclosed list'
        }
        response = self.client.post(reverse('render_template'), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['error_msg'])
        self.assertIn('Rendering error', response.context['error_msg'])


class RestApiAndConsoleViewTests(TestCase):
    """Unit tests for REST APIs, Web Console, and Command Execution endpoints."""

    def setUp(self):
        self.client = Client()
        self.r1 = Device.objects.create(
            name='R1', device_type='router', vendor='arista',
            mgmt_ip='172.20.20.11', status='Online'
        )

    def test_api_devices_get_positive(self):
        """Positive Test: GET `/api/devices/` returns JSON list of devices."""
        response = self.client.get(reverse('api_devices'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['devices'][0]['name'], 'R1')

    def test_device_console_view_positive(self):
        """Positive Test: GET `/console/` renders interactive terminal page."""
        response = self.client.get(reverse('device_console'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'automation/device_console.html')

    @patch('automation.views.call_router_eapi', return_value=(True, {'result': [{'output': 'Arista cEOSLab\n'}]}))
    def test_api_device_exec_cmd_positive(self, mock_eapi):
        """Positive Test: POST `/api/device/exec/` executes command via mocked eAPI and returns JSON."""
        payload = {
            'device': 'R1',
            'command': 'show version',
            'is_config': 'false'
        }
        response = self.client.post(reverse('api_device_exec_cmd'), data=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['device'], 'R1')
        self.assertIn('Arista cEOSLab', data['output'])

    def test_api_device_exec_cmd_get_negative(self):
        """Negative Test: GET `/api/device/exec/` is rejected with HTTP 405 Method Not Allowed."""
        response = self.client.get(reverse('api_device_exec_cmd'))
        self.assertEqual(response.status_code, 405)

    def test_api_device_exec_cmd_empty_command_negative(self):
        """Negative Test: POST `/api/device/exec/` with empty command returns HTTP 400 Bad Request."""
        payload = {'device': 'R1', 'command': ''}
        response = self.client.post(reverse('api_device_exec_cmd'), data=payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('cannot be empty', data['message'])

    @patch('automation.views.call_router_eapi', return_value=(False, {'error': 'eAPI Connection Refused'}))
    def test_api_device_exec_cmd_eapi_failure_negative(self, mock_eapi):
        """Negative Test: POST `/api/device/exec/` when eAPI fails returns HTTP 500 JSON error."""
        payload = {'device': 'R1', 'command': 'show version'}
        response = self.client.post(reverse('api_device_exec_cmd'), data=payload)
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Connection Refused', data['output'])

    def test_config_change_view_positive(self):
        """Positive Test: GET `/config/change/` renders Configuration Change Studio."""
        response = self.client.get(reverse('config_change'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'automation/config_change.html')

    def test_api_commit_and_pipeline_get_negative(self):
        """Negative Test: GET `/api/cicd/commit-change/` is rejected with HTTP 405."""
        response = self.client.get(reverse('api_commit_and_pipeline'))
        self.assertEqual(response.status_code, 405)

    def test_api_commit_and_pipeline_empty_commands_negative(self):
        """Negative Test: POST `/api/cicd/commit-change/` without commands returns HTTP 400."""
        payload = {'device': 'R1', 'config_commands': ''}
        response = self.client.post(reverse('api_commit_and_pipeline'), data=payload)
        self.assertEqual(response.status_code, 400)


class MaintenanceAndCicdViewTests(TestCase):
    """Unit tests for Maintenance Window, DR failover, and CI/CD diagnostic views."""

    def setUp(self):
        self.client = Client()
        self.r1 = Device.objects.create(name='R1', device_type='router', mgmt_ip='172.20.20.11', status='Online')
        self.r2 = Device.objects.create(name='R2', device_type='router', mgmt_ip='172.20.20.12', status='Online')

    def test_maintenance_view_positive(self):
        """Positive Test: GET `/maintenance/` renders Maintenance Mode & Disaster Recovery HUD."""
        response = self.client.get(reverse('maintenance'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'automation/maintenance.html')

    def test_maintenance_action_api_get_negative(self):
        """Negative Test: GET `/api/maintenance/action/` is rejected with HTTP 405."""
        response = self.client.get(reverse('maintenance_action_api'))
        self.assertEqual(response.status_code, 405)

    def test_maintenance_action_api_invalid_action_negative(self):
        """Negative Test: POST `/api/maintenance/action/` with invalid action returns HTTP 400."""
        response = self.client.post(reverse('maintenance_action_api'), data={'action': 'invalid_unknown_action'})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')

    def test_cicd_view_positive(self):
        """Positive Test: GET `/cicd/` renders NetDevOps CI/CD dashboard."""
        response = self.client.get(reverse('cicd_pipeline'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'automation/cicd_pipeline.html')

    @patch('subprocess.run')
    def test_api_run_cicd_positive(self, mock_sub):
        """Positive Test: POST `/api/cicd/run/` triggers CI/CD pipeline and returns JSON status."""
        mock_sub.return_value = MagicMock(returncode=0, stdout='Pipeline completed successfully', stderr='')
        response = self.client.post(reverse('api_run_cicd'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(data['status'], ['success', 'warning'])

    @patch('subprocess.run')
    def test_api_golden_audit_positive(self, mock_sub):
        """Positive Test: GET `/api/cicd/golden-audit/` returns audit JSON."""
        mock_sub.return_value = MagicMock(returncode=0, stdout=json.dumps({'R1': {'drift': False}}), stderr='')
        response = self.client.get(reverse('api_golden_audit'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('devices', data)

    @patch('subprocess.run')
    def test_api_golden_audit_failure_negative(self, mock_sub):
        """Negative Test: Subprocess error in `/api/cicd/golden-audit/` returns HTTP 500."""
        mock_sub.return_value = MagicMock(returncode=1, stdout='', stderr='Audit script crashed')
        response = self.client.get(reverse('api_golden_audit'))
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['status'], 'error')

    @patch('subprocess.run')
    def test_api_telemetry_positive(self, mock_sub):
        """Positive Test: GET `/api/cicd/telemetry/` returns telemetry JSON."""
        mock_sub.return_value = MagicMock(returncode=0, stdout=json.dumps({'R1': {'cpu': '5%'}}), stderr='')
        response = self.client.get(reverse('api_telemetry'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('telemetry', data)

    @patch('subprocess.run')
    def test_api_telemetry_failure_negative(self, mock_sub):
        """Negative Test: Telemetry collector timeout returns HTTP 504."""
        import subprocess
        mock_sub.side_effect = subprocess.TimeoutExpired(cmd='telemetry', timeout=30)
        response = self.client.get(reverse('api_telemetry'))
        self.assertEqual(response.status_code, 504)
        data = response.json()
        self.assertEqual(data['status'], 'error')

    @patch('subprocess.run')
    def test_api_troubleshoot_positive(self, mock_sub):
        """Positive Test: GET `/api/cicd/troubleshoot/` returns AI troubleshoot diagnostics JSON."""
        mock_sub.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({'status': 'HEALTHY', 'summary': 'All systems green'}),
            stderr=''
        )
        response = self.client.get(reverse('api_troubleshoot'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('report', data)
        self.assertEqual(data['report']['status'], 'HEALTHY')

    @patch('subprocess.run')
    def test_api_troubleshoot_failure_negative(self, mock_sub):
        """Negative Test: AI troubleshooting engine failure returns HTTP 500."""
        mock_sub.return_value = MagicMock(returncode=1, stdout='', stderr='Engine failure')
        response = self.client.get(reverse('api_troubleshoot'))
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['status'], 'error')


class CoreLogicAndMaintenanceExtendedTests(TestCase):
    """Extended unit tests covering live config pulling, status checks, and maintenance actions."""

    def setUp(self):
        self.client = Client()
        self.arista_dev = Device.objects.create(
            name='R1', device_type='router', vendor='arista',
            mgmt_ip='172.20.20.11', status='Online',
            custom_config_yaml='hostname: R1'
        )
        self.cisco_dev = Device.objects.create(
            name='S1', device_type='switch', vendor='cisco_nxos',
            mgmt_ip='172.20.20.21', status='Online',
            template_name='cisco_nxos_s1_s2.j2',
            custom_config_yaml='hostname: S1\nmgmt_ip: 172.20.20.21\nvlans:\n  - id: 10\n    name: DEV\nports:\n  - cisco_name: Ethernet1/1\n    description: Uplink\n    mode: trunk\n    allowed_vlans: "10,20"\n'
        )

    @patch('urllib.request.urlopen')
    def test_pull_live_config_arista_success_positive(self, mock_urlopen):
        """Positive Test: pull_live_config_from_node parses eAPI output successfully."""
        from automation.views import pull_live_config_from_node
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            'result': [{}, {'output': '! Arista Running Config\nhostname R1'}]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        ok, out = pull_live_config_from_node(self.arista_dev)
        self.assertTrue(ok)
        self.assertIn('hostname R1', out)

    @patch('urllib.request.urlopen', side_effect=Exception('Connection refused'))
    def test_pull_live_config_arista_exception_negative(self, mock_urlopen):
        """Negative Test: pull_live_config_from_node handles eAPI exceptions gracefully."""
        from automation.views import pull_live_config_from_node
        dev_unknown = Device.objects.create(name='UNKNOWN_R99', vendor='arista', mgmt_ip='172.20.20.99')
        ok, out = pull_live_config_from_node(dev_unknown)
        self.assertFalse(ok)
        self.assertIn('Failed to pull live eAPI config', out)

    def test_pull_live_config_cisco_render_positive(self):
        """Positive Test: Simulated multi-vendor render for Cisco NX-OS devices."""
        from automation.views import pull_live_config_from_node
        ok, out = pull_live_config_from_node(self.cisco_dev)
        self.assertTrue(ok)
        self.assertIn('hostname S1', out)

    def test_check_device_live_status_offline_no_ip_negative(self):
        """Negative Test: check_device_live_status returns Offline when management IP is missing."""
        from automation.views import check_device_live_status
        dev_no_ip = Device.objects.create(name='R_NO_IP', device_type='router', vendor='arista', mgmt_ip='')
        status = check_device_live_status(dev_no_ip)
        self.assertEqual(status, 'Offline')

    @patch('urllib.request.urlopen')
    def test_check_device_live_status_arista_healthy_positive(self, mock_urlopen):
        """Positive Test: check_device_live_status returns Online when eAPI reports nominal state."""
        from automation.views import check_device_live_status
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            'result': [
                {},
                {'output': 'Et1 connected\nEt2 connected'},
                {'output': 'router ospf 1\n redistribute connected'},
                {'output': 'vrrp 10 state Master'}
            ]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        status = check_device_live_status(self.arista_dev)
        self.assertEqual(status, 'Online')

    @patch('urllib.request.urlopen')
    def test_check_device_live_status_arista_drained_positive(self, mock_urlopen):
        """Positive Test: check_device_live_status returns Drained when maintenance mode is active."""
        from automation.views import check_device_live_status
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            'result': [
                {},
                {'output': 'Et1 connected\nEt2 disabled'},
                {'output': 'router ospf 1'},
                {'output': 'vrrp 10 state Backup'}
            ]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        status = check_device_live_status(self.arista_dev)
        self.assertEqual(status, 'Drained')

    @patch('automation.views.call_router_eapi', return_value=(True, {'result': [{'output': 'Config applied'}]}))
    def test_api_device_exec_cmd_config_mode_positive(self, mock_eapi):
        """Positive Test: api_device_exec_cmd in is_config=true mode wraps commands with enable/configure."""
        payload = {
            'device': 'R1',
            'command': 'interface Loopback100\ndescription Test',
            'is_config': 'true'
        }
        response = self.client.post(reverse('api_device_exec_cmd'), data=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

    @patch('automation.views.call_router_eapi', return_value=(True, {}))
    @patch('automation.views.run_host_pings', return_value={'success': True, 'overall_loss_pct': 0.0, 'overall_latency_ms': 1.2, 'summary': '0% Loss'})
    def test_maintenance_action_drain_r2_soft_positive(self, mock_pings, mock_eapi):
        """Positive Test: maintenance_action_api executes soft drain for R2 without errors."""
        payload = json.dumps({'action': 'drain_r2_soft'})
        response = self.client.post(
            reverse('maintenance_action_api'),
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('stage', data)

    @patch('automation.views.call_router_eapi', return_value=(True, {}))
    @patch('automation.views.run_host_pings', return_value={'success': True, 'overall_loss_pct': 0.0, 'overall_latency_ms': 1.0, 'summary': '0% Loss'})
    def test_maintenance_action_restore_r1_soft_positive(self, mock_pings, mock_eapi):
        """Positive Test: maintenance_action_api executes restore_r1_soft for R1."""
        payload = json.dumps({'action': 'restore_r1_soft'})
        response = self.client.post(
            reverse('maintenance_action_api'),
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

    @patch('automation.views.get_cluster_failover_status')
    def test_maintenance_status_api_positive(self, mock_status):
        """Positive Test: maintenance_status_api returns cluster state and metrics."""
        mock_status.return_value = {
            'cluster_active_path': 'R1 (Primary Active Core)',
            'vrrp_state': 'R1 Master / R2 Backup',
            'ospf_state': 'Normal Metrics',
            'bgp_state': 'Direct AS-Path',
            'r1_status': 'Online',
            'r2_status': 'Online',
            'dhcp_state': 'Active on R1',
            'pings': {'packet_loss': '0%', 'avg_latency_ms': 1.1}
        }
        response = self.client.get(reverse('maintenance_status_api'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('cluster_active_path', data['cluster'])

    @patch('automation.views.call_router_eapi')
    @patch('subprocess.run')
    def test_api_commit_and_pipeline_success_positive(self, mock_sub, mock_eapi):
        """Positive Test: api_commit_and_pipeline applies config, commits, and returns JSON."""
        mock_eapi.side_effect = [
            (True, {'result': []}),  # Configuration push
            (True, {'result': [{}, {'output': 'hostname R1\ninterface Loopback99'}]})  # Running config pull
        ]
        mock_sub.return_value = MagicMock(returncode=0, stdout='[main 1234abc] commit message', stderr='')

        payload = {
            'device': 'R1',
            'config_commands': 'interface Loopback99\ndescription Test-Loopback',
            'commit_message': 'feat(r1): add loopback99 interface'
        }
        response = self.client.post(reverse('api_commit_and_pipeline'), data=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

    @patch('automation.views.call_router_eapi', return_value=(False, {'error': 'Syntax Error at line 2'}))
    def test_api_commit_and_pipeline_eapi_failure_negative(self, mock_eapi):
        """Negative Test: api_commit_and_pipeline returns HTTP 500 when device rejects commands."""
        payload = {
            'device': 'R1',
            'config_commands': 'invalid syntax command here'
        }
        response = self.client.post(reverse('api_commit_and_pipeline'), data=payload)
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertFalse(data['deploy_ready'])

    def test_add_device_with_uploaded_files_positive(self):
        """Positive Test: Adding device with uploaded config and template files."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        config_file = SimpleUploadedFile("r99.cfg", b"hostname r99\n", content_type="text/plain")
        template_file = SimpleUploadedFile("r99.j2", b"hostname {{ name }}\n", content_type="text/plain")

        payload = {
            'name': 'R99',
            'device_type': 'router',
            'vendor': 'arista',
            'tier': 'distribution',
            'uploaded_config_file': config_file,
            'uploaded_template_file': template_file
        }
        response = self.client.post(reverse('add_device'), data=payload)
        self.assertEqual(response.status_code, 302)
        dev = Device.objects.filter(name='R99').first()
        self.assertIsNotNone(dev)
        self.assertIn('hostname r99', dev.running_config)

    def test_render_template_with_device_autofill_positive(self):
        """Positive Test: Loading template rendering with device autofill."""
        TemplateModel.objects.create(name='r1_r2.j2', vendor='arista', tier='distribution', content='hostname {{ hostname }}')
        response = self.client.get(reverse('render_template') + f'?template=r1_r2.j2&device={self.arista_dev.id}&auto_render=true')
        self.assertEqual(response.status_code, 200)
        self.assertIn('hostname R1', response.context['rendered_output'])

    @patch('subprocess.run')
    def test_run_host_pings_success_positive(self, mock_sub):
        """Positive Test: run_host_pings calculates packet loss and latency correctly."""
        from automation.views import run_host_pings
        mock_sub.return_value = MagicMock(
            returncode=0,
            stdout="3 packets transmitted, 3 received, 0% packet loss, time 2002ms\nrtt min/avg/max/mdev = 1.200/1.500/1.800/0.200 ms\n"
        )
        res = run_host_pings(count=3)
        self.assertTrue(res['success'])
        self.assertEqual(res['overall_loss_pct'], 0.0)
        self.assertEqual(res['overall_latency_ms'], 1.5)

    @patch('subprocess.run')
    def test_run_host_pings_timeout_negative(self, mock_sub):
        """Negative Test: run_host_pings handles packet loss with 100% loss and success=False."""
        from automation.views import run_host_pings
        mock_sub.return_value = MagicMock(returncode=1, stdout='', stderr='Network is unreachable')
        res = run_host_pings(count=3)
        self.assertFalse(res['success'])
        self.assertEqual(res['overall_loss_pct'], 100.0)

    @patch('automation.views.call_router_eapi')
    @patch('automation.views.run_host_pings', return_value={'success': True, 'overall_loss_pct': 0.0, 'overall_latency_ms': 1.1, 'summary': '0% Loss'})
    def test_maintenance_actions_all_variants_positive(self, mock_pings, mock_eapi):
        """Positive Tests: Execute all maintenance actions (drain_r1_soft, hard downs, restores)."""
        mock_eapi.return_value = (True, {'result': []})
        actions = [
            'drain_r1_soft',
            'restore_r1_soft',
            'restore_r2_soft',
            'r2_down',
            'r2_up',
            'r1_down',
            'r1_up',
            'restore_all_normal',
            'run_probe'
        ]
        for act in actions:
            payload = json.dumps({'action': act})
            response = self.client.post(
                reverse('maintenance_action_api'),
                data=payload,
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200, f"Failed for action: {act}")
            data = response.json()
            self.assertEqual(data['status'], 'success', f"Expected success for {act}")

    @patch('automation.views.call_router_eapi')
    def test_get_cluster_failover_status_direct_positive(self, mock_eapi):
        """Positive Test: get_cluster_failover_status queries eAPI and constructs failover metrics."""
        from automation.views import get_cluster_failover_status
        r1_result = {
            'result': [
                {},
                {'output': 'Et2 connected'},
                {'output': 'vrrp 10 state Master'},
                {'output': 'router ospf 1\n redistribute connected'},
                {'output': 'Et1 100 12.5 10 15.0 100 12.5 10 15.0\nEt2 100 12.5 10 15.0 100 12.5 10 15.0'}
            ]
        }
        r2_result = {
            'result': [
                {},
                {'output': 'Et2 connected'},
                {'output': 'vrrp 10 state Backup'},
                {'output': 'router ospf 1\n redistribute connected'},
                {'output': 'Et1 10 1.5 2 2.0 10 1.5 2 2.0\nEt2 10 1.5 2 2.0 10 1.5 2 2.0'}
            ]
        }
        mock_eapi.side_effect = [(True, r1_result), (True, r2_result)]
        status = get_cluster_failover_status()
        self.assertIn('active_path', status)
        self.assertTrue(status['r1']['online'])
        self.assertTrue(status['r2']['online'])
        self.assertEqual(status['r1']['vrrp_state'], 'Master')
        self.assertEqual(status['r2']['vrrp_state'], 'Backup')

