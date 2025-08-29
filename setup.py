"""Setup for jupyter-scheduler-k8s."""

from setuptools import setup, find_packages

setup(
    name="jupyter-scheduler-k8s",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)