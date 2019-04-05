# {% for ip in var.ips %}
#   {% if ip is private_ipv4 %}
#       {{ ip }} is private
#   {% elif ip is public_ipv4 %}
#       {{ ip }} is public
#   {% else %}
#       {{ ip }} is not an ip
#   {% endif %}
# {% endfor %}
