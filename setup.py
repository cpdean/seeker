import sys

version = sys.version_info[:2]

from setuptools import setup, find_packages
README = """this is for looking up where a function comes from"""
CHANGES = ''

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Natural Language :: English',
    "Programming Language :: Python :: 2.7",
]

__version__ = "0.0.1"

tests_require = [
    "pytest==2.8.5"
]

dist = setup(
    name='seeker',
    version=__version__,
    license='MIT',
    description="Making elm nicer",
    long_description="Making elm nicer",
    classifiers=CLASSIFIERS,
    author="Conrad Dean",
    author_email="conrad.p.dean@gmail.com",
    packages=find_packages(),
    tests_require=tests_require,
    include_package_data=True,
    zip_safe=False,
    test_suite="seeker.tests",
    entry_points={
        'console_scripts': [
            'seeker = seeker:main',
        ],
    },
)
