# TODO Replace PYTHONPATH edit of .envrc with package install
# https://realpython.com/python-import/#create-and-install-a-local-package
import io
import os
from setuptools import find_packages, setup

HERE = os.path.abspath(os.path.dirname(__file__))


def load_readme():
    with io.open(os.path.join(HERE, "README.md"), "rt", encoding="utf8") as f:
        readme = f.read()

    return readme


setup(
    name="educate_infrastructure",
    version="0.0.1",
    description="Pulumi project for Dicey Tech's Infrastructure",
    long_description=load_readme(),
    long_description_content_type="text/markdown",
    author="Sofiane Bebert",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.6",
)
