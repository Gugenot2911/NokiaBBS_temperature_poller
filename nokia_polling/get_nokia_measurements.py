import json
import asyncio
from typing import List, Dict, Any, Optional, Set

from alarms_extraction.temperature_extraction import update_all_sites_temperatures
from nokia_polling.site_availability import check_availability_batch

# Lock для синхронизации вывода (устраняет коллизии при параллельном опросе)
print_lock = asyncio.Lock()

# Доступные команды опроса
AVAILABLE_COMMANDS = {
    "voltage": "getRealTimeMeasurements",
    "alarms": "getActiveAlarms",
    "temperature": "sfpData",
}


async def run_cli_command_async(host: str, command: str, verbose: bool = False) -> str:
    """Асинхронно выполняет CLI команду и возвращает сырой вывод."""
    cmd = [
        r"D:\Documents\PythonProject\CA_analise\experiment_CA_analise\nokia_polling\script_nokia\admin-cli.bat",
        "--bts-host", host,
        "--bts-port", "443",
        "--bts-username", "Nemuadmin",
        "--bts-password", "nemuuser",
        "--data", json.dumps({"requestId": 1, "parameters": {"name": command}}),
        "--format", "human"
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            if verbose:
                async with print_lock:
                    print(stdout.decode())
            return stdout.decode().strip()
        else:
            async with print_lock:
                print(f"Ошибка выполнения команды {command}: {stderr.decode()}")
            return 'not_nokia'

    except Exception as e:
        async with print_lock:
            print(f"Ошибка выполнения команды {command}: {e}")
        return 'not_nokia'


async def poll_single_site(
        site: Dict[str, Any],
        fields: Set[str],
        verbose: bool = False
) -> Dict[str, Any]:
    """
    Опрашивает один сайт и заполняет выбранные поля.

    Входные поля (ожидаемые):
        - hostname: str
        - ip: str
        - vendor: str (если 'bulat' - пропустить опрос)
        - availability: bool (если False - не опрашивать)
        - voltage: None (пустое)
        - alarms: None (пустое)
        - temperature: None (пустое)
        - status: str

    Выходные поля (заполненные):
        - voltage: сырые данные или None
        - alarms: сырые данные или None
        - temperature: сырые данные или None
        - status: "success" | "unavailable" | "error" | "partial" | "skipped_vendor"

    :param site: Словарь с данными сайта
    :param fields: Множество полей для опроса ("voltage", "alarms", "temperature")
    :param verbose: Выводить ли отладочную информацию
    """
    result = site.copy()

    # Проверяем vendor (если bulat - пропускаем опрос)
    vendor = site.get("vendor", "")
    if vendor == "bulat":
        result["voltage"] = None
        result["alarms"] = None
        result["temperature"] = None
        result["status"] = "skipped_vendor"
        return result

    # Проверяем availability
    availability = site.get("availability", True)

    if not availability:
        result["voltage"] = None
        result["alarms"] = None
        result["temperature"] = None
        result["status"] = "unavailable"
        return result

    # Получаем IP
    ip = site.get("ip")
    if not ip:
        result["voltage"] = None
        result["alarms"] = None
        result["temperature"] = None
        result["status"] = "error_no_ip"
        return result

    # Формируем список задач для опроса
    tasks = []
    task_names = []

    if "voltage" in fields:
        tasks.append(run_cli_command_async(ip, AVAILABLE_COMMANDS["voltage"], verbose=verbose))
        task_names.append("voltage")

    if "alarms" in fields:
        tasks.append(run_cli_command_async(ip, AVAILABLE_COMMANDS["alarms"], verbose=verbose))
        task_names.append("alarms")

    if "temperature" in fields:
        tasks.append(run_cli_command_async(ip, AVAILABLE_COMMANDS["temperature"], verbose=verbose))
        task_names.append("temperature")

    if not tasks:
        result["status"] = "error_no_fields"
        return result

    try:
        # Параллельный опрос выбранных команд
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Обработка результатов
        success_count = 0
        error_count = 0

        for field, raw_data in zip(task_names, raw_results):
            if isinstance(raw_data, Exception):
                result[field] = None
                error_count += 1
                if verbose:
                    print(f"Ошибка при опросе {field}: {raw_data}")
            elif raw_data == 'not_nokia':
                result[field] = None
                error_count += 1
                if verbose:
                    print(f"Сайт {ip} не является Nokia BTS для команды {field}")
            else:
                result[field] = raw_data
                success_count += 1

        # Определяем статус
        if error_count == 0 and success_count == len(fields):
            result["status"] = "success"
        elif success_count > 0:
            result["status"] = "partial"
        else:
            result["status"] = "error"

    except Exception as e:
        result["voltage"] = None
        result["alarms"] = None
        result["temperature"] = None
        result["status"] = f"error: {str(e)}"

    return result


async def poll_sites_batch(
        sites: List[Dict[str, Any]],
        fields: Set[str],
        verbose: bool = False,
        check_availability: bool = True,
        ping_timeout: float = 1
) -> List[Dict[str, Any]]:
    """
    Обрабатывает пакет сайтов асинхронно (параллельно).

    :param sites: Список словарей с данными сайтов
    :param fields: Множество полей для опроса
    :param verbose: Выводить ли отладочную информацию
    :param check_availability: Проверять ли доступность хостов перед опросом
    :param ping_timeout: Таймаут ping в секундах
    :return: Список с заполненными полями voltage, alarms, temperature, status
    """
    # Проверяем доступность хостов в батче
    if check_availability:
        check_availability_batch(sites, timeout=ping_timeout)

    # Опрашиваем только доступные сайты
    tasks = []
    for site in sites:
        # Если availability явно установлен в False, не опрашиваем
        if site.get('availability') is False:
            # Создаем результат сразу
            result = site.copy()
            result["voltage"] = None
            result["alarms"] = None
            result["temperature"] = None
            result["status"] = "unavailable"
            tasks.append(asyncio.sleep(0, result=result))
        else:
            tasks.append(poll_single_site(site, fields, verbose=verbose))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Фильтрация ошибок
    filtered_results = []
    for r in results:
        if isinstance(r, Exception):
            print(f"⚠️ Ошибка при опросе сайта: {type(r).__name__}: {r}")
            filtered_results.append({
                "status": "error",
                "error_message": str(r)
            })
        else:
            filtered_results.append(r)

    return filtered_results


def nokia_polling_module(
        sites: List[Dict[str, Any]],
        fields: Optional[Set[str]] = None,
        batch_size: int = 10,
        verbose: bool = False,
        check_availability: bool = True,
        ping_timeout: float = 1
) -> List[Dict[str, Any]]:
    """
    Основная функция модуля опроса BTS.

    Вход (list[dict]):
        [
            {
                "hostname": "NS1120",
                "ip": "10.8.235.118",
                "vendor": "nokia",  # если "bulat" - опрос игнорируется
                "voltage": None,
                "alarms": None,
                "temperature": None,
                "status": ""
            },
            ...
        ]

    Выход (list[dict]):
        [
            {
                "hostname": "NS1120",
                "ip": "10.8.235.118",
                "vendor": "nokia",
                "availability": bool,  # добавляется при check_availability=True
                "voltage": "raw_data_voltage...",
                "alarms": "raw_data_alarms...",
                "temperature": "raw_data_sfp...",
                "status": "success"  # success | unavailable | error | partial | skipped_vendor
            },
            ...
        ]

    :param sites: Список сайтов для опроса
    :param fields: Множество полей для опроса {"voltage", "alarms", "temperature"}
                    Если None - опрашиваются все поля
    :param batch_size: Количество параллельных опросов
    :param verbose: Выводить ли отладочную информацию
    :param check_availability: Проверять ли доступность хостов перед опросом (по умолчанию True)
    :param ping_timeout: Таймаут ping в секундах (по умолчанию 1)
    :return: Список с заполненными сырыми данными
    """
    # По умолчанию опрашиваем все поля
    if fields is None:
        fields = {"voltage", "alarms", "temperature"}

    # Валидация полей
    invalid_fields = fields - AVAILABLE_COMMANDS.keys()
    if invalid_fields:
        print(f"⚠️ Неизвестные поля: {invalid_fields}. Доступные: {list(AVAILABLE_COMMANDS.keys())}")
        fields = fields & AVAILABLE_COMMANDS.keys()

    if not fields:
        print("Нет полей для опроса")
        return sites

    if not sites:
        print("Нет сайтов для обработки")
        return []

    print(f"Опрашиваемые поля: {fields}")

    # Фильтрация: пропускаем bulat vendor
    nokia_sites = [s for s in sites if s.get("vendor") != "bulat"]
    skipped_vendor_sites = [s for s in sites if s.get("vendor") == "bulat"]

    print(
        f"Всего сайтов: {len(sites)}, Nokia: {len(nokia_sites)}, пропущено (vendor=bulat): {len(skipped_vendor_sites)}")

    # Разбиваем на батчи
    batches = [nokia_sites[i:i + batch_size] for i in range(0, len(nokia_sites), batch_size)]
    print(f"Батчей для опроса: {len(batches)}")

    final_results = []

    # Добавляем пропущенные сайты (vendor=bulat)
    for site in skipped_vendor_sites:
        result = site.copy()
        result["voltage"] = None
        result["alarms"] = None
        result["temperature"] = None
        result["status"] = "skipped_vendor"
        final_results.append(result)

    # Обрабатываем Nokia сайты батчами
    for batch_idx, batch in enumerate(batches):
        print(f"Обработка батча {batch_idx + 1}/{len(batches)}: {[s.get('hostname') for s in batch]}")

        # Проверка доступности выполняется внутри poll_sites_batch
        batch_results = asyncio.run(poll_sites_batch(
            batch,
            fields,
            verbose=verbose,
            check_availability=check_availability,
            ping_timeout=ping_timeout
        ))
        final_results.extend(batch_results)


    final_results = update_all_sites_temperatures(final_results)

    return final_results


if __name__ == "__main__":
    # Пример входных данных
    input_sites = [
        {"hostname": "NS1120", "ip": "10.8.227ав", "vendor": "nokia", "voltage": None, "alarms": None,
         "temperature": None, "status": ""},
        {"hostname": "NS1111", "ip": "10.8.227.209", "vendor": "nokia", "voltage": None, "alarms": None,
         "temperature": None, "status": ""},
        {"hostname": "NS0830", "ip": "10.8.239.189", "vendor": "nokia", "voltage": None, "alarms": None,
         "temperature": None, "status": ""},
        {"hostname": "NS1830", "ip": "10.148.233.137", "vendor": "nokia", "voltage": None, "alarms": None,
         "temperature": None, "status": ""}
    ]

    print("Пример с проверкой доступности")
    result = nokia_polling_module(
        sites=input_sites,
        fields={"temperature"},
        batch_size=2,
        verbose=False,
        check_availability=True,
        ping_timeout=1
    )


    print(result)


