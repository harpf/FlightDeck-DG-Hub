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
            "weight_range_g": {"type": "string", "nullable": True, "example": "175 g"},
            "plastic_type": {"type": "string", "nullable": True, "example": "Star"},
            "stability": {"type": "string", "nullable": True, "example": "überstabil"},
            "price": {"type": "string", "nullable": True, "example": "22.90 EUR"},
            "created_at": {"type": "string", "format": "date-time"},
            "reviews": {"type": "array", "items": review_schema},
        },
    }
    error_schema = {
        "type": "object",
        "properties": {"error": {"type": "string", "example": "Invalid API token"}},
    }
    product_input_schema = {
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {"type": "string", "example": "Wraith"},
            "manufacturer": {"type": "string", "nullable": True, "example": "Innova"},
            "category": {"type": "string", "example": "Disc", "description": "Default: 'Disc'"},
            "description": {"type": "string", "nullable": True},
            "product_url": {"type": "string", "nullable": True},
            "image_url": {"type": "string", "nullable": True},
            "disc_type": {"type": "string", "nullable": True, "example": "Distance Driver"},
            "speed": {"type": "integer", "nullable": True, "example": 11},
            "glide": {"type": "integer", "nullable": True, "example": 5},
            "turn": {"type": "integer", "nullable": True, "example": -1},
            "fade": {"type": "integer", "nullable": True, "example": 3},
            "diameter_cm": {"type": "number", "nullable": True},
            "weight_range_g": {"type": "string", "nullable": True},
            "plastic_type": {"type": "string", "nullable": True},
            "stability": {"type": "string", "nullable": True},
            "price": {"type": "string", "nullable": True, "example": "22.90 EUR"},
        },
    }
    source_input_schema = {
        "type": "object",
        "required": ["source_url"],
        "properties": {
            "source_url": {"type": "string", "example": "https://shop.example/kat/discs/"},
            "note": {"type": "string", "nullable": True},
            "status": {"type": "string", "enum": ["open", "approved", "rejected"], "example": "open"},
        },
    }
    review_input_schema = {
        "type": "object",
        "required": ["rating"],
        "properties": {
            "rating": {"type": "integer", "minimum": 1, "maximum": 5, "example": 5},
            "comment": {"type": "string", "nullable": True},
        },
    }
    scan_result_schema = {
        "type": "object",
        "properties": {
            "found": {"type": "integer", "example": 12},
            "created": {"type": "integer", "example": 10},
            "duplicates": {"type": "integer", "example": 2},
        },
    }
    unauthorized = {
        "description": "Fehlender oder ungültiger API-Token",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    }
    forbidden = {
        "description": "Token ohne Schreibrechte (Admin-Scope erforderlich)",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    }
    not_found = {
        "description": "Nicht gefunden",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    }
    admin_security = [{"ApiTokenAuth": []}]

    def _json_body(ref):
        return {"required": True, "content": {"application/json": {"schema": {"$ref": ref}}}}

    def _product_response(code, desc):
        return {code: {"description": desc, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Product"}}}}}

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
            {"name": "Admin", "description": "Schreibzugriff – erfordert einen Admin-API-Token"},
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
                "ProductInput": product_input_schema,
                "SourceInput": source_input_schema,
                "ReviewInput": review_input_schema,
                "ScanResult": scan_result_schema,
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
                },
                "post": {
                    "tags": ["Admin"],
                    "summary": "Produkt anlegen (Admin-Token)",
                    "security": admin_security,
                    "requestBody": _json_body("#/components/schemas/ProductInput"),
                    "responses": {
                        "201": _product_response("201", "Produkt erstellt")["201"],
                        "400": {"description": "Ungültige Eingabe", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "401": unauthorized,
                        "403": forbidden,
                    },
                },
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
                        "404": not_found,
                    },
                },
                "patch": {
                    "tags": ["Admin"],
                    "summary": "Produkt aktualisieren (Admin-Token)",
                    "security": admin_security,
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "requestBody": _json_body("#/components/schemas/ProductInput"),
                    "responses": {
                        "200": _product_response("200", "Produkt aktualisiert")["200"],
                        "401": unauthorized,
                        "403": forbidden,
                        "404": not_found,
                    },
                },
                "delete": {
                    "tags": ["Admin"],
                    "summary": "Produkt löschen (Admin-Token)",
                    "security": admin_security,
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {
                        "204": {"description": "Gelöscht"},
                        "401": unauthorized,
                        "403": forbidden,
                        "404": not_found,
                    },
                },
            },
            "/api/v1/products/{id}/reviews": {
                "post": {
                    "tags": ["Admin"],
                    "summary": "Bewertung anlegen/aktualisieren (Admin-Token)",
                    "security": admin_security,
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "requestBody": _json_body("#/components/schemas/ReviewInput"),
                    "responses": {
                        "201": {"description": "Bewertung erstellt", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Review"}}}},
                        "200": {"description": "Bewertung aktualisiert", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Review"}}}},
                        "400": {"description": "Ungültige Eingabe", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "401": unauthorized,
                        "403": forbidden,
                        "404": not_found,
                    },
                },
            },
            "/api/v1/sources": {
                "post": {
                    "tags": ["Admin"],
                    "summary": "Source-Request anlegen (Admin-Token)",
                    "security": admin_security,
                    "requestBody": _json_body("#/components/schemas/SourceInput"),
                    "responses": {
                        "201": {"description": "Source-Request erstellt", "content": {"application/json": {"schema": {"type": "object"}}}},
                        "400": {"description": "Ungültige Eingabe", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                        "401": unauthorized,
                        "403": forbidden,
                    },
                },
            },
            "/api/v1/sources/{id}": {
                "patch": {
                    "tags": ["Admin"],
                    "summary": "Source-Status ändern (Admin-Token)",
                    "security": admin_security,
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "requestBody": _json_body("#/components/schemas/SourceInput"),
                    "responses": {
                        "200": {"description": "Source aktualisiert", "content": {"application/json": {"schema": {"type": "object"}}}},
                        "401": unauthorized,
                        "403": forbidden,
                        "404": not_found,
                    },
                },
            },
            "/api/v1/sources/{id}/scan": {
                "post": {
                    "tags": ["Admin"],
                    "summary": "Source scannen und Produkte importieren (Admin-Token)",
                    "description": "Scannt eine freigegebene Quelle und legt neue Produkte an.",
                    "security": admin_security,
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {
                        "200": {"description": "Scan-Ergebnis", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ScanResult"}}}},
                        "401": unauthorized,
                        "403": forbidden,
                        "404": not_found,
                        "409": {"description": "Quelle nicht freigegeben", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    },
                },
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
