"""OpenAPI 3.0 specification for the FlightDeck DG Hub REST API.

Kept as a plain dict and served at /api/openapi.json so the API can be
documented and explored via an embedded Swagger UI (/api/docs) without adding a
heavyweight framework dependency. The spec is hand-maintained to match the
serializers and routes in app/routes.py.
"""

API_VERSION = "1.0.0"


def build_openapi_spec() -> dict:
    review_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer", "example": 1},
            "rating": {"type": "integer", "minimum": 1, "maximum": 5, "example": 5},
            "comment": {"type": "string", "nullable": True, "example": "Mein Go-to-Driver bei Wind."},
            "created_at": {"type": "string", "format": "date-time"},
            "username": {"type": "string", "example": "discgolfer"},
        },
    }
    flight_numbers_schema = {
        "type": "object",
        "properties": {
            "speed": {"type": "integer", "nullable": True, "example": 12},
            "glide": {"type": "integer", "nullable": True, "example": 5},
            "turn": {"type": "integer", "nullable": True, "example": -1},
            "fade": {"type": "integer", "nullable": True, "example": 3},
        },
    }
    product_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer", "example": 1},
            "name": {"type": "string", "example": "Destroyer"},
            "manufacturer": {"type": "string", "nullable": True, "example": "Innova"},
            "category": {"type": "string", "example": "Disc"},
            "description": {"type": "string", "nullable": True},
            "product_url": {"type": "string", "nullable": True},
            "disc_type": {"type": "string", "nullable": True, "example": "Distance Driver"},
            "flight_numbers": flight_numbers_schema,
            "diameter_cm": {"type": "number", "nullable": True, "example": 21.1},
            "weight_range_g": {"type": "string", "nullable": True, "example": "165-175 g"},
            "plastic_type": {"type": "string", "nullable": True, "example": "Star"},
            "stability": {"type": "string", "nullable": True, "example": "overstable"},
            "created_at": {"type": "string", "format": "date-time"},
            "reviews": {"type": "array", "items": review_schema},
        },
    }
    error_schema = {
        "type": "object",
        "properties": {"error": {"type": "string", "example": "Invalid API token"}},
    }
    unauthorized = {
        "description": "Fehlender oder ungültiger API-Token",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    }

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "FlightDeck DG Hub API",
            "version": API_VERSION,
            "description": (
                "Lesendes REST-API für ausgewählte Anwendungsdaten (Discs/Produkte, "
                "Reviews, Source-Requests). Authentifizierung über einen statischen "
                "API-Token im Header `X-API-Token: <id>.<secret>` (im Admin-Dashboard "
                "erstellt). Kein Browser/Session erforderlich."
            ),
        },
        "servers": [{"url": "/", "description": "Aktueller Host"}],
        "tags": [
            {"name": "System", "description": "Status & Health"},
            {"name": "Products", "description": "Discs und Produkte"},
            {"name": "Export", "description": "Vollexport"},
        ],
        "components": {
            "securitySchemes": {
                "ApiTokenAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Token",
                    "description": "Format: `<token-id>.<secret>` – im Admin-Dashboard erstellt.",
                }
            },
            "schemas": {
                "Product": product_schema,
                "Review": review_schema,
                "Error": error_schema,
            },
        },
        "paths": {
            "/api/v1/health": {
                "get": {
                    "tags": ["System"],
                    "summary": "Liveness-Check (öffentlich)",
                    "security": [],
                    "responses": {
                        "200": {
                            "description": "Service läuft",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "example": "ok"},
                                            "service": {"type": "string", "example": "flightdeck-dg-hub"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/v1/products": {
                "get": {
                    "tags": ["Products"],
                    "summary": "Produktliste",
                    "description": "Liste der Produkte; unterstützt die Filter `q` und `category`.",
                    "security": [{"ApiTokenAuth": []}],
                    "parameters": [
                        {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "Freitext (Name/Hersteller)"},
                        {"name": "category", "in": "query", "schema": {"type": "string"}, "description": "Kategorie-Filter"},
                    ],
                    "responses": {
                        "200": {
                            "description": "Produktliste",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "count": {"type": "integer", "example": 8},
                                            "products": {"type": "array", "items": {"$ref": "#/components/schemas/Product"}},
                                        },
                                    }
                                }
                            },
                        },
                        "401": unauthorized,
                    },
                }
            },
            "/api/v1/products/{id}": {
                "get": {
                    "tags": ["Products"],
                    "summary": "Einzelprodukt inkl. Reviews",
                    "security": [{"ApiTokenAuth": []}],
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Produkt",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Product"}}},
                        },
                        "401": unauthorized,
                        "404": {
                            "description": "Produkt nicht gefunden",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
                        },
                    },
                }
            },
            "/api/v1/full": {
                "get": {
                    "tags": ["Export"],
                    "summary": "Vollexport (Produkte + Source-Requests)",
                    "security": [{"ApiTokenAuth": []}],
                    "responses": {
                        "200": {
                            "description": "Vollständiger Export",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "products": {"type": "array", "items": {"$ref": "#/components/schemas/Product"}},
                                            "source_requests": {"type": "array", "items": {"type": "object"}},
                                        },
                                    }
                                }
                            },
                        },
                        "401": unauthorized,
                    },
                }
            },
        },
    }
