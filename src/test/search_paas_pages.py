#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.confluence.confluence_kb import ConfluenceKnowledgeBase


def search_paas_pages():
    kb = ConfluenceKnowledgeBase()
    pages = kb.load_all_pages()

    # Search for pages in DOC space
    doc_pages = [p for p in pages if p["space_name"] == "DOC"]
    print(f"Found {len(doc_pages)} pages in DOC space")

    # Filter pages related to PaaS
    paas_related_pages = []
    for page in doc_pages:
        title = page["title"].lower()
        if "paas" in title:
            paas_related_pages.append(page)

    print(f"\nFound {len(paas_related_pages)} pages related to PaaS:")
    for page in paas_related_pages:
        print(f"- {page['title']} (ID: {page['page_id']})")
        print(f"  URL: {page['url']}")
        print(f"  Author: {page['author']}")
        print(f"  Created: {page['created_at']}")
        print(f"  Updated: {page['updated_at']}")
        print()


if __name__ == "__main__":
    search_paas_pages()
