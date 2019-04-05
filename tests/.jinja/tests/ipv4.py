from .utils import _parse_ip, _is_private_ip


def ipv4(addr):
    ip = _parse_ip(addr)
    if ip:
        return True
    return False


def private_ipv4(addr):
    ip = _parse_ip(addr)
    if ip and _is_private_ip(ip):
        return True
    return False


def public_ipv4(addr):
    ip = _parse_ip(addr)
    if ip and not _is_private_ip(ip):
        return True
    return False


__all__ = ['ipv4', 'private_ipv4', 'public_ipv4']
