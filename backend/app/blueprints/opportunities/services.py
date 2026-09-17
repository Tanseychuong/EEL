"""
Business logic for opportunities, kept out of routes.py so it's testable
on its own and reusable (e.g. from the admin blueprint or a future CLI
command) without duplicating the rules.

Phase 2 will add functions here such as:
    submit_opportunity(user, data) -> Opportunity
    list_visible_opportunities(user, category=None, page=1) -> Pagination
"""
