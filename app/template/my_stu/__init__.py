import re

if __name__ == '__main__':

    text = '<p>Topic for {{name}}:{% for t in topics %}{{t}},{% endfor %}</p>'

    tokens =re.split(r"(?s)({{.*?}})|{%.*?%}|{#.*?#}", text)

    print tokens
