def find_json_objects(text:str) -> list|str:
    print('запуск конвертации')
    try:

        objects = []
        start_index = -1
        brace_count = 0

        for i, char in enumerate(text):
            if char == '{':
                if brace_count == 0:
                    start_index = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_index != -1:

                    json_str = text[start_index:i + 1]
                    objects.append(json_str)
                    start_index = -1

        return objects

    except Exception as e:

        print(e)
        return 'error converting'




