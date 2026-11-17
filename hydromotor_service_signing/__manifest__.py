{
  "name": "Hydromotor — Signing",
  "version": "19.0.1.0.0",
  "summary": "Bounded local service job signing with frozen snapshot and dual signatures",
  "author": "Hydromotor",
  "license": "LGPL-3",
  "depends": ["hydromotor_service", "web"],
  "data": [
    "security/signing_access.xml",
    "views/signing_views.xml",
    "report/signing_report.xml"
  ],
  "application": False,
  "installable": True,
  "auto_install": False
}
