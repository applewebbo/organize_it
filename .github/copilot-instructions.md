# Coding Guidelines

You are an expert in Python, Django, and scalable web application development. You write secure, maintainable, and performant code following Django and Python best practices.

## Python Best Practices
- Follow PEP 8 with 120 character line limit
- Use double quotes for Python strings
- Sort imports with `isort`
- Use f-strings for string formatting

## Django Best Practices
- Follow Django's "batteries included" philosophy - use built-in features before third-party packages
- Prioritize security and follow Django's security best practices
- Use Django's ORM effectively and avoid raw SQL unless absolutely necessary
- Use Django signals sparingly and document them well.

## Models
- Add `__str__` methods to all models for a better admin interface
- Use `related_name` for foreign keys when needed
- Define `Meta` class with appropriate options (ordering, verbose_name, etc.)
- Use `blank=True` for optional form fields, `null=True` for optional database fields

## Views
- Always validate and sanitize user input
- Handle exceptions gracefully with try/except blocks
- Use `get_object_or_404` instead of manual exception handling
- Implement proper pagination for list views
- Always prefer function-based views over class-based views unless necessary

## URLs
- Use descriptive URL names for reverse URL lookups
- Always end URL patterns with a trailing slash

## Forms
- Use ModelForms when working with model instances
- Use crispy forms for better form rendering

## Templates
- Use template inheritance with base templates
- Use template tags and filters for common operations
- Avoid complex logic in templates - move it to views or template tags
- Use static files properly with `{% load static %}`
- Implement CSRF protection in all forms

## Settings
- Use environment variables in a single `settings.py` file
- Never commit secrets to version control
- Use `django-environ` for managing environment variables
- Use `DEBUG = False` in production and configure allowed hosts properly

## Database
- Use migrations for all database changes
- Optimize queries with `select_related` and `prefetch_related`
- Use database indexes for frequently queried fields
- Avoid N+1 query problems

## Testing
- Always write unit tests and check that they pass for new features.
- Test both positive and negative scenarios
- Always use `pytest`, `pytest-django` and `django-test-plus` for unit tests
- Use a consistent naming convention for test files and functions
- Use fixtures for test data when necessary
- Use `pytestmark = pytest.mark.django_db` at the beginning of the file for tests that require database access
- Always put tests in a tests folder in the root of the project
- Don't test internal Django functions or methods that are already tested by Django itself

## Javascript Add-options
- Use `htmx` when needed and `django-htmx` to implement SPA like features
- Use `alpinejs` for frontend interactivity

## Naming Conventions
- Use kebab-case for template file names (e.g., `my-template.html`)
- Use snake_case for function names (e.g., `my_function`)
- Use PascalCase for model names (e.g., `MyModel`)
- Use snake_case for variable names (e.g., `my_variable`)
- Use UPPERCASE for constants (e.g., `MY_CONSTANT`)
- Use singular nouns for model names (e.g., `Book` instead of `Books`)
- Use plural nouns for model managers (e.g., `BooksManager` for a manager that returns multiple books)
- Use descriptive names for functions and variables (e.g., `calculate_total_price` instead of `calc_price`)

## Documentation
- Use docstrings for all public functions, classes, and methods
