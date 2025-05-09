from setuptools import setup, find_packages


with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="deskquery",
    version="0.1.0",
    author="",                                                                      # TODO
    author_email="",                                                                # TODO
    description="An intelligent query system for workplace and desk analytics",
    
    long_description=open("README.md", encoding="utf-8").read(),
    
    long_description_content_type="text/markdown",
    url="https://github.com/deinname/deskquery",                                    # TODO
    
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires='>=3.9',
    install_requires=requirements,
)
