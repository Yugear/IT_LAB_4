"""
Требуется: Python 3.12+ и psutil.
"""

import json
import platform
import socket
from datetime import datetime
from pathlib import Path

import psutil


def get_system_info():
    return {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M"),
    }


def get_cpu_info():
    freq = psutil.cpu_freq()
    return {
        "model": platform.processor() or platform.uname().processor or platform.machine(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "max_freq_mhz": round(freq.max) if freq and freq.max > 0 else None,
        "load_percent": psutil.cpu_percent(interval=1),
    }


def get_memory_info():
    mem = psutil.virtual_memory()
    return {
        "total_gb": round(mem.total / (1024 ** 3), 1),
        "used_percent": mem.percent,
        "available_gb": round(mem.available / (1024 ** 3), 1),
    }


def get_disk_info():
    disks = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            # Некоторые системные/съёмные разделы недоступны для чтения.
            continue
        disks.append({
            "device": part.device,
            "mountpoint": part.mountpoint,
            "fs": part.fstype,
            "total_gb": round(usage.total / (1024 ** 3), 1),
            "used_percent": usage.percent,
        })
    return disks


def get_network_info():
    """Задание 2: один элемент на каждый IPv4-адрес интерфейса."""
    interfaces = []
    for name, addrs in psutil.net_if_addrs().items():
        mac = next(
            (addr.address for addr in addrs if addr.family == psutil.AF_LINK),
            None,
        )
        for addr in addrs:
            if addr.family == socket.AF_INET:
                interfaces.append({
                    "name": name,
                    "ipv4": addr.address,
                    "netmask": addr.netmask,
                    "mac": mac,
                })
    return interfaces


def analyze(passport):
    recommendations = []
    memory = passport["memory"]
    cpu = passport["cpu"]

    ram = memory["total_gb"]
    cores = cpu["physical_cores"]

    if ram < 8:
        recommendations.append("Недостаточно памяти для виртуальных машин и Docker (RAM < 8 ГБ).")
    if ram >= 16 and cores is not None and cores >= 6:
        recommendations.append("Подходит для одновременной работы нескольких VM (RAM >= 16 ГБ, физических ядер >= 6).")
    for disk in passport["disks"]:
        if disk["used_percent"] > 85:
            recommendations.append(
                f"Освободить место на диске {disk['device']} "
                f"({disk['used_percent']}% заполнено)."
            )
    if cores is not None and cores < 4:
        recommendations.append("Процессор может стать узким местом (bottleneck): меньше 4 физических ядер.")
    # Собственное правило: проверка объёма доступной оперативной памяти.
    if memory["available_gb"] < 2:
        recommendations.append("Доступно менее 2 ГБ ОЗУ: закройте ненужные приложения.")

    return recommendations


def main():
    passport = {
        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "system": get_system_info(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disks": get_disk_info(),
        "network": get_network_info(),
    }
    passport["recommendations"] = analyze(passport)
    safe_hostname = "".join(
        c if c.isalnum() or c in "-_." else "_"
        for c in passport["system"]["hostname"]
    )
    filename = Path(f"passport_{safe_hostname}.json")
    with filename.open("w", encoding="utf-8") as f:
        json.dump(passport, f, ensure_ascii=False, indent=2)
    print(json.dumps(passport, ensure_ascii=False, indent=2))
    print(f"\nПаспорт сохранён в файл {filename}")


if __name__ == "__main__":
    main()
