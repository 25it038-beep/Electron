"""Holistic Hardware & Performance Troubleshooter for Windows.

Diagnoses CPU, Memory, GPU, Disk bottlenecks, Thermal issues, and Power throttling.
Answers user queries like 'Why is my laptop slow?' with actionable prioritized solutions.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import psutil

from electorn.computer_engine.controllers.display_controller import DisplayController
from electorn.computer_engine.controllers.power_controller import PowerController
from electorn.computer_engine.controllers.storage_controller import StorageController

logger = logging.getLogger(__name__)


class DeviceTroubleshooter:
    """Diagnoses system performance, bottlenecks, and hardware health."""

    def __init__(self) -> None:
        self.display = DisplayController()
        self.storage = StorageController()
        self.power = PowerController()

    def diagnose_system_performance(self) -> Dict[str, Any]:
        """Perform a full system diagnostic of CPU, RAM, GPU, Disk, and Battery."""
        findings: List[str] = []
        recommendations: List[str] = []
        severity = "healthy"

        # 1. CPU Diagnostic
        cpu_pct = psutil.cpu_percent(interval=0.5)
        top_cpu_procs = self._get_top_processes_by_cpu(limit=5)
        if cpu_pct > 85.0:
            severity = "critical"
            findings.append(f"High CPU utilization: {cpu_pct}%")
            if top_cpu_procs:
                top_p = top_cpu_procs[0]
                recommendations.append(f"Process '{top_p['name']}' (PID {top_p['pid']}) is using {top_p['cpu_percent']}% CPU. Consider closing it if not needed.")
        elif cpu_pct > 65.0:
            if severity != "critical":
                severity = "warning"
            findings.append(f"Moderate CPU load: {cpu_pct}%")

        # 2. RAM Diagnostic
        mem = psutil.virtual_memory()
        top_mem_procs = self._get_top_processes_by_memory(limit=5)
        if mem.percent > 90.0:
            severity = "critical"
            findings.append(f"Critical memory pressure: {mem.percent}% RAM used ({round(mem.used / (1024**3), 1)}GB / {round(mem.total / (1024**3), 1)}GB)")
            if top_mem_procs:
                recommendations.append(f"Top memory consumer is '{top_mem_procs[0]['name']}' using {top_mem_procs[0]['memory_mb']} MB.")
        elif mem.percent > 80.0:
            if severity == "healthy":
                severity = "warning"
            findings.append(f"High memory usage: {mem.percent}% RAM used")

        # 3. GPU & Thermals
        gpu_info = self.display.get_gpu_info()
        gpus = gpu_info.get("gpus", [])
        gpu_summary = []
        for g in gpus:
            name = g.get("name", "GPU")
            temp = g.get("temperature_c", 0)
            util = g.get("utilization_percent", 0)
            gpu_summary.append(f"{name}: {util}% load, {temp}°C")
            if temp > 85.0:
                severity = "critical"
                findings.append(f"GPU thermal threshold high: {name} is at {temp}°C.")
                recommendations.append("Ensure laptop cooling vents are not blocked and elevate laptop for airflow.")

        # 4. Storage Bottlenecks
        drives = self.storage.get_drive_overview().get("drives", [])
        for d in drives:
            if d.get("percent_used", 0) > 95.0:
                severity = "critical"
                findings.append(f"Drive {d['device']} is {d['percent_used']}% full ({d['free_gb']} GB free). Windows paging and apps may lag.")
                recommendations.append(f"Run disk cleanup or remove large files on {d['device']}.")
            elif d.get("percent_used", 0) > 85.0:
                if severity == "healthy":
                    severity = "warning"
                findings.append(f"Drive {d['device']} is {d['percent_used']}% full.")

        # 5. Power & Throttling
        batt = self.power.get_battery_status()
        if batt.get("has_battery") and not batt.get("power_plugged"):
            if batt.get("percent", 100) < 20:
                findings.append(f"Battery is low ({batt['percent']}%) and running on DC power. CPU may be throttled by Windows.")
                recommendations.append("Plug in the charger to restore full hardware clock speeds.")

        if not findings:
            findings.append("All primary subsystems (CPU, RAM, GPU, Disk, Power) are running within nominal parameters.")
            recommendations.append("System is performing well. No intervention needed.")

        return {
            "success": True,
            "overall_status": severity,
            "cpu_percent": cpu_pct,
            "memory_percent": mem.percent,
            "ram_used_gb": round(mem.used / (1024**3), 1),
            "ram_total_gb": round(mem.total / (1024**3), 1),
            "gpu_telemetry": gpu_summary,
            "findings": findings,
            "recommendations": recommendations,
            "top_cpu_processes": top_cpu_procs,
            "top_memory_processes": top_mem_procs,
        }

    def _get_top_processes_by_cpu(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top processes by CPU percentage."""
        procs: List[Dict[str, Any]] = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
            try:
                info = p.info
                if info.get("cpu_percent") and info["cpu_percent"] > 0:
                    procs.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "cpu_percent": round(info["cpu_percent"], 1),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
        return procs[:limit]

    def _get_top_processes_by_memory(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top processes by memory usage (RSS)."""
        procs: List[Dict[str, Any]] = []
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                info = p.info
                mem_info = info.get("memory_info")
                if mem_info:
                    rss_mb = round(mem_info.rss / (1024 * 1024), 1)
                    procs.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "memory_mb": rss_mb,
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x["memory_mb"], reverse=True)
        return procs[:limit]
