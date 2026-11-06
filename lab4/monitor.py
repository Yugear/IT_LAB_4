
"""
Запуск: python monitor.py --variant 3
"""

import argparse
import csv
import os
import time
from datetime import datetime

import psutil


VARIANTS = {
    3: {
        "interval": 3,
        "samples": 15,
        "thresholds": {"cpu": 80, "ram": 80, "disk": 85},
        "extra_field": "network_sent_mb",
        "extra_label": "Сеть отправлено (МБ)",
    },
}


LOG_FILE = "monitor_log.csv"

DISK_PATH = os.path.abspath(os.sep)


def read_extra_metric(variant):
    if variant == 3:
        return round(psutil.net_io_counters().bytes_sent / (1024 ** 2), 2)
    raise ValueError(f"Неподдерживаемый вариант: {variant}")


def take_sample(variant):
    sample = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "cpu": psutil.cpu_percent(interval=None),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage(DISK_PATH).percent,
    }
    sample[VARIANTS[variant]["extra_field"]] = read_extra_metric(variant)
    return sample


def check_alerts(sample, thresholds):
    alerts = []
    for metric, limit in thresholds.items():
        if sample[metric] >= limit:
            alerts.append(f"{metric.upper()} = {sample[metric]}% (порог {limit}%)")
    return alerts


def show_summary(samples, extra_field, extra_label):
    print("\nИтоговая статистика:")
    names = {"cpu": "CPU", "ram": "RAM", "disk": "DISK", extra_field: extra_label}
    for metric, name in names.items():
        values = [float(s[metric]) for s in samples if s[metric] is not None]
        if not values:
            print(f"  {name}: данных нет (датчик/функция недоступны).")
            continue
        unit = "%" if metric in {"cpu", "ram", "disk", "battery_percent"} else " МБ"
        print(
            f"  {name}: среднее {sum(values)/len(values):.2f}{unit}, "
            f"минимум {min(values):.2f}{unit}, максимум {max(values):.2f}{unit}"
        )


def main():
    parser = argparse.ArgumentParser(description="Мониторинг CPU/RAM/DISK: варианты 3, 4, 5")
    parser.add_argument("--variant", type=int, choices=sorted(VARIANTS), required=True,
                        help="Номер варианта из таблицы задания: 3, 4 или 5")
    parser.add_argument("--log-file", default=LOG_FILE,
                        help=f"Имя выходного CSV (по умолчанию {LOG_FILE})")
    args = parser.parse_args()

    cfg = VARIANTS[args.variant]
    interval = cfg["interval"]
    samples_count = cfg["samples"]
    thresholds = cfg["thresholds"]
    extra = cfg["extra_field"]

    print(f"Вариант {args.variant}: интервал {interval} с, замеров {samples_count}, "
          f"пороги CPU/RAM/DISK = {thresholds['cpu']}/{thresholds['ram']}/{thresholds['disk']}%")
    print(f"Мониторинг раздела диска: {DISK_PATH}")

    psutil.cpu_percent(interval=None)  
    samples = []
    fieldnames = ["time", "cpu", "ram", "disk", extra, "alert"]
    with open(args.log_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for index in range(1, samples_count + 1):
            time.sleep(interval)
            sample = take_sample(args.variant)
            alerts = check_alerts(sample, thresholds)
            sample["alert"] = "; ".join(alerts)
            writer.writerow(sample)
            f.flush()
            samples.append(sample)
            mark = " <-- ВНИМАНИЕ: " + sample["alert"] if alerts else ""
            extra_value = sample[extra]
            extra_display = "N/A" if extra_value is None else str(extra_value)
            print(
                f"[{index:02d}/{samples_count}] {sample['time']} "
                f"CPU {sample['cpu']:5.1f}% RAM {sample['ram']:5.1f}% "
                f"DISK {sample['disk']:5.1f}% {extra}={extra_display}{mark}"
            )

    print(f"\nЖурнал сохранён в {args.log_file}")
    show_summary(samples, extra, cfg["extra_label"])
    print("Вывод в CSV.")


if __name__ == "__main__":
    main()
