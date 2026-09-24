"""
18-query hand-labeled eval dataset.
Labels derived by reading sample_code/ files and tracing the call graph manually.

Call graph summary (relevant to impact queries):
  charge_card     → calls: validate_payment
  validate_payment → calls: nothing
  place_order     → calls: check_stock, reserve_item, charge_card, release_item, save_order, notify_user
  get_product     → called by: check_stock, update_stock
  check_stock     → called by: reserve_item, place_order
  update_stock    → called by: complete_order
  send_email      → called by: notify_user, notify_admin
  notify_user     → called by: place_order, cancel_order, complete_order
  notify_admin    → called by: cancel_order
  send_receipt    → called by: complete_order
"""

EVAL_DATASET = [
    # ── code_analysis (6) ────────────────────────────────────────────────
    {
        "query": "What does place_order do?",
        "expected_query_type": "code_analysis",
        "expected_functions": ["place_order"],
    },
    {
        "query": "How does inventory reservation work?",
        "expected_query_type": "code_analysis",
        "expected_functions": ["reserve_item", "check_stock"],
    },
    {
        "query": "How are users notified?",
        "expected_query_type": "code_analysis",
        "expected_functions": ["notify_user"],
    },
    {
        "query": "What does the refund function do?",
        "expected_query_type": "code_analysis",
        "expected_functions": ["refund"],
    },
    {
        "query": "How does check_stock work?",
        "expected_query_type": "code_analysis",
        "expected_functions": ["check_stock"],
    },
    {
        "query": "What does complete_order do?",
        "expected_query_type": "code_analysis",
        "expected_functions": ["complete_order"],
    },
    # ── doc_generation (6) ───────────────────────────────────────────────
    {
        "query": "Generate docs for the refund function",
        "expected_query_type": "doc_generation",
        "expected_functions": ["refund"],
    },
    {
        "query": "Write documentation for cancel_order",
        "expected_query_type": "doc_generation",
        "expected_functions": ["cancel_order"],
    },
    {
        "query": "Document the notify_user function",
        "expected_query_type": "doc_generation",
        "expected_functions": ["notify_user"],
    },
    {
        "query": "Generate documentation for place_order",
        "expected_query_type": "doc_generation",
        "expected_functions": ["place_order"],
    },
    {
        "query": "Write docs for check_stock",
        "expected_query_type": "doc_generation",
        "expected_functions": ["check_stock"],
    },
    {
        "query": "Generate API docs for charge_card",
        "expected_query_type": "doc_generation",
        "expected_functions": ["charge_card"],
    },
    # ── impact_analysis (6) ──────────────────────────────────────────────
    {
        "query": "What breaks if charge_card changes?",
        "expected_query_type": "impact_analysis",
        "expected_functions": ["charge_card"],
        "expected_function": "charge_card",
        "expected_callers": ["place_order"],
        "expected_callees": ["validate_payment"],
    },
    {
        "query": "What breaks if validate_payment changes?",
        "expected_query_type": "impact_analysis",
        "expected_functions": ["validate_payment"],
        "expected_function": "validate_payment",
        "expected_callers": ["charge_card", "place_order"],
        "expected_callees": [],
    },
    {
        "query": "What is affected if get_product changes?",
        "expected_query_type": "impact_analysis",
        "expected_functions": ["get_product"],
        "expected_function": "get_product",
        # depth-2 BFS on reversed graph: check_stock+update_stock (d1),
        # then reserve_item+place_order (via check_stock) + complete_order (via update_stock) (d2)
        "expected_callers": ["check_stock", "update_stock", "reserve_item", "place_order", "complete_order"],
        "expected_callees": ["_load"],
    },
    {
        "query": "What depends on the card charging function?",
        "expected_query_type": "impact_analysis",
        "expected_functions": ["charge_card"],
        "expected_function": "charge_card",   # tests extraction with natural-language phrasing
        "expected_callers": ["place_order"],
        "expected_callees": ["validate_payment"],
    },
    {
        "query": "What breaks if send_email changes?",
        "expected_query_type": "impact_analysis",
        "expected_functions": ["send_email"],
        "expected_function": "send_email",
        "expected_callers": ["notify_user", "notify_admin", "place_order", "cancel_order", "complete_order"],
        "expected_callees": [],
    },
    {
        "query": "What is affected if send_receipt changes?",
        "expected_query_type": "impact_analysis",
        "expected_functions": ["send_receipt"],
        "expected_function": "send_receipt",
        "expected_callers": ["complete_order"],
        "expected_callees": [],
    },
]
