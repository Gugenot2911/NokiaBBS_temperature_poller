import re
from typing import Dict, List, Any, Union


def process_voltage_field(data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Обрабатывает поле voltage, вычисляет среднее значение (исключая нули)

    Args:
        data_list: Список словарей с полем voltage (содержит текст CLI лога)

    Returns:
        Список словарей с обновленным полем voltage:
        - среднее значение (float) если найдены voltage > 0
        - "no data available" если поле voltage отсутствует или нет валидных данных
    """

    def calculate_average_voltage(log_text: str) -> Union[float, str]:
        """Извлекает все значения voltage из лога и возвращает среднее (исключая нули)"""

        # Проверяем наличие поля
        if not isinstance(log_text, str):
            return "no data available"

        # Ищем все значения voltage в тексте
        # Паттерн ищет "voltage": followed by number (with or without quotes)
        pattern = r'"voltage":\s*"?(\d+(?:\.\d+)?)"?'
        matches = re.findall(pattern, log_text)

        if not matches:
            return "no data available"

        # Преобразуем в числа и исключаем нули
        voltages = []
        for v in matches:
            voltage_val = float(v)
            if voltage_val != 0:  # Исключаем нулевые значения
                voltages.append(voltage_val)

        # Если после исключения нулей остались значения
        if voltages:
            average = sum(voltages) / len(voltages)
            return round(average, 2)  # Округляем до 2 знаков
        else:
            return "no data available"

    # Обрабатываем каждый словарь в списке
    for item in data_list:
        if 'voltage' in item:
            item['voltage'] = calculate_average_voltage(item['voltage'])
        else:
            # Если поля voltage нет, добавляем его с сообщением
            item['voltage'] = "no data available"

    return data_list


# Пример использования
if __name__ == "__main__":
    # Ваш CLI лог текст
    cli_log_text = '''CLI LOG:  CLI 2.7.8-client started
CLI LOG:  {"time":"15:20:05","requestStatus":"completed","requestMessage":{"accountType":"LOCAL","failedLoginNo":0,"forcedPasswordUpdate":false,"httpSessionId":"00e86661-efc7-4573-91a7-4bbdd7e5b2c3","lastSuccess":1775204404923,"presentTimeStamp":1775204405092,"profile":"Nemuadmin","readOnlyAccess":false,"rndMode":false,"userName":"Nemuadmin"},"errorCode":0}
CLI LOG:  {
   "time": "15:20:15",
   "requestId": 1,
   "requestStatus": "completed",
   "requestMessage": [
      {
         "ENERGY_EFFICIENCY/RMOD/RMOD_R-2": {
            "voltage": "52.5",
            "power": "511.8"
         }
      },
      {
         "ENERGY_EFFICIENCY/RMOD/RMOD_R-1": {
            "voltage": "52.3",
            "power": "498.8"
         }
      },
      {
         "ENERGY_EFFICIENCY/RMOD/RMOD_R-3": {
            "voltage": "53.1",
            "power": "560.0"
         }
      },
      {
         "ENERGY_EFFICIENCY/RMOD/RMOD_R-6": {
            "voltage": 0,
            "power": 0
         }
      },
      {
         "ENERGY_EFFICIENCY/RMOD/RMOD_R-4": {
            "voltage": "53.9",
            "power": "497.4"
         }
      }
   ],
   "errorCode": 0
}'''

    # Тестовые данные
    test_data = [
        {
            "hostname": "NS1120",
            "ip": "10.8.227.245",
            "availability": True,
            "voltage": cli_log_text,  # Текст с voltage значениями
            "alarms": "alarms text",
            "temperature": "temp text",
            "status": ""
        },
        {
            "hostname": "NS1111",
            "ip": "10.8.227.209",
            "availability": True,
            "voltage": cli_log_text,  # Тот же текст для примера
            "alarms": "alarms text",
            "temperature": "temp text",
            "status": ""
        },
        {
            "hostname": "NS9999",
            "ip": "10.8.227.999",
            "availability": True,
            # Поле voltage отсутствует
            "alarms": "alarms text",
            "temperature": "temp text",
            "status": ""
        }
    ]

    # Обрабатываем данные
    print("=== Обработка voltage (среднее значение) ===")
    result = process_voltage_field(test_data)

    for item in result:
        print(f"\nХост: {item['hostname']} ({item['ip']})")
        print(f"  Voltage: {item['voltage']}")
        if isinstance(item['voltage'], float):
            print(f"  Тип: Числовое значение (среднее)")
        else:
            print(f"  Тип: {item['voltage']}")

    # Демонстрация расчета
    print("\n=== Проверка расчета ===")
    # Ручной расчет для проверки
    voltages = [52.5, 52.3, 53.1, 53.9]  # 0 был исключен
    manual_average = sum(voltages) / len(voltages)
    print(f"Найденные значения (исключая 0): {voltages}")
    print(f"Ручной расчет среднего: {manual_average:.2f}")
    print(f"Результат функции: {result[0]['voltage']}")