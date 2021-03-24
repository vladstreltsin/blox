from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()


setup(
    name="blox",

    python_requires='>=3.7',

    version="0.0.1",

    author="Vlad Streltsin",

    author_email="vladstreltsin@gmail.com",

    description="Block diagram modeling",

    long_description=long_description,

    long_description_content_type="text/markdown",

    url="https://github.com/vladstreltsin/blox.git",

    find_packages=['blox'],

    install_requires=[
        'networkx>=2.4',
        'tabulate>=0.8.7'
        'boltons>=20.2.1'
        'scalpl>=0.4.0'
    ],

    extras_require={
    }
)
