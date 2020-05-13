from setuptools import setup, find_packages

setup(
    name='mhd-utils',
    version='2.0.0',
    packages=find_packages(),
    install_requires=["numpy"],
    license=open('LICENSE').read(),
    long_description=open('README.md').read(),
    author="Bing Jain, Price Jackson, Peter Fischer",
    author_email="..., ..., ...",
    url="https://github.com/yanlend/mhd_utils"
)
