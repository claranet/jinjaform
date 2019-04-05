import re


def _parse_ip(addr):
    match = re.match(r'(\d+)\.(\d+)\.(\d+)\.(\d+)(/\d+)?', addr)
    if match:
        a, b, c, d, n = match.groups()
        ip = (int(a), int(b), int(c), int(d))
        if ip >= (0, 0, 0, 0) and ip <= (255, 255, 255, 255):
            return ip


def _is_private_ip(ip):
    if ip >= (10, 0, 0, 0) and ip <= (10, 255, 255, 255):
        return True
    if ip >= (172, 16, 0, 0) and ip <= (172, 31, 255, 255):
        return True
    if ip >= (192, 168, 0, 0) and ip <= (192, 168, 255, 255):
        return True
    return False
