import json
import alarms_extraction.raw_text_converter as raw_convert
from datetime import datetime


def temperature_sfp(raw_data:str) -> dict|str:

    '''

    :param raw_data: bla blal { payload { payload } } blablabla
    :return: {payload:{payload:...} }
    '''

    if raw_data != 'error converting':

        json_objects = json.loads(raw_convert.find_json_objects(text=raw_data)[-1])
        # print(i, json_objects.keys())

        # print(f'keys: {json_objects.keys()}')


        rru = json_objects['requestMessage']['connected']
        bbu = json_objects['requestMessage']['notConnected']

        sfp_temperature = {
            "RRU": [],
            "BBU": [],
            "timestamp": datetime.now().isoformat()
        }

        for item in rru:
            src_module = item['source']['productName']
            src_temp = item['source']['connector']['sfp']['temperature']
            dst_module = item['destination']['productName']
            dst_temp = item['destination']['connector']['sfp']['temperature']

            sfp_temperature['RRU'].append({src_module: src_temp})
            sfp_temperature['BBU'].append({dst_module: dst_temp})

        for item in bbu:
            module = item['source']['productName']
            temp = item['source']['connector']['sfp']['temperature']
            sfp_temperature['RRU'].append({module: temp})

        return sfp_temperature



    else:

        return raw_data


def max_min_avg_temperature(raw_data: str) -> dict:
    data = temperature_sfp(raw_data=raw_data)
    result = {}

    for device_type, device_data in data.items():
        if device_type == 'timestamp':
            continue

        values = []
        for item in device_data:
            for value in item.values():
                # Пытаемся привести к числу, игнорируем ошибки
                try:
                    num_value = float(value)
                    values.append(num_value)
                except (ValueError, TypeError):
                    continue  # Пропускаем некорректные данные (str, None и т.д.)

        # Проверяем, что список не пуст, чтобы не делить на ноль
        if values:
            result[device_type] = {
                'max': max(values),
                'min': min(values),
                'avg': round(sum(values) / len(values))
            }
        else:
            # Если данных нет, можно либо пропустить ключ, либо записать None
            result[device_type] = {'max': None, 'min': None, 'avg': None}

    return result



def update_all_sites_temperatures(sites_list):
    """
    Применяет max_min_avg_temperature к полю "temperatures" каждого сайта
    и заменяет raw данные на вычисленную статистику
    """
    for site in sites_list:
        if site.get('temperature') and isinstance(site['temperature'], str):
            site['temperature'] = max_min_avg_temperature(site['temperature'])
        elif site.get('temperature') is None:
            site['temperature'] = {"error": "No temperature data available"}

    return sites_list


