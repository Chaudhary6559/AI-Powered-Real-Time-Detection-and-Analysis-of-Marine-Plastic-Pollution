"""
routes/geo.py – Geospatial data endpoint.

GET /geo-data
  Returns a list of plastic hotspot objects with lat/lon/density/severity
  formatted for map visualisation (Leaflet.js / Mapbox on the frontend).
"""

from __future__ import annotations

from flask import Blueprint, request

from services.geo_analysis import get_geo_data, compute_density_summary
from utils.helpers import success, error

geo_bp = Blueprint("geo", __name__)


@geo_bp.get("/geo-data")
def geo_data():
    """GET /geo-data – Return geospatial hotspot data."""
    # Optional query param: ?live=true  →  include DB records
    use_db = request.args.get("live", "true").lower() != "false"

    try:
        hotspots = get_geo_data(use_db=use_db)
        summary  = compute_density_summary(hotspots)
    except Exception as exc:
        return error(f"Geo data fetch failed: {exc}", 500)

    return success({
        "hotspots": hotspots,
        "summary":  summary,
        "count":    len(hotspots),
    })
