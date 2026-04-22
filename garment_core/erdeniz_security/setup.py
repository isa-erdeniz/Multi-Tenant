from setuptools import setup, find_packages

setup(
    name="erdeniz_security",
    version="1.0.0",
    description="ErdenizTech merkezi güvenlik paketi — tek katman, iş + kişisel",
    author="ErdenizTech",
    python_requires=">=3.11",
    packages=find_packages(where="."),
    package_dir={"": "."},
    install_requires=[
        "cryptography>=42.0.0",
        "argon2-cffi>=23.1.0",
        "django-encrypted-model-fields>=0.6.5",
        "django-axes>=6.3.0",
        "django-cors-headers>=4.3.0",
        "django-ratelimit>=4.1.0",
        "django-csp>=3.8",
        "python-decouple>=3.8",
        "django-auditlog>=3.0.0",
    ],
    extras_require={"dev": ["bandit>=1.7.0", "safety>=3.0.0"]},
)
