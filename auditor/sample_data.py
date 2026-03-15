SAMPLE_POLICY = {
    "policy": {
        "meta": {
            "policy_id": "A1",
            "policy_name": "Current Policy A1",
            "currency": "USD",
            "deductibles": {
                "Hospital Room and Board": 150,
                "Diagnostic Imaging": 100,
            },
            "coinsurance": None,
        },
        "coverage_categories": [
            {
                "name": "Diagnostic Imaging",
                "description": "CT scans, MRI, X-ray, and ultrasound.",
                "coverage_rate": "80% up to limits",
                "limits": {"per_item": 2000},
                "premium_score": 78.0,
                "upgrade_premium_cost": 120.0,
                "upgrade_coverage_rate": 0.95,
                "scope": "all_conditions",
                "core_clauses": [
                    "Insurer covers 80% of diagnostic imaging.",
                    "Coverage applies to medically necessary scans.",
                ],
            },
            {
                "name": "Hospital Room and Board",
                "description": "Daily room fee and nursing support.",
                "coverage_rate": "70% up to limits",
                "limits": {"per_day": 300},
                "premium_score": 68.0,
                "upgrade_premium_cost": 700.0,
                "upgrade_coverage_rate": 1.0,
                "scope": "all_conditions",
                "core_clauses": [
                    "Room charge covered up to USD 300 per day.",
                    "Services must be provided by licensed facilities.",
                ],
            },
            {
                "name": "Emergency Care",
                "description": "Accident emergency interventions.",
                "coverage_rate": "100%",
                "premium_score": 82.0,
                "scope": "accident_only",
                "core_clauses": [
                    "Emergency care covered only for accidents.",
                ],
            },
        ],
        "exclusions": [
            "Elective cosmetic services are excluded.",
            "Experimental treatment without policy endorsement is excluded.",
        ],
    }
}


SAMPLE_SIMILAR_POLICIES = [
    {
        "policy": {
            "meta": {
                "policy_id": "B1",
                "policy_name": "Alternative Policy B1",
                "currency": "USD",
                "deductibles": {"General": 100},
                "coinsurance": 0.85,
            },
            "coverage_categories": [
                {
                    "name": "Diagnostic Imaging",
                    "description": "CT scans, MRI, X-ray, and ultrasound.",
                    "coverage_rate": "90%",
                    "premium_score": 70.0,
                    "scope": "all_conditions",
                    "core_clauses": ["Insurer covers 90% of diagnostic imaging."],
                },
                {
                    "name": "Hospital Room and Board",
                    "description": "Daily room fee and nursing support.",
                    "coverage_rate": "90%",
                    "premium_score": 65.0,
                    "scope": "all_conditions",
                    "core_clauses": ["Room charge covered up to USD 400 per day."],
                },
                {
                    "name": "Emergency Care",
                    "description": "Accident emergency interventions.",
                    "coverage_rate": "100%",
                    "premium_score": 78.0,
                    "scope": "accident_only",
                    "core_clauses": ["Emergency care covered only for accidents."],
                },
            ],
            "exclusions": ["Elective cosmetic services are excluded."],
        },
    },
    {
        "policy": {
            "meta": {
                "policy_id": "C1",
                "policy_name": "Alternative Policy C1",
                "currency": "USD",
                "deductibles": {"General": 300},
                "coinsurance": 0.75,
            },
            "coverage_categories": [
                {
                    "name": "Diagnostic Imaging",
                    "description": "CT scans, MRI, X-ray, and ultrasound.",
                    "coverage_rate": "75%",
                    "premium_score": 90.0,
                    "scope": "all_conditions",
                    "core_clauses": ["Insurer covers 75% of diagnostic imaging."],
                },
                {
                    "name": "Hospital Room and Board",
                    "description": "Daily room fee and nursing support.",
                    "coverage_rate": "65%",
                    "premium_score": 92.0,
                    "scope": "all_conditions",
                    "core_clauses": ["Room charge covered up to USD 280 per day."],
                },
                {
                    "name": "Emergency Care",
                    "description": "Accident emergency interventions.",
                    "coverage_rate": "100%",
                    "premium_score": 88.0,
                    "scope": "accident_only",
                    "core_clauses": ["Emergency care covered only for accidents."],
                },
            ],
            "exclusions": ["Elective cosmetic services are excluded."],
        },
    },
]


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
