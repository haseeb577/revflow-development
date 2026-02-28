<?php

if (!defined('ABSPATH')) {
    exit;
}

class Portal_Content_Injector {
    /**
     * @var Portal_Content_Injector|null
     */
    private static $instance = null;

    /**
     * @var Portal_Content_Shortcode
     */
    private $shortcode;

    public static function instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        $client = new Portal_Content_Api_Client();
        $cache = new Portal_Content_Cache();
        $this->shortcode = new Portal_Content_Shortcode($client, $cache);
        $this->shortcode->register();
    }

    public static function activate() {
        if (!function_exists('add_shortcode')) {
            deactivate_plugins(plugin_basename(PCI_PLUGIN_FILE));
            wp_die(esc_html__('WordPress shortcode support is required.', 'portal-content-injector'));
        }
    }

    public static function deactivate() {
        // Keep transients by default. No destructive cleanup on deactivate.
    }
}
