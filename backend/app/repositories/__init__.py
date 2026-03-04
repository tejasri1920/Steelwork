# app/repositories/__init__.py
#
# Makes `repositories` a Python package.
# The repository layer is the ONLY place that touches the database.
# Routers call repositories; repositories call SQLAlchemy.
#
# This separation means:
#   - Routers stay thin (HTTP concerns only)
#   - Repositories are independently testable with a fake/test DB session
