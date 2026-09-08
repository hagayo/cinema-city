# Deployment

## פרופיל מומלץ

```text
Browser
  -> HTTPS Gateway / Cloud Run
  -> FastAPI
  -> Clerk Authentication Adapter
  -> Application Services
  -> Neon Repositories
```

## Release

1. הגדירו Secrets ותצורת `.env.production` בפלטפורמת הענן.
2. הריצו `uv sync --frozen` ו-`bash scripts/check.sh`.
3. בנו image עם tag חד-חד-ערכי.
4. הריצו Job עם הרשאת DDL: `uv run alembic upgrade head`.
5. הריצו אחריו `uv run cinema-db-seed` עם הרשאת DML.
6. העלו את השרת עם role ללא DDL.
7. בדקו `/api/health`, Login, הזמנה, ביטול ופעולת מנהל.
8. רק לאחר מכן העבירו תעבורה לגרסה החדשה.

## Cloud Run

ה-container מאזין ל-`0.0.0.0:${PORT}`. הגדירו:

```env
APP_ENV=production
HOST=0.0.0.0
PORT=8080
AUTH_ENABLED=true
AUTH_PROVIDER=clerk
STORAGE_BACKEND=neon
```

הפעילו minimum instances רק אם זמן ה-Cold Start משמעותי. Connection pooling מוגדר עם `pool_pre_ping`; יש לכוון את מגבלת החיבורים לפי מגבלת Neon ומספר ה-instances.

## Gateway יחיד או שניים

למערכת קטנה מומלץ להתחיל ב-`API_MODE=combined`. אם נדרשים isolation, הרשאות deployment או rate limits שונים, פרסו שני containers מאותו image:

```text
customer-api -> API_MODE=customer
manager-api  -> API_MODE=manager
```

אין לשנות Business Logic בין שני ה-deployments.

## Rollback

Rollback של image אינו Rollback של schema. שינויי schema עתידיים חייבים להיות backward-compatible לפחות לגרסה אחת, עם Migration קדימה נפרד ותכנית Restore מתועדת.

## ניהול Schema

- `database/migrations/versions` מכיל את היסטוריית Alembic המחייבת.
- `database/schema.sql` הוא snapshot קריא של המבנה הנוכחי לשימוש חיצוני.
- השרת לעולם אינו מפעיל `metadata.create_all()`.
- Migration חדש נוצר באמצעות `uv run alembic revision --autogenerate -m "description"`, נבדק ידנית ונשמר ב-Git.
- במסד Neon ישן שכבר מכיל טבלאות מלפני Alembic, אין להריץ את המיגרציה הראשונית אוטומטית. יש לגבות, להשוות ל-`schema.sql`, ואז לבצע baseline מבוקר או ליצור מסד חדש.
