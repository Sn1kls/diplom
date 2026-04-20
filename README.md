# SoulVia

## Installation
1. Install uv 
    ````shell
    curl -Ls https://astral.sh/uv/install.sh | bash
    ````
2. Install dependencies
   ````shell
   uv sync --frozen --no-cache
   ````

## Locale compile
1. Make messages for translation
   ```shell
   python manage.py makemessages -l en
   ```
2. Compile the messages after adding translations to the `.po` files for them:
   ```shell
   python manage.py compilemessages   
   ```


## Ruff
1. To format the entire project
   ```shell
   ruff format .
   ```
2. To check the entire project for code style compliance
   ```shell
   ruff check . --fix
   ```