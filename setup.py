import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="bartocsuggest",
    version="0.0.3",
    author="Maximilian Hindermann",
    author_email="maximilian.hindermann@unibas.ch",
    description="Vocabulary suggestion module based on BARTOC FAST",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MHindermann/bartocsuggest",
    packages=setuptools.find_packages(),
    install_requires=[
        "urllib3",
        "requests",
        "python-Levenshtein-wheels",
        "openpyxl",
        "annif-client",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
