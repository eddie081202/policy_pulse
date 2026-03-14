SAMPLE_POLICY = {
    "meta": {
        "currency": "USD",
        "deductible": 150.0,
        "coinsurance": 0.8,
    },
    "coverage_categories": [
        {
            "id": "diagnostic_imaging",
            "name": "Diagnostic Imaging",
            "description": "CT scans, MRI, X-ray, and ultrasound.",
            "coverage_rate": 0.8,
            "premium_score": 78.0,
            "upgrade_premium_cost": 120.0,
            "upgrade_coverage_rate": 0.95,
            "per_item_limit": 2000.0,
            "scope": "all_conditions",
            "clauses": [{"id": "4.2.1", "text": "Insurer covers 80% of diagnostic imaging."}],
        },
        {
            "id": "hospital_room",
            "name": "Hospital Room and Board",
            "description": "Daily room fee and nursing support.",
            "coverage_rate": 0.7,
            "premium_score": 68.0,
            "upgrade_premium_cost": 700.0,
            "upgrade_coverage_rate": 1.0,
            "per_item_limit": 300.0,
            "scope": "all_conditions",
            "clauses": [{"id": "3.1.2", "text": "Room charge covered up to USD 300 per day."}],
        },
        {
            "id": "emergency_care",
            "name": "Emergency Care",
            "description": "Accident emergency interventions.",
            "coverage_rate": 1.0,
            "premium_score": 82.0,
            "per_item_limit": None,
            "scope": "accident_only",
            "clauses": [{"id": "2.4.0", "text": "Emergency care covered only for accidents."}],
        },
    ],
    "exclusions": [
        {
            "id": "excl_cosmetic",
            "name": "Cosmetic Procedures",
            "text": "Elective cosmetic services are excluded.",
            "clauses": [{"id": "5.1.3", "text": "Cosmetic procedures are excluded."}],
        }
    ],
}


SAMPLE_BILL = {
    "invoice_meta": {
        "date": "2026-03-14",
        "hospital_name": "Metro Hospital",
        "diagnosis": "Hypertension follow-up",
    },
    "line_items": [
        {
            "id": "line_1",
            "item_name": "Computed Tomography (CT) Scan",
            "quantity": 1,
            "unit_cost": 1200.0,
            "total_cost": 1200.0,
        },
        {
            "id": "line_2",
            "item_name": "Hospital Room Charge",
            "quantity": 1,
            "unit_cost": 500.0,
            "total_cost": 500.0,
        },
        {
            "id": "line_3",
            "item_name": "Hospital Room Charge",
            "quantity": 1,
            "unit_cost": 500.0,
            "total_cost": 500.0,
        },
        {
            "id": "line_4",
            "item_name": "Cosmetic facial treatment",
            "quantity": 1,
            "unit_cost": 350.0,
            "total_cost": 350.0,
        },
    ],
}
