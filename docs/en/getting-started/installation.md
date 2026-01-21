# Installation

This guide will help you set up Organize It on your local machine.

## Requirements

Before you begin, ensure you have the following installed:

- **Python 3.14 or higher** - [Download Python](https://www.python.org/downloads/)
- **uv** - Modern Python package manager - [Install uv](https://docs.astral.sh/uv/)
- **just** - Command runner (optional but recommended) - [Install just](https://github.com/casey/just)
- **Git** - For cloning the repository

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/applewebbo/organize_it.git
cd organize_it
```

### 2. Install Dependencies

Use `uv` to install all project dependencies:

```bash
just install
```

Or manually:

```bash
uv sync
```

!!! note
    Never use `pip` with this project - always use `uv` for package management.

### 3. Environment Configuration

Create a `.env` file in the project root with the following configuration:

```bash
# Required settings
SECRET_KEY=your-secret-key-here
ENVIRONMENT=dev
DEBUG=True

# Optional API keys (for enhanced features)
MAPBOX_ACCESS_TOKEN=your-mapbox-token
GOOGLE_PLACES_API_KEY=your-google-places-key
UNSPLASH_ACCESS_KEY=your-unsplash-key
```

!!! tip "Generate a Secret Key"
    You can generate a secure secret key using Python:
    ```bash
    python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
    ```

### 4. Database Setup

Run migrations to set up the database:

```bash
just migrate
```

Or manually:

```bash
uv run python manage.py migrate
```

### 5. Create a Superuser (Optional)

To access the Django admin panel, create a superuser account:

```bash
uv run python manage.py createsuperuser
```

### 6. Run the Development Server

Start the development server with TailwindCSS compilation:

```bash
just local
```

Or for the full stack with background workers:

```bash
just serve
```

The application will be available at [http://localhost:8000](http://localhost:8000)

## Verification

To verify your installation is correct:

1. Visit [http://localhost:8000](http://localhost:8000) in your browser
2. You should see the Organize It homepage
3. Try creating an account and logging in

## Troubleshooting

### Port Already in Use

If port 8000 is already in use, you can specify a different port:

```bash
uv run python manage.py runserver 8080
```

### Database Issues

If you encounter database issues, try:

```bash
just clean
just fresh
```

This will remove all temporary files and reinstall everything from scratch.

### Missing Dependencies

If you see import errors, ensure all dependencies are installed:

```bash
just install
```

## Next Steps

Once installation is complete, proceed to the [Quick Start Guide](quick-start.md) to learn how to use Organize It.

## Development Tools

If you plan to contribute to Organize It, install additional development dependencies:

```bash
just update_all
```

This will:
- Update all dependencies
- Update pre-commit hooks
- Install development tools (pytest, ruff, etc.)

For testing:

```bash
just test      # Run all tests
just ftest     # Run tests in parallel (faster)
```

For code quality:

```bash
just lint      # Run linting and formatting
```
