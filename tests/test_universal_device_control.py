"""Comprehensive Test Suite for ARIA Universal Device Control (AUDC).

Validates all 16 AUDC capability areas: Display & NVIDIA GPU, Audio & Sound,
Camera & Webcam, Wi-Fi & Network, Bluetooth & USB, Storage & Optimization,
Power & Battery, System Administration, Troubleshooter, Inventory,
and Option 7 Companion voice/text routing.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from electorn.computer_engine.controllers.display_controller import DisplayController
from electorn.computer_engine.controllers.audio_controller import AudioController
from electorn.computer_engine.controllers.camera_controller import CameraController
from electorn.computer_engine.controllers.network_controller import NetworkController
from electorn.computer_engine.controllers.bluetooth_controller import BluetoothController
from electorn.computer_engine.controllers.storage_controller import StorageController
from electorn.computer_engine.controllers.power_controller import PowerController
from electorn.computer_engine.controllers.system_admin import SystemAdminController
from electorn.computer_engine.controllers.troubleshooter import DeviceTroubleshooter
from electorn.computer_engine.controllers.device_inventory import DeviceInventory
from electorn.companion.supervisor import CompanionSupervisor
from electorn.companion.schema import CompanionConfig


class TestDisplayController(unittest.TestCase):
    def setUp(self):
        self.display = DisplayController()

    def test_get_display_info(self):
        info = self.display.get_display_info()
        self.assertTrue(info["success"])
        self.assertIn("controllers", info)
        self.assertIn("count", info)

    def test_gpu_info_structure(self):
        gpu = self.display.get_gpu_info()
        self.assertTrue(gpu["success"])
        self.assertIn("has_nvidia", gpu)
        self.assertIn("gpus", gpu)
        self.assertIn("processes", gpu)
        if gpu["has_nvidia"] and gpu["gpus"]:
            g = gpu["gpus"][0]
            self.assertIn("name", g)
            self.assertIn("temperature_c", g)
            self.assertIn("utilization_percent", g)

    def test_brightness_query(self):
        b = self.display.get_brightness()
        self.assertIn("success", b)
        if b["success"]:
            self.assertGreaterEqual(b["brightness"], 0)
            self.assertLessEqual(b["brightness"], 100)


class TestAudioController(unittest.TestCase):
    def setUp(self):
        self.audio = AudioController()

    def test_get_volume_and_mute(self):
        vol = self.audio.get_volume()
        self.assertTrue(vol["success"])
        self.assertIn("volume", vol)
        self.assertIn("muted", vol)
        self.assertGreaterEqual(vol["volume"], 0)
        self.assertLessEqual(vol["volume"], 100)

    def test_list_audio_devices(self):
        devs = self.audio.list_audio_devices()
        self.assertTrue(devs["success"])
        self.assertIn("devices", devs)
        self.assertIn("active_count", devs)

    def test_troubleshoot_audio(self):
        diag = self.audio.troubleshoot_audio()
        self.assertTrue(diag["success"])
        self.assertIn("status", diag)
        self.assertIn("issues", diag)
        self.assertIn("recommended_actions", diag)


class TestCameraController(unittest.TestCase):
    def setUp(self):
        self.camera = CameraController()

    def test_list_cameras(self):
        cams = self.camera.list_cameras()
        self.assertTrue(cams["success"])
        self.assertIn("cameras", cams)
        self.assertIn("available_count", cams)

    def test_check_camera_health(self):
        health = self.camera.check_camera_health()
        self.assertTrue(health["success"])
        self.assertIn("healthy", health)
        self.assertIn("issues", health)


class TestNetworkController(unittest.TestCase):
    def setUp(self):
        self.net = NetworkController()

    def test_wifi_status(self):
        w = self.net.get_wifi_status()
        self.assertIn("success", w)
        if w.get("connected"):
            self.assertIsNotNone(w.get("ssid"))
            self.assertGreaterEqual(w.get("signal_percent", 0), 0)

    def test_scan_wifi_networks(self):
        scan = self.net.scan_wifi_networks()
        self.assertTrue(scan["success"])
        self.assertIn("networks", scan)

    def test_ip_configuration(self):
        ip = self.net.get_ip_configuration()
        self.assertTrue(ip["success"])
        self.assertIn("primary_ip", ip)

    def test_ping_test(self):
        ping = self.net.ping_test(host="8.8.8.8", count=2)
        self.assertIn("reachable", ping)
        self.assertIn("packet_loss_percent", ping)

    def test_detect_vpn(self):
        vpn = self.net.detect_vpn()
        self.assertTrue(vpn["success"])
        self.assertIn("vpn_active", vpn)
        self.assertIn("active_vpns", vpn)


class TestBluetoothAndUSBController(unittest.TestCase):
    def setUp(self):
        self.bt = BluetoothController()

    def test_list_bluetooth_devices(self):
        res = self.bt.list_bluetooth_devices()
        self.assertTrue(res["success"])
        self.assertIn("devices", res)
        self.assertIn("total_paired", res)

    def test_list_usb_devices(self):
        res = self.bt.list_usb_devices()
        self.assertTrue(res["success"])
        self.assertIn("peripherals", res)
        self.assertIn("count", res)


class TestStorageController(unittest.TestCase):
    def setUp(self):
        self.storage = StorageController()

    def test_get_drive_overview(self):
        d = self.storage.get_drive_overview()
        self.assertTrue(d["success"])
        self.assertGreaterEqual(d["total_drives"], 1)
        c_drive = d["drives"][0]
        self.assertIn("total_gb", c_drive)
        self.assertIn("free_gb", c_drive)
        self.assertIn("percent_used", c_drive)

    def test_analyze_temp_files(self):
        temp = self.storage.analyze_temp_files()
        self.assertTrue(temp["success"])
        self.assertIn("temp_files_count", temp)
        self.assertIn("total_size_mb", temp)

    def test_clean_temp_files_dry_run(self):
        clean = self.storage.clean_temp_files(dry_run=True)
        self.assertTrue(clean["success"])
        self.assertEqual(clean.get("mode"), "dry_run")


class TestPowerController(unittest.TestCase):
    def setUp(self):
        self.power = PowerController()

    def test_get_battery_status(self):
        b = self.power.get_battery_status()
        self.assertTrue(b["success"])
        self.assertIn("has_battery", b)
        if b["has_battery"]:
            self.assertGreaterEqual(b["percent"], 0)
            self.assertIn("power_plugged", b)

    def test_get_power_scheme(self):
        scheme = self.power.get_power_scheme()
        self.assertIn("active_scheme", scheme)

    def test_shutdown_confirmation_guard(self):
        # Unconfirmed shutdown MUST be rejected
        res = self.power.shutdown(confirm=False)
        self.assertFalse(res["success"])
        self.assertTrue(res["requires_confirmation"])

    def test_restart_confirmation_guard(self):
        # Unconfirmed restart MUST be rejected
        res = self.power.restart(confirm=False)
        self.assertFalse(res["success"])
        self.assertTrue(res["requires_confirmation"])


class TestSystemAdminController(unittest.TestCase):
    def setUp(self):
        self.admin = SystemAdminController()

    def test_list_services(self):
        services = self.admin.list_services(["Audiosrv", "Spooler"])
        self.assertTrue(services["success"])
        self.assertIn("services", services)

    def test_check_service(self):
        res = self.admin.check_service("Audiosrv")
        self.assertTrue(res["success"])
        self.assertEqual(res["service"], "Audiosrv")

    def test_prohibited_powershell_commands(self):
        res = self.admin.execute_powershell("format C: /q", risk_level="destructive")
        self.assertFalse(res["success"])
        self.assertTrue(res.get("blocked", False))


class TestDeviceTroubleshooter(unittest.TestCase):
    def setUp(self):
        self.troubleshooter = DeviceTroubleshooter()

    def test_diagnose_system_performance(self):
        diag = self.troubleshooter.diagnose_system_performance()
        self.assertTrue(diag["success"])
        self.assertIn("overall_status", diag)
        self.assertIn("cpu_percent", diag)
        self.assertIn("memory_percent", diag)
        self.assertIn("findings", diag)
        self.assertIn("recommendations", diag)
        self.assertGreater(len(diag["recommendations"]), 0)


class TestDeviceInventory(unittest.TestCase):
    def setUp(self):
        self.inv = DeviceInventory()

    def test_get_full_inventory(self):
        cat = self.inv.get_full_inventory()
        self.assertTrue(cat["success"])
        self.assertIn("os", cat)
        self.assertIn("cpu", cat)
        self.assertIn("memory", cat)
        self.assertIn("gpu", cat)
        self.assertIn("display", cat)
        self.assertIn("audio", cat)
        self.assertIn("network", cat)
        self.assertIn("storage", cat)


class TestCompanionAudcRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = CompanionConfig()
        config.personality.user_name = "Harshan"
        config.voice_enabled = False
        mock_llm = MagicMock()
        mock_llm.ask.return_value = "I am Aria, your AI companion."
        cls.supervisor = CompanionSupervisor(config=config, llm_provider=mock_llm)

    def test_voice_gpu_query(self):
        reply = self.supervisor.process_user_input("check gpu status")
        self.assertIn("Harshan", reply)
        self.assertTrue("NVIDIA" in reply or "graphics" in reply or "telemetry" in reply or "RTX" in reply)

    def test_voice_screen_resolution(self):
        reply = self.supervisor.process_user_input("what is my screen resolution")
        self.assertIn("Harshan", reply)
        self.assertTrue("resolution" in reply or "display" in reply or "1920" in reply)

    def test_voice_volume_control(self):
        reply = self.supervisor.process_user_input("set volume to 65%")
        self.assertIn("Harshan", reply)
        self.assertIn("65%", reply)

    def test_voice_mute_control(self):
        reply = self.supervisor.process_user_input("mute audio")
        self.assertIn("Harshan", reply)
        self.assertIn("muted", reply.lower())

    def test_voice_unmute_control(self):
        reply = self.supervisor.process_user_input("unmute audio")
        self.assertIn("Harshan", reply)
        self.assertIn("unmuted", reply.lower())

    def test_voice_wifi_status(self):
        reply = self.supervisor.process_user_input("check wifi status")
        self.assertIn("Harshan", reply)
        self.assertTrue("Wi-Fi" in reply or "connected" in reply or "network" in reply)

    def test_voice_ping_test(self):
        reply = self.supervisor.process_user_input("test ping latency")
        self.assertIn("Harshan", reply)
        self.assertTrue("ms" in reply or "latency" in reply or "packet loss" in reply)

    def test_voice_battery_status(self):
        reply = self.supervisor.process_user_input("check battery status")
        self.assertIn("Harshan", reply)
        self.assertTrue("Battery" in reply or "power" in reply or "%" in reply)

    def test_voice_troubleshoot_laptop_slow(self):
        reply = self.supervisor.process_user_input("why is my laptop slow")
        self.assertIn("Harshan", reply)
        self.assertIn("CPU", reply)
        self.assertIn("RAM", reply)

    def test_voice_lock_workstation(self):
        with patch.object(self.supervisor.computer_engine.power, "lock_workstation", return_value={"success": True}):
            reply = self.supervisor.process_user_input("lock workstation")
            self.assertIn("Harshan", reply)
            self.assertIn("locked", reply.lower())

    def test_shutdown_confirmation_safety_dialogue(self):
        reply = self.supervisor.process_user_input("shutdown computer")
        self.assertIn("Harshan", reply)
        self.assertIn("confirmation required", reply)


if __name__ == "__main__":
    unittest.main()
