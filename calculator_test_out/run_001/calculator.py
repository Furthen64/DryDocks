#!/usr/bin/env python3
"""A simple calculator CLI application."""

import sys

def add(a, b):
    """Return the sum of a and b."""
    return a + b

def subtract(a, b):
    """Return the difference of a and b."""
    return a - b

def divide(a, b):
    """Return the quotient of a and b. Raises ZeroDivisionError if b is zero."""
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero.")
    return a / b

def power(a, b):
    """Return a raised to the power of b."""
    return a ** b

def calculate(operation, a, b):
    """Perform a calculation based on the operation type."""
    operations = {
        'add': add,
        'subtract': subtract,
        'divide': divide,
        'power': power
    }
    
    if operation in operations:
        return operations[operation](a, b)
    else:
        raise ValueError(f"Unsupported operation: {operation}")

def main():
    """Main entry point for the CLI."""
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
    except ZeroDivisionError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
