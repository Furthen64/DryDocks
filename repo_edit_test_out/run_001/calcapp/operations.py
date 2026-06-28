def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def calculate(operation, a, b):
    if operation == "add":
        return add(a, b)
    if operation == "subtract":
        return subtract(a, b)
    raise ValueError(f"unsupported operation: {operation}")
