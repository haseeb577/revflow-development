#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/shared-api-engine')
from src.costs.pipeline_wrapper import generate_page, PagePriority

print('Testing Cost Management v2.0...')
print('Generating 4 test pages...\n')

pages = [
    {'slug': 'index.html', 'type': 'homepage'},
    {'slug': 'emergency', 'type': 'service'},
    {'slug': 'aurora', 'type': 'location'},
    {'slug': 'lakewood', 'type': 'location'}
]

results = []
for page in pages:
    priority = PagePriority.P0 if page['type'] == 'homepage' else PagePriority.P1 if page['type'] == 'service' else PagePriority.P2
    print(f"Page: {page['slug']} (Priority: {priority})")
    result = generate_page('https://test.com', page['slug'], 'Plumbing', 'Denver', 'CO', page_priority=priority)
    print(f"  Status: {result.get('status', 'unknown')}\n")
    results.append(result)

completed = len([r for r in results if r.get('status') == 'completed'])
queued = len([r for r in results if r.get('status') == 'queued'])
print(f"Summary: {completed} completed, {queued} queued")
