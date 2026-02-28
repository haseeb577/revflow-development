<?php

if (!defined('ABSPATH')) {
    exit;
}

class Portal_Content_Cache {
    const TTL = 300; // 5 minutes.
    const KEY_PREFIX = 'pci_content_';

    public function get($cache_key) {
        return get_transient($this->build_key($cache_key));
    }

    public function set($cache_key, $value) {
        set_transient($this->build_key($cache_key), $value, self::TTL);
    }

    private function build_key($cache_key) {
        return self::KEY_PREFIX . md5((string) $cache_key);
    }
}
