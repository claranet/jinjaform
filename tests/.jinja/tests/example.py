def even(value):
    """
    Tests if a number is even.

    Usage: {% if 123 is even %}{% endif %}

    """

    return value % 2 == 0


def odd(value):
    """
    Tests if a number is odd.

    Usage: {% if 123 is odd %}{% endif %}

    """

    return not even(value)


__all__ = ['even', 'odd']
