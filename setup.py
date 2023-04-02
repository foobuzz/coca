from setuptools import setup


setup(
    name='coca',
    version='1.0.0',
    package_dir={'': 'src'},
    py_modules=['coca'],
    description=(
        "A Python lib to help you update the lines you have already printed to "
        "stdout."
    ),
    author='@foobuzz',
    author_email='foobuzz@fastmail.com',
    url='https://github.com/foobuzz/coca',
    extras_require={
        'tests': {
            'flake8==3.8.4',
            'mypy==1.1.1',
            'pytest==5.4.3',
            'pytest-mock==3.1.1',
        },
    },
)
