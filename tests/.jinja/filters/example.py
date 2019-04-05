def double(value):
    """
    Doubles the value.

    Usage: "{{ 2 | double }}"
    Output: "4"

    """

    return value * 2


def tf(value):
    """
    Wraps the value with Terraform interpolation syntax.

    Usage: "{{ 'module.example.arn' | tf }}"
    Output: "${module.example.arn}"

    """

    return '${' + value + '}'


__all__ = ['double', 'tf']
