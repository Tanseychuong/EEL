# EEL — Opportunity Portal: Implementation Plan

## 1. Where things actually stand (checked against the GitHub repo)

## 2. User access levels

## 3. Restructured file layout

```
backend/
├── apps/
│   ├── __init__.py            # factory (needs pushing)
│   │
│   ├── accounts/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── forms.py          # /register /login /refresh /me
│   │   ├── models.py
│   │   ├── serializer.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── migration/
│   │   │
│   ├── opportunities/  
│   │   ├── __init__.py
│   │   ├── admin.py          
│   │   ├── models.py         
│   │   ├── serializers.py       
│   │   ├── urls.py         
│   │   ├── views.py      
│   │   └── migrations/   
│   │   │
│   ├── ingestion/  
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── models.py
│   │   ├── urls.py
│   │   ├── connectors/
│   │   │   ├── __init__.py 
│   │   │   ├── base.py         
│   │   │   └── rss_connector.py 
│   │   │   │       
│   │   ├── management/
│   │   │   ├── __init__.py      
│   │   │   ├── base.py   
│   │   │   └── commands/
│   │   │       └── rss_connector.py
│   │   └── migrations/ 
│   │
├── config/                         # ✅ done
│   ├── __init__.py                 # ✅ done 
│   ├── wsgi.py                     # ✅ done
│   ├── settings.py                 # ✅ done
│   ├── asgi.py.py                  # ✅ done
│   └── urls.py  
├── docs/
│   ├── accounts.md
│   ├── opportunities.md
│   ├── ingestion.md
│   ├── plan.md
│   └── schemas.sql
│   │
├── migrations/ 
├── tests/
│   ├── conftest.py             # NEW — app fixture using TestingConfig + sqlite
│   ├── test_auth.py
│   ├── test_opportunities.py
│   └── test_admin.py
├── manage.py                   # ✅ done
├── requirements.txt            # ✅ done (add pytest, pytest-flask for the tests/ folder)
└── .env.example                # needs pushing
```