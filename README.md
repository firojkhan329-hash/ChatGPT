# Visitor Management System

A lightweight starter project for a visitor management system covering pre-enrollment, walk-ins, approvals, access control sync, badge printing, blacklisting, reporting, multi-branch support, and notifications.

## Features
- Pre-enrollment and pre-approved visitor creation
- Walk-in registration
- Approve/Deny workflows
- Access control integration stub
- Visitor badge printing stub
- Blacklist visitor handling
- Detailed visitor reports endpoint
- Multi-user and multi-branch support
- Government ID proof and photo capture
- Path management
- Email/SMS notification logging

## Quick start
```bash
cd visitor_management
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The API will run at `http://localhost:5000`.

## Example requests
### Create a branch
```bash
curl -X POST http://localhost:5000/branches \
  -H 'Content-Type: application/json' \
  -d '{"name":"HQ","location":"Downtown"}'
```

### Pre-enroll a visitor
```bash
curl -X POST http://localhost:5000/visitors/pre-enroll \
  -H 'Content-Type: application/json' \
  -d '{"full_name":"Alex Doe","company":"Contoso","branch_id":1}'
```

### Approve a visitor
```bash
curl -X POST http://localhost:5000/visitors/1/approve
```

### Generate a visitor report
```bash
curl http://localhost:5000/visitors/report
```

## Notes
- ID proof and photo capture expect base64-encoded strings in the `id_proof` and `photo` fields.
- Notification endpoints write to the database for auditing.
- Access control and badge printing endpoints are stubs to integrate with real systems.
