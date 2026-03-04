# app/models/__init__.py
#
# Imports all ORM model classes so SQLAlchemy's mapper is aware of them.
#
# Why is this necessary?
#   SQLAlchemy discovers table definitions by inspecting which classes have
#   inherited from Base (defined in database.py). A class is only registered
#   when its module is imported. If we never import ProductionRecord, SQLAlchemy
#   doesn't know it exists and relationship joins to it will fail.
#
#   By importing everything here, any code that does `from app.models import *`
#   or simply `import app.models` triggers registration of all five models.

from app.models.data_completeness import DataCompleteness  # noqa: F401
from app.models.inspection import InspectionRecord  # noqa: F401
from app.models.lot import Lot  # noqa: F401 (imported for side effects)
from app.models.production import ProductionRecord  # noqa: F401
from app.models.shipping import ShippingRecord  # noqa: F401
