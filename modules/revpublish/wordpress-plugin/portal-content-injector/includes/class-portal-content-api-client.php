<?php

if (!defined('ABSPATH')) {
    exit;
}

class Portal_Content_Api_Client {
    const DEFAULT_TIMEOUT = 6;
    const MAX_BODY_BYTES = 200000;

    /**
     * Fetch content payload from external API.
     *
     * Expected API response examples:
     * - { "content": "..." }
     * - { "data": { "hero.heading": "..." } }
     * - { "hero.heading": "..." }
     *
     * @param string $content_key
     * @return array{ok:bool, content:string, error:string}
     */
    public function fetch($content_key) {
        $endpoint = $this->get_endpoint();
        if (!$endpoint) {
            return array('ok' => false, 'content' => '', 'error' => 'Missing API endpoint.');
        }

        $request_url = add_query_arg(
            array('key' => rawurlencode($content_key)),
            $endpoint
        );

        $args = array(
            'timeout' => apply_filters('pci_api_timeout', self::DEFAULT_TIMEOUT),
            'redirection' => 2,
            'httpversion' => '1.1',
            'blocking' => true,
            'headers' => array(
                'Accept' => 'application/json',
            ),
        );

        $response = wp_remote_get($request_url, $args);
        if (is_wp_error($response)) {
            $this->debug_log('API request error: ' . $response->get_error_message());
            return array('ok' => false, 'content' => '', 'error' => 'API request failed.');
        }

        $status = (int) wp_remote_retrieve_response_code($response);
        $body = (string) wp_remote_retrieve_body($response);
        if ($status < 200 || $status >= 300) {
            $this->debug_log('API non-2xx status: ' . $status);
            return array('ok' => false, 'content' => '', 'error' => 'API returned non-success status.');
        }

        if (strlen($body) > self::MAX_BODY_BYTES) {
            $this->debug_log('API response too large.');
            return array('ok' => false, 'content' => '', 'error' => 'API response too large.');
        }

        $decoded = json_decode($body, true);
        if (!is_array($decoded)) {
            $this->debug_log('Invalid JSON response.');
            return array('ok' => false, 'content' => '', 'error' => 'API response is not valid JSON.');
        }

        $content = $this->extract_content($decoded, $content_key);
        if ($content === '') {
            return array('ok' => false, 'content' => '', 'error' => 'Content key not found in API response.');
        }

        return array('ok' => true, 'content' => $content, 'error' => '');
    }

    private function get_endpoint() {
        $default = 'https://your-python-api.example.com/api/portal-content';
        $endpoint = apply_filters('pci_api_endpoint', $default);
        $endpoint = is_string($endpoint) ? trim($endpoint) : '';
        if ($endpoint === '') {
            return '';
        }

        // Basic SSRF hardening: allow only HTTPS endpoint.
        if (stripos($endpoint, 'https://') !== 0) {
            return '';
        }

        return esc_url_raw($endpoint);
    }

    private function extract_content($decoded, $content_key) {
        if (isset($decoded['content']) && is_string($decoded['content'])) {
            return $decoded['content'];
        }

        if (isset($decoded['data']) && is_array($decoded['data']) && isset($decoded['data'][$content_key])) {
            return is_string($decoded['data'][$content_key]) ? $decoded['data'][$content_key] : '';
        }

        if (isset($decoded[$content_key]) && is_string($decoded[$content_key])) {
            return $decoded[$content_key];
        }

        return '';
    }

    private function debug_log($message) {
        if (defined('WP_DEBUG') && WP_DEBUG) {
            error_log('[PCI] ' . $message);
        }
    }
}
