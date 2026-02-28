<?php
/**
 * Plugin Name: Portal Content Injector
 * Plugin URI: https://revflow.os
 * Description: Inject dynamic content into Elementor via shortcode from external API.
 * Version: 1.0.0
 * Author: RevFlow OS
 * Author URI: https://revflow.os
 * License: GPL v2 or later
 * Text Domain: portal-content-injector
 */

if (!defined('ABSPATH')) {
    exit;
}

define('PCI_VERSION', '1.0.0');
define('PCI_PLUGIN_FILE', __FILE__);
define('PCI_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('PCI_PLUGIN_URL', plugin_dir_url(__FILE__));

require_once PCI_PLUGIN_DIR . 'includes/class-portal-content-api-client.php';
require_once PCI_PLUGIN_DIR . 'includes/class-portal-content-cache.php';
require_once PCI_PLUGIN_DIR . 'includes/class-portal-content-shortcode.php';
require_once PCI_PLUGIN_DIR . 'includes/class-portal-content-injector.php';

register_activation_hook(PCI_PLUGIN_FILE, array('Portal_Content_Injector', 'activate'));
register_deactivation_hook(PCI_PLUGIN_FILE, array('Portal_Content_Injector', 'deactivate'));

Portal_Content_Injector::instance();
