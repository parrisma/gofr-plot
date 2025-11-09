from typing import Any, List, Optional
from app.models import GraphData
from app.validation.models import ValidationError, ValidationResult
from app.themes import list_themes


class GraphDataValidator:
    """Validates GraphData with helpful error messages and suggestions"""

    def __init__(self):
        self.valid_types = ["line", "scatter", "bar"]
        self.valid_formats = ["png", "jpg", "svg", "pdf"]
        self.valid_themes = list_themes()

    def validate(self, data: GraphData) -> ValidationResult:
        """
        Validate graph data and return detailed results with comprehensive error handling

        Args:
            data: GraphData instance to validate

        Returns:
            ValidationResult with errors and suggestions
        """
        errors: List[ValidationError] = []

        try:
            # Validate x and y arrays
            try:
                errors.extend(self._validate_arrays(data))
            except Exception as e:
                errors.append(
                    ValidationError(
                        field="arrays",
                        message=f"Error validating arrays: {str(e)}",
                        received_value=None,
                        expected="Valid array data",
                        suggestions=["Check that x and y are valid arrays of numbers"],
                    )
                )

            # Validate type
            try:
                errors.extend(self._validate_type(data))
            except Exception as e:
                errors.append(
                    ValidationError(
                        field="type",
                        message=f"Error validating type: {str(e)}",
                        received_value=data.type if hasattr(data, "type") else None,
                        expected="Valid chart type",
                        suggestions=["Use 'line', 'scatter', or 'bar'"],
                    )
                )

            # Validate format
            try:
                errors.extend(self._validate_format(data))
            except Exception as e:
                errors.append(
                    ValidationError(
                        field="format",
                        message=f"Error validating format: {str(e)}",
                        received_value=data.format if hasattr(data, "format") else None,
                        expected="Valid output format",
                        suggestions=["Use 'png', 'jpg', 'svg', or 'pdf'"],
                    )
                )

            # Validate theme
            try:
                errors.extend(self._validate_theme(data))
            except Exception as e:
                errors.append(
                    ValidationError(
                        field="theme",
                        message=f"Error validating theme: {str(e)}",
                        received_value=data.theme if hasattr(data, "theme") else None,
                        expected="Valid theme name",
                        suggestions=["Use 'light' or 'dark'"],
                    )
                )

            # Validate numeric ranges
            try:
                errors.extend(self._validate_numeric_ranges(data))
            except Exception as e:
                errors.append(
                    ValidationError(
                        field="numeric_values",
                        message=f"Error validating numeric ranges: {str(e)}",
                        received_value=None,
                        expected="Valid numeric parameters",
                        suggestions=["Check alpha (0-1), line_width (>0), marker_size (>0)"],
                    )
                )

            # Validate color format
            try:
                errors.extend(self._validate_color(data))
            except Exception as e:
                errors.append(
                    ValidationError(
                        field="color",
                        message=f"Error validating color: {str(e)}",
                        received_value=data.color if hasattr(data, "color") else None,
                        expected="Valid color format",
                        suggestions=[
                            "Use hex (#FF5733), rgb(255,87,51), or color name (red, blue, etc.)"
                        ],
                    )
                )

            return ValidationResult(is_valid=len(errors) == 0, errors=errors)

        except Exception as e:
            # Ultimate fallback - if validation itself fails
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        field="validation_system",
                        message=f"Critical validation error: {str(e)}",
                        received_value=None,
                        expected="Valid graph data",
                        suggestions=[
                            "The validation system encountered an unexpected error",
                            "Please check your input data format",
                        ],
                    )
                ],
            )

    def _validate_arrays(self, data: GraphData) -> List[ValidationError]:
        """Validate x and y arrays"""
        errors = []

        # Check if arrays are empty
        if not data.x:
            errors.append(
                ValidationError(
                    field="x",
                    message="X-axis data cannot be empty",
                    received_value=data.x,
                    expected="Non-empty list of numbers",
                    suggestions=["Provide at least one data point", "Example: [1, 2, 3, 4, 5]"],
                )
            )

        if not data.y:
            errors.append(
                ValidationError(
                    field="y",
                    message="Y-axis data cannot be empty",
                    received_value=data.y,
                    expected="Non-empty list of numbers",
                    suggestions=[
                        "Provide at least one data point",
                        "Example: [10, 20, 15, 30, 25]",
                    ],
                )
            )

        # Check if arrays have matching lengths
        if data.x and data.y and len(data.x) != len(data.y):
            errors.append(
                ValidationError(
                    field="x, y",
                    message=f"X and Y arrays must have the same length. X has {len(data.x)} points, Y has {len(data.y)} points",
                    received_value={"x_length": len(data.x), "y_length": len(data.y)},
                    expected="Arrays of equal length",
                    suggestions=[
                        f"Add {abs(len(data.x) - len(data.y))} more point(s) to the shorter array",
                        "Remove extra points from the longer array",
                        "Ensure each X value has a corresponding Y value",
                    ],
                )
            )

        # Check for minimum data points
        if data.x and len(data.x) < 2 and data.type == "line":
            errors.append(
                ValidationError(
                    field="x, y",
                    message="Line charts require at least 2 data points",
                    received_value=len(data.x),
                    expected="At least 2 points",
                    suggestions=[
                        "Add more data points to create a line",
                        "Use 'scatter' type for single points",
                        "Example: x=[1, 2], y=[10, 20]",
                    ],
                )
            )

        return errors

    def _validate_type(self, data: GraphData) -> List[ValidationError]:
        """Validate chart type"""
        errors = []

        if data.type not in self.valid_types:
            errors.append(
                ValidationError(
                    field="type",
                    message=f"Invalid chart type '{data.type}'",
                    received_value=data.type,
                    expected=f"One of: {', '.join(self.valid_types)}",
                    suggestions=[
                        f"Use 'line' for line charts",
                        f"Use 'scatter' for scatter plots",
                        f"Use 'bar' for bar charts",
                        f"Did you mean '{self._find_closest_match(data.type, self.valid_types)}'?",
                    ],
                )
            )

        return errors

    def _validate_format(self, data: GraphData) -> List[ValidationError]:
        """Validate output format"""
        errors = []

        if data.format not in self.valid_formats:
            errors.append(
                ValidationError(
                    field="format",
                    message=f"Invalid output format '{data.format}'",
                    received_value=data.format,
                    expected=f"One of: {', '.join(self.valid_formats)}",
                    suggestions=[
                        "Use 'png' for standard raster images",
                        "Use 'svg' for scalable vector graphics",
                        "Use 'pdf' for documents",
                        "Use 'jpg' for compressed images",
                        f"Did you mean '{self._find_closest_match(data.format, self.valid_formats)}'?",
                    ],
                )
            )

        return errors

    def _validate_theme(self, data: GraphData) -> List[ValidationError]:
        """Validate theme"""
        errors = []

        if data.theme not in self.valid_themes:
            errors.append(
                ValidationError(
                    field="theme",
                    message=f"Invalid theme '{data.theme}'",
                    received_value=data.theme,
                    expected=f"One of: {', '.join(self.valid_themes)}",
                    suggestions=[
                        "Use 'light' for bright backgrounds",
                        "Use 'dark' for dark mode",
                        f"Available themes: {', '.join(self.valid_themes)}",
                        f"Did you mean '{self._find_closest_match(data.theme, self.valid_themes)}'?",
                    ],
                )
            )

        return errors

    def _validate_numeric_ranges(self, data: GraphData) -> List[ValidationError]:
        """Validate numeric parameter ranges"""
        errors = []

        # Validate alpha
        if not 0.0 <= data.alpha <= 1.0:
            errors.append(
                ValidationError(
                    field="alpha",
                    message=f"Alpha (transparency) must be between 0.0 and 1.0",
                    received_value=data.alpha,
                    expected="Number between 0.0 (transparent) and 1.0 (opaque)",
                    suggestions=[
                        "Use 0.0 for fully transparent",
                        "Use 1.0 for fully opaque",
                        "Use 0.5 for semi-transparent",
                        f"Try: {max(0.0, min(1.0, data.alpha))}",
                    ],
                )
            )

        # Validate line_width
        if data.line_width <= 0:
            errors.append(
                ValidationError(
                    field="line_width",
                    message=f"Line width must be positive",
                    received_value=data.line_width,
                    expected="Positive number (typically 0.5 to 5.0)",
                    suggestions=[
                        "Use 1.0 for thin lines",
                        "Use 2.0 for normal lines",
                        "Use 3.0 or higher for thick lines",
                        "Try: 2.0",
                    ],
                )
            )

        # Validate marker_size
        if data.marker_size <= 0:
            errors.append(
                ValidationError(
                    field="marker_size",
                    message=f"Marker size must be positive",
                    received_value=data.marker_size,
                    expected="Positive number (typically 10 to 200)",
                    suggestions=[
                        "Use 20 for small markers",
                        "Use 36 for normal markers",
                        "Use 100 for large markers",
                        "Try: 36",
                    ],
                )
            )

        return errors

    def _validate_color(self, data: GraphData) -> List[ValidationError]:
        """Validate color format"""
        errors = []

        if data.color is None:
            return errors

        color = data.color.strip()

        # Check if it's a valid format (hex, named color, or rgb)
        is_hex = color.startswith("#") and len(color) in [4, 7, 9]
        is_rgb = color.startswith("rgb(") and color.endswith(")")
        is_rgba = color.startswith("rgba(") and color.endswith(")")

        # List of common named colors
        named_colors = [
            "red",
            "blue",
            "green",
            "yellow",
            "orange",
            "purple",
            "pink",
            "black",
            "white",
            "gray",
            "brown",
            "cyan",
            "magenta",
        ]
        is_named = color.lower() in named_colors

        if not (is_hex or is_rgb or is_rgba or is_named):
            errors.append(
                ValidationError(
                    field="color",
                    message=f"Invalid color format '{data.color}'",
                    received_value=data.color,
                    expected="Hex (#RGB, #RRGGBB), rgb(r,g,b), rgba(r,g,b,a), or color name",
                    suggestions=[
                        "Use hex format: '#FF5733' or '#F53'",
                        "Use RGB format: 'rgb(255,87,51)'",
                        "Use RGBA format: 'rgba(255,87,51,0.8)'",
                        "Use named colors: 'red', 'blue', 'green', etc.",
                        f"Common colors: {', '.join(named_colors[:6])}",
                    ],
                )
            )

        return errors

    def _find_closest_match(self, value: str, options: List[str]) -> str:
        """Find the closest matching option using simple string similarity"""
        if not options:
            return ""

        value_lower = value.lower()

        # Check for exact substring matches first
        for option in options:
            if value_lower in option.lower() or option.lower() in value_lower:
                return option

        # Check for common prefixes
        for option in options:
            if option.lower().startswith(value_lower[0]) if value_lower else False:
                return option

        # Return first option as fallback
        return options[0]
