from functools import wraps


class _Dependencies:
    _instance = None
    _dependencies = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __contains__(self, dependency):
        return dependency in self._dependencies

    def register(self, dependency):
        self._dependencies[dependency.__class__.__base__] = dependency

    def get(self, dependency_interface):
        return self._dependencies[dependency_interface]


def inject(**injected_dependencies):
    def method_decorator(method):
        @wraps(method)
        def inject_wrapper(*args, **kwargs):
            for dependency_name, dependency_interface in injected_dependencies.items():
                if dependency_interface not in _dependencies:
                    raise RuntimeError(f'Dependency is not registered for interface "{dependency_interface}"')
                kwargs[dependency_name] = _dependencies.get(dependency_interface)
            return method(*args, **kwargs)

        return inject_wrapper

    return method_decorator


_dependencies = _Dependencies()
