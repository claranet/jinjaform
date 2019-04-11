# {{ 2 | double }} == 4
# {{ 'module.example.arn' | tf }} == ${module.example.arn}
# {% if 123 is even %}123 is even{% else %}123 is odd{% endif %} == 123 is odd
# {% if 234 is odd %}234 is odd{% else %}234 is even{% endif %} == 234 is even
# example_context_func should output ips: {% for item in example_context_func() %}{{ item }} {% endfor %}
# example_func should output 1 2 3: {% for item in example_func(3) %}{{ item }} {% endfor %}
# example_value should be hello: {{ example_value }}

