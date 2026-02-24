import json
def test_inventory_exists_and_parses():
    p="/opt/revhome_api/inventory.json"
    with open(p,'r') as fh:
        j = json.load(fh)
    assert isinstance(j, dict) or isinstance(j, list)
