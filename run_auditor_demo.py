import json

from auditor.entities import Bill, Policy
from auditor.services import audit_invoice
from auditor.sample_data import SAMPLE_BILL, SAMPLE_POLICY


def main() -> None:
    policy = Policy.from_dict(SAMPLE_POLICY)
    bill = Bill.from_dict(SAMPLE_BILL)

    result = audit_invoice(policy=policy, bill=bill)
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
