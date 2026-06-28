#!/usr/bin/env python3

"""A simple calculator module with basic arithmetic operations."""

def add(a, b):
    """Add two numbers."""
    return a + b

def subtract(a, b):
    """Subtract b from a."""
    return a - b

def divide(a, b):
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b

def power(a, b):
    """Raise a to the power of b."""
    return a ** b

def calculate(operation, a, b):
    """Perform an operation on two numbers."""
    operations = {
        'add': add,
        'subtract': subtract,
        'divide': divide,
        'power': power
    }
    if operation not in operations:
        raise ValueError(f"Unsupported operation: {operation}")
    return operations[operation](a, b)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 4:
        print("Usage: python calculator.py <operation> <a> <b>")
        print("Operations: add, subtract, divide, power")
        sys.exit(1)
    
    operation = sys.argv[1]
    try:
        a = float(sys.argv[2])
        b = float(sys.argv[3])
        result = calculate(operation, a, b)
        print(result)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)