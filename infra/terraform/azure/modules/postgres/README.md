# postgres module

Creates Azure PostgreSQL Flexible Server.
High availability can be disabled by setting `high_availability_mode = "Disabled"`.

## pgvector path

After deployment, connect as admin and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
