"""
Schema Validator - Validación de inputs/outputs contra JSON Schemas

Responsabilidad:
- Validar datos contra JSON Schema
- Bloquear ejecuciones inválidas
- Proveer errores claros y accionables
- NO ejecutar nada
- NO transformar datos
"""

import jsonschema
from jsonschema import Draft7Validator
from typing import Any


class ValidationError(Exception):
    """Error de validación de schema."""
    
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Schema validation failed: {', '.join(errors)}")


class SchemaValidator:
    """
    Validador de schemas JSON.
    
    Usa jsonschema Draft 7 para validación estricta.
    """
    
    @staticmethod
    def validate_input(data: Any, schema: dict) -> None:
        """
        Valida input contra schema.
        
        Args:
            data: Datos a validar
            schema: JSON Schema
        
        Raises:
            ValidationError: Si la validación falla
        """
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(data))
        
        if errors:
            error_messages = [
                f"{'.'.join(str(p) for p in error.path)}: {error.message}"
                for error in errors
            ]
            raise ValidationError(error_messages)
    
    @staticmethod
    def validate_output(data: Any, schema: dict) -> None:
        """
        Valida output contra schema.
        
        Args:
            data: Datos a validar
            schema: JSON Schema
        
        Raises:
            ValidationError: Si la validación falla
        """
        # Mismo comportamiento que validate_input
        # Separado por claridad semántica
        SchemaValidator.validate_input(data, schema)


__all__ = ["SchemaValidator", "ValidationError"]
