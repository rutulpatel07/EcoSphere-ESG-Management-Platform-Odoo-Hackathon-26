"""Evidence-requirement policy for participation approval endpoints.

``settings.evidence_required`` does not exist as a column on the ``settings``
table in backend/db/schema.sql, and neither that table nor its router
(app/routers/settings.py) are in this owner zone. Per product decision,
evidence is always required to approve/verify participation, so this is
enforced as a constant here rather than invented as a schema field.
"""

EVIDENCE_REQUIRED = True
