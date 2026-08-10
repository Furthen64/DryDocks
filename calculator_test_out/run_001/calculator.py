import sys

def add(a, b):
    return a + b
def subtract(a, b):
    return a - b
def divide(a, b):
    return a / b
def power(a, b):
    return a ** b
def calculate(operation, a, b):
    if operation == 'add':
        return add(a, b)
    elif operation == 'subtract':
        return subtract(a, b)
    elif operation == 'divide':
        return divide(a, b)
    elif operation == 'power':
        return power(a, b)
    else:
        raise ValueError("Invalid operation")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python calculator.py <operation> <a> <b>")
    else:
        op = sys.argv[1]
        a = float(sys.argv[2])
        b = float(sys.argv[3])
        result = calculate(op, a, b)
        print(result)