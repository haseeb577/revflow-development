<?php

if (!defined('ABSPATH')) {
    exit;
}

class Portal_Content_Shortcode {
    /**
     * @var Portal_Content_Api_Client
     */
    private $api_client;

    /**
     * @var Portal_Content_Cache
     */
    private $cache;

    public function __construct(Portal_Content_Api_Client $api_client, Portal_Content_Cache $cache) {
        $this->api_client = $api_client;
        $this->cache = $cache;
    }

    public function register() {
        add_shortcode('portal_content', array($this, 'render'));
    }

    public function render($atts) {
        $atts = shortcode_atts(
            array(
                'key' => '',
                'fallback' => '',
                // html|text
                'format' => 'html',
            ),
            $atts,
            'portal_content'
        );

        $content_key = sanitize_text_field($atts['key']);
        $fallback = (string) $atts['fallback'];
        $format = strtolower(sanitize_text_field($atts['format']));

        if (!$this->is_valid_key($content_key)) {
            return $this->escape_output($fallback, $format);
        }

        $cache_key = $content_key . '|' . $format;
        $cached = $this->cache->get($cache_key);
        if (is_string($cached) && $cached !== '') {
            return $cached;
        }

        $result = $this->api_client->fetch($content_key);
        if (!$result['ok']) {
            $output = $this->escape_output($fallback, $format);
            if ($output !== '') {
                $this->cache->set($cache_key, $output);
            }
            return $output;
        }

        $output = $this->escape_output($result['content'], $format);
        if ($output !== '') {
            $this->cache->set($cache_key, $output);
        }

        return $output;
    }

    private function is_valid_key($key) {
        if ($key === '') {
            return false;
        }
        // Dot/underscore/hyphen notation only.
        return (bool) preg_match('/^[a-zA-Z0-9._-]{1,120}$/', $key);
    }

    private function escape_output($value, $format) {
        $value = is_string($value) ? $value : '';
        if ($value === '') {
            return '';
        }

        if ($format === 'text') {
            return esc_html($value);
        }

        // HTML mode: allow safe inline markup only.
        return wp_kses_post($value);
    }
}
