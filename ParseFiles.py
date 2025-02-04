def parse_mkprg_file(filename):
    data = []
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if line.startswith('$MKPRG,CFG:R'):
                parts = line.split(',')
                entry = {}
                entry['ChannelNumber'] = int(parts[2])
                for item in parts[3:]:
                    key, value = item.split(':')
                    entry[key] = value
                data.append(entry)
    return data

def write_mkprg_file(data, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        file.write("\n")
        for entry in data:
            line_parts = ["$MKPRG,CFG:R", str(entry['ChannelNumber'])]
            for key, value in entry.items():
                if key != 'ChannelNumber':
                    line_parts.append(f"{key}:{value}")
            file.write(','.join(line_parts) + '\n')
