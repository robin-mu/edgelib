from crc import Configuration, Calculator
config_name = Configuration(width=32, polynomial=0x4C11DB7, init_value=0, final_xor_value=0, reverse_input=True, reverse_output=True)
calc_name = Calculator(config_name)
config_namespace = Configuration(width=32, polynomial=0xFB3EE248, init_value=0, final_xor_value=0, reverse_input=True, reverse_output=True)
calc_namespace = Calculator(config_namespace)

def generate_crc(name: str, namespace: str) -> str:
    return f'{calc_name.checksum(bytes(name[::-1], encoding='ascii')):08X}{calc_namespace.checksum(bytes(namespace[::-1], encoding='ascii')):08X}'
