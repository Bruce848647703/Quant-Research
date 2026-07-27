from setuptools import setup, find_packages

setup(
    name="quant-research",
    version="0.1.0",
    description="A股量化研究项目 - 短期反转因子回测",
    author="Bruce",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "akshare>=1.10.0",
        "backtrader>=1.9.78",
        "pandas>=1.5.0",
        "numpy>=1.23.0",
        "matplotlib>=3.6.0",
        "seaborn>=0.12.0",
        "pyyaml>=6.0",
    ],
)
