# EEL — Opportunity Portal: Implementation Plan

## 1. Where things actually stand (checked against the GitHub repo)

## 2. User access levels

## 3. Restructured file layout

```
backend/
├── apps/
│   ├── __init__.py           
│   │
│   ├── accounts/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── forms.py          
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
├── config/                         
│   ├── __init__.py                
│   ├── wsgi.py                     
│   ├── settings.py                 
│   ├── asgi.py.py                  
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
│   ├── conftest.py             # 
│   ├── test_auth.py
│   ├── test_opportunities.py
│   └── test_admin.py
├── manage.py                   #
├── requirements.txt            # 
└── .env.example                # 
```