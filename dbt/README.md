# dbt for Benefits API

This directory contains the dbt (data build tool) project for the Benefits API data pipeline.

## Overview

dbt is used to transform data in your PostgreSQL database using SQL. It provides:
- **Models**: SQL transformations that build tables/views
- **Tests**: Data quality checks
- **Documentation**: Auto-generated docs for your data models
- **Version Control**: Track changes to your data pipeline in git

## Project Structure

```
dbt/
├── dbt_project.yml      # Project configuration
├── profiles.yml         # Database connection settings
├── models/              # SQL models (transformations)
│   └── staging/        # Raw data staging models
├── tests/               # Custom data tests
├── macros/              # Reusable SQL snippets
├── seeds/               # Static data files
└── snapshots/           # Type 2 SCD tracking
```

## Quick Start

### Prerequisites
- Python 3.10+ with virtual environment activated
- PostgreSQL database access
- Environment variables set (see below)

### Environment Variables
Set these in your `.env` file:
```bash
DB_HOST=localhost
DB_USER=your_db_user
DB_PASS=your_db_password
DB_NAME=your_db_name
DB_SCHEMA=analytics  # Optional, defaults to 'analytics'
```

### Commands

All dbt commands are available via Makefile targets:

```bash
# Check dbt version
make dbt-version

# Test database connection
make dbt-debug

# Build all models
make dbt-build

# Run tests
make dbt-test

# Generate documentation
make dbt-docs

# Serve documentation locally
make dbt-docs-serve

# Clean build artifacts
make dbt-clean
```

## Adding New Models

1. Create SQL files in `models/` subdirectories
2. Use the `{{ ref('model_name') }}` function to reference other models
3. Run `make dbt-build` to build your models

### Example Model
```sql
-- models/staging/my_model.sql
SELECT 
    id,
    name,
    created_at
FROM {{ ref('source_table') }}
WHERE active = true
```

## Best Practices

- **Staging**: Start with staging models that clean raw data
- **Marts**: Build business-level models for end users
- **Testing**: Add tests to ensure data quality
- **Documentation**: Document your models with `description` in YAML

## Database Schema

Models are created in the `analytics` schema by default. You can change this by setting `DB_SCHEMA` environment variable.

## Troubleshooting

- **Connection issues**: Check your environment variables and database credentials
- **Build errors**: Check the SQL syntax and table references
- **Permission errors**: Ensure your database user has CREATE privileges on the target schema

## Resources

- [dbt Documentation](https://docs.getdbt.com/)
- [dbt Best Practices](https://docs.getdbt.com/guides/best-practices)
- [dbt Community](https://community.getdbt.com/) 