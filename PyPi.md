### Just notes for me on how to publish to PyPi
https://packaging.python.org/en/latest/tutorials/packaging-projects/
- `py -m build`
- `py -m twine upload dist/*`
- Enter `__token__` as username and the api key as password

- `py -m twine upload --repository testpypi dist/*`