# Portal Content Injector

Dynamic shortcode-based content injection for Elementor without editing `_elementor_data`.

## Shortcode

```text
[portal_content key="hero.heading"]
[portal_content key="hero.heading" fallback="Default Heading"]
[portal_content key="hero.description" format="html"]
[portal_content key="cta.phone" format="text"]
```

## Expected API Response

One of the following JSON shapes:

```json
{ "content": "..." }
```

```json
{ "data": { "hero.heading": "..." } }
```

```json
{ "hero.heading": "..." }
```

## Security Notes

- Only HTTPS API endpoint is accepted.
- Shortcode key is validated with strict pattern.
- Output is escaped:
  - `format="html"` -> `wp_kses_post`
  - `format="text"` -> `esc_html`
- Request timeout is enforced.
- API failures return fallback or empty string safely.

## Caching

- Uses WordPress transients.
- TTL is 5 minutes.

## Configure API Endpoint

Use this filter in a must-use plugin or theme:

```php
add_filter('pci_api_endpoint', function () {
    return 'https://your-python-api.example.com/api/portal-content';
});
```

