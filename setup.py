from setuptools import setup, find_packages

from hr_procedures import __version__

setup(
    name="hr_procedures",
    version=__version__,
    description="Employee violations and disciplinary procedures for Frappe HRMS",
    author="Shams Solutions",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
