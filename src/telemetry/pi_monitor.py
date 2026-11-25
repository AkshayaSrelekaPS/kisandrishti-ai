"""
Arm Linux / Raspberry Pi 5 Hardware Telemetry Monitor for KisanDrishti AI.
Reads Cortex-A76 clock frequency, SoC temperature, CPU utilization, and RAM RSS.
Provides safe cross-platform fallbacks when running on Windows/x86 dev machines.
"""
import os
import platform
import psutil


class ArmTelemetryMonitor:
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.system = platform.system()
        self.machine = platform.machine()

    def get_cpu_temp_c(self):
        """Reads Raspberry Pi / Linux thermal zone temperature in Celsius."""
        thermal_path = "/sys/class/thermal/thermal_zone0/temp"
        if os.path.exists(thermal_path):
            try:
                with open(thermal_path, "r") as f:
                    return round(int(f.read().strip()) / 1000.0, 1)
            except Exception:
                pass
        return None

    def get_cpu_freq_mhz(self):
        """Reads current CPU core clock frequency in MHz."""
        cpufreq_path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
        if os.path.exists(cpufreq_path):
            try:
                with open(cpufreq_path, "r") as f:
                    return round(int(f.read().strip()) / 1000.0, 1)
            except Exception:
                pass
        try:
            freq = psutil.cpu_freq()
            if freq and freq.current:
                return round(freq.current, 1)
        except Exception:
            pass
        return None

    def snapshot(self) -> dict:
        """Captures current process & SoC telemetry."""
        mem_info = self.process.memory_info()
        vm = psutil.virtual_memory()
        is_arm = "aarch64" in self.machine.lower() or "arm" in self.machine.lower()
        return {
            "platform": f"{self.system} ({self.machine})",
            "is_arm_edge": is_arm,
            "process_rss_mb": round(mem_info.rss / (1024 * 1024), 1),
            "system_ram_used_mb": round(vm.used / (1024 * 1024), 1),
            "system_ram_total_mb": round(vm.total / (1024 * 1024), 1),
            "cpu_percent": round(psutil.cpu_percent(interval=None), 1),
            "cpu_freq_mhz": self.get_cpu_freq_mhz(),
            "soc_temp_c": self.get_cpu_temp_c(),
        }
