from jinja2 import contextfunction


@contextfunction
def example_context_func(ctx):
    return ctx['var']['ips']


def example_func(num):
    return range(num)


example_value = 'hello'


__all__ = ['example_context_func', 'example_func', 'example_value']
