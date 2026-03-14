"""Setup for the Elcorp Python SDK."""

from setuptools import setup, find_packages

setup(
    name="elcorp-sdk",
    version="0.1.0",
    description="Python SDK for the Elcorp Digital Identity & Payments API",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.28",
    ],
)
