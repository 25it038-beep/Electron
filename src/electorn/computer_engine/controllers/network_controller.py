"""Network, Wi-Fi, and Connectivity Controller for Windows.

Provides Wi-Fi status inspection, network scanning, IP configuration discovery,
ping latency/loss diagnostics, and VPN detection.
Security Note: Strictly redacts all Wi-Fi security keys and credentials.
"""
from __future__ import annotations

import logging
import re
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NetworkController:
    """Manages Wi-Fi, Ethernet, network diagnostics, and connectivity checks."""

    def get_wifi_status(self) -> Dict[str, Any]:
        """Retrieve active Wi-Fi connection parameters (SSID, Signal, Band, Rates)."""
        cmd = ["netsh", "wlan", "show", "interfaces"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
            if res.returncode != 0:
                return {"success": False, "connected": False, "message": "No wireless interface found or wlan service stopped"}

            output = res.stdout
            connected = "State                  : connected" in output or "State : connected" in output or "connected" in output.lower()

            def extract_val(pattern: str) -> Optional[str]:
                match = re.search(pattern, output, re.IGNORECASE)
                return match.group(1).strip() if match else None

            ssid = extract_val(r"SSID\s*:\s*([^\r\n]+)")
            signal_str = extract_val(r"Signal\s*:\s*(\d+)%")
            signal = int(signal_str) if signal_str else None
            band = extract_val(r"Band\s*:\s*([^\r\n]+)")
            channel = extract_val(r"Channel\s*:\s*([^\r\n]+)")
            rx_rate = extract_val(r"Receive rate \(Mbps\)\s*:\s*([^\r\n]+)")
            tx_rate = extract_val(r"Transmit rate \(Mbps\)\s*:\s*([^\r\n]+)")
            adapter_desc = extract_val(r"Description\s*:\s*([^\r\n]+)")

            return {
                "success": True,
                "connected": connected and bool(ssid),
                "ssid": ssid,
                "signal_percent": signal,
                "band": band,
                "channel": channel,
                "rx_rate_mbps": rx_rate,
                "tx_rate_mbps": tx_rate,
                "adapter": adapter_desc,
            }
        except Exception as e:
            return {"success": False, "connected": False, "error": str(e)}

    def scan_wifi_networks(self) -> Dict[str, Any]:
        """Scan for available nearby Wi-Fi networks (SSIDs and signals). Never extracts passwords."""
        cmd = ["netsh", "wlan", "show", "networks", "mode=bssid"]
        networks: List[Dict[str, Any]] = []
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            if res.returncode == 0:
                current_ssid = None
                for line in res.stdout.splitlines():
                    ssid_match = re.match(r"SSID\s+\d+\s+:\s+(.*)", line.strip())
                    if ssid_match:
                        current_ssid = ssid_match.group(1).strip()
                        if current_ssid:
                            networks.append({"ssid": current_ssid, "signals": []})
                    signal_match = re.search(r"Signal\s*:\s*(\d+)%", line)
                    if signal_match and networks:
                        networks[-1]["signals"].append(int(signal_match.group(1)))

                for n in networks:
                    sigs = n.pop("signals", [])
                    n["signal_percent"] = max(sigs) if sigs else 50

            return {
                "success": True,
                "networks": networks,
                "count": len(networks),
            }
        except Exception as e:
            return {"success": False, "networks": [], "error": str(e)}

    def get_ip_configuration(self) -> Dict[str, Any]:
        """Retrieve IP configuration: IPv4 addresses, default gateway, and DNS servers."""
        ps_code = (
            "Get-NetIPConfiguration -ErrorAction SilentlyContinue | "
            "Select-Object -Property InterfaceAlias, IPv4Address, IPv4DefaultGateway, DNSServer | ConvertTo-Json -Compress"
        )
        adapters: List[Dict[str, Any]] = []
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], capture_output=True, text=True, timeout=6)
            if res.returncode == 0 and res.stdout.strip():
                import json
                data = json.loads(res.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    ipv4_obj = item.get("IPv4Address")
                    ip = ipv4_obj.get("IPAddress") if isinstance(ipv4_obj, dict) else (ipv4_obj if isinstance(ipv4_obj, str) else None)
                    adapters.append({
                        "interface": item.get("InterfaceAlias"),
                        "ipv4": ip,
                    })
        except Exception:
            pass

        # Fallback to socket gethostbyname
        primary_ip = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            primary_ip = s.getsockname()[0]
            s.close()
        except Exception:
            primary_ip = "127.0.0.1"

        return {
            "success": True,
            "primary_ip": primary_ip,
            "adapters": adapters,
        }

    def ping_test(self, host: str = "8.8.8.8", count: int = 4) -> Dict[str, Any]:
        """Run ICMP ping test to measure network latency and packet loss."""
        # Clean host to prevent command injection
        host = re.sub(r"[^a-zA-Z0-9\.-]", "", host) or "8.8.8.8"
        count = max(1, min(10, count))
        cmd = ["ping", "-n", str(count), host]
        try:
            start_t = time.time()
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            elapsed = time.time() - start_t
            if res.returncode == 0:
                out = res.stdout
                loss_match = re.search(r"\((\d+)%\s+loss\)", out)
                loss_pct = int(loss_match.group(1)) if loss_match else 0
                avg_match = re.search(r"Average\s*=\s*(\d+)ms", out)
                avg_latency = int(avg_match.group(1)) if avg_match else None

                return {
                    "success": True,
                    "host": host,
                    "avg_latency_ms": avg_latency,
                    "packet_loss_percent": loss_pct,
                    "reachable": loss_pct < 100,
                    "test_duration_s": round(elapsed, 2),
                }
            return {
                "success": False,
                "host": host,
                "reachable": False,
                "packet_loss_percent": 100,
                "error": "Ping destination unreachable or timed out",
            }
        except Exception as e:
            return {"success": False, "host": host, "error": str(e)}

    def detect_vpn(self) -> Dict[str, Any]:
        """Detect active VPN adapters or secure tunnels."""
        vpn_keywords = ["wireguard", "openvpn", "cisco", "anyconnect", "nordvpn", "expressvpn", "tap", "tun", "ppp"]
        active_vpns: List[str] = []
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-NetAdapter | Where-Object { $_.Status -eq 'Up' }).Name"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    name = line.strip()
                    if any(k in name.lower() for k in vpn_keywords):
                        active_vpns.append(name)
        except Exception:
            pass

        return {
            "success": True,
            "vpn_active": len(active_vpns) > 0,
            "active_vpns": active_vpns,
        }
