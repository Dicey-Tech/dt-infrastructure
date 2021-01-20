# TODO Replace PYTHONPATH edit of .envrc with package install
# https://realpython.com/python-import/#create-and-install-a-local-package
import setuptools

with open("README.md") as fp:
    long_description = fp.read()

setuptools.setup(
    name="educate_infrastructure",
    version="0.0.1",
    description="Pulumi project for Dicey Tech's Infrastructure",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Sofiane Bebert",
    package_dir={"": "educate_infrastructure"},
    packages=setuptools.find_packages(where="educate_infrastructure"),
    python_requires=">=3.6",
)
