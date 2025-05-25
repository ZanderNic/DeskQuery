from typing import Any, TypedDict

class FunctionRegistryExpectedFormat(TypedDict):
    data: dict[str, Any]
    plotable: bool