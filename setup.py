from setuptools import setup, find_packages

setup(
    name="cs3news-gigavpn",
    version="2.0.0",
    description="CS3NEWS corporate network accelerator",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "cryptography>=41.0.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cs3news-gigavpn=proxy.main:main",
        ],
    },
)