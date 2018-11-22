import colorama


def init(_cache=[]):
    if not _cache:
        colorama.init()
        _cache.append(True)


def bad(message, *args, **kwargs):
    init()
    if args or kwargs:
        message = message.format(*args, **kwargs)
    print(colorama.Fore.RED + '[terraform wrapper] ' + message + colorama.Style.RESET_ALL)


def ok(message, *args, **kwargs):
    init()
    if args or kwargs:
        message = message.format(*args, **kwargs)
    print(colorama.Fore.CYAN + '[terraform wrapper] ' + message + colorama.Style.RESET_ALL)
