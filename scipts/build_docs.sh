sphinx-apidoc -f -o docs yaecs/
mv docs/yaecs.config.rst docs/yaecs_config.rst
sphinx-build -b html logml/ docs/
# Linux
xdg-open docs/_build/index.html
# Windows
start docs/_build/index.html > /dev/null
