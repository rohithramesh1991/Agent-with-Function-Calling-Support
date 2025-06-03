available_functions = {}
definitions = []

def register_tool(name, definition):
    def decorator(fn):
        available_functions[name] = fn
        definitions.append(definition)
        return fn
    return decorator
