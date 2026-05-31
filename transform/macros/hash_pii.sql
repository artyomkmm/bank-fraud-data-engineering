{% macro hash_pii(column_name) %}
    lower(hex(SHA256(toString(coalesce({{ column_name }}, '')))))
{% endmacro %}
