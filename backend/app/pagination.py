"""
Single shared helper so every list endpoint paginates the same way,
reading limits from config.DEFAULT_PAGE_SIZE / config.MAX_PAGE_SIZE
rather than hard-coding page sizes per route.

Phase 2 will fill this in, e.g.:

    from flask import current_app, request

    def paginate(query, schema):
        page = request.args.get("page", 1, type=int)
        per_page = min(
            request.args.get("per_page", current_app.config["DEFAULT_PAGE_SIZE"], type=int),
            current_app.config["MAX_PAGE_SIZE"],
        )
        result = query.paginate(page=page, per_page=per_page, error_out=False)
        return {
            "items": schema.dump(result.items, many=True),
            "page": result.page,
            "per_page": result.per_page,
            "total": result.total,
            "pages": result.pages,
        }
"""
