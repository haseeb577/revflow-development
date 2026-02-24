<?php
/**
 * Plugin Name: RevPublish Connector
 * Plugin URI: https://revflow.os
 * Description: Connects your WordPress site to RevPublish portal for automated content management
 * Version: 1.0.0
 * Author: RevFlow OS
 * Author URI: https://revflow.os
 * License: GPL v2 or later
 * Text Domain: revpublish-connector
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

class RevPublishConnector {
    
    private $portal_url;
    private $site_secret;
    
    public function __construct() {
        $this->portal_url = get_option('revpublish_portal_url', '');
        $this->site_secret = get_option('revpublish_site_secret', '');
        
        // Register REST API endpoint
        add_action('rest_api_init', array($this, 'register_rest_routes'));
        
        // Admin menu
        add_action('admin_menu', array($this, 'add_admin_menu'));
        
        // Auto-register on activation
        register_activation_hook(__FILE__, array($this, 'activate'));
    }
    
    public function register_rest_routes() {
        // Site info endpoint (public, but requires secret)
        register_rest_route('revpublish/v1', '/site-info', array(
            'methods' => 'GET',
            'callback' => array($this, 'get_site_info'),
            'permission_callback' => array($this, 'verify_secret'),
        ));
        
        // Health check endpoint
        register_rest_route('revpublish/v1', '/health', array(
            'methods' => 'GET',
            'callback' => array($this, 'health_check'),
            'permission_callback' => '__return_true',
        ));
        
        // Register with portal endpoint
        register_rest_route('revpublish/v1', '/register', array(
            'methods' => 'POST',
            'callback' => array($this, 'register_with_portal'),
            'permission_callback' => array($this, 'verify_secret'),
        ));
    }
    
    public function verify_secret($request) {
        $secret = $request->get_header('X-RevPublish-Secret');
        $stored_secret = get_option('revpublish_site_secret', '');
        
        // If no secret is set, allow first-time access
        if (empty($stored_secret)) {
            return true;
        }
        
        return !empty($secret) && hash_equals($stored_secret, $secret);
    }
    
    public function get_site_info($request) {
        return array(
            'site_id' => get_option('revpublish_site_id', wp_generate_uuid4()),
            'site_name' => get_bloginfo('name'),
            'site_url' => home_url(),
            'admin_url' => admin_url(),
            'wp_version' => get_bloginfo('version'),
            'php_version' => PHP_VERSION,
            'theme' => get_option('stylesheet'),
            'plugins_count' => count(get_option('active_plugins', array())),
            'status' => 'active',
            'registered_at' => get_option('revpublish_registered_at', current_time('mysql')),
            'last_sync' => get_option('revpublish_last_sync', null),
        );
    }
    
    public function health_check($request) {
        return array(
            'status' => 'ok',
            'plugin_version' => '1.0.0',
            'wordpress_version' => get_bloginfo('version'),
            'site_url' => home_url(),
        );
    }
    
    public function register_with_portal($request) {
        $data = $request->get_json_params();
        
        // Store registration data
        if (isset($data['portal_url'])) {
            update_option('revpublish_portal_url', $data['portal_url']);
        }
        
        if (isset($data['site_secret'])) {
            update_option('revpublish_site_secret', $data['site_secret']);
        }
        
        if (isset($data['site_id'])) {
            update_option('revpublish_site_id', $data['site_id']);
        }
        
        update_option('revpublish_registered_at', current_time('mysql'));
        
        return array(
            'status' => 'success',
            'message' => 'Site registered successfully',
            'site_info' => $this->get_site_info($request),
        );
    }
    
    public function add_admin_menu() {
        add_options_page(
            'RevPublish Settings',
            'RevPublish',
            'manage_options',
            'revpublish-connector',
            array($this, 'admin_page')
        );
    }
    
    public function admin_page() {
        $portal_url = get_option('revpublish_portal_url', '');
        $site_secret = get_option('revpublish_site_secret', '');
        $site_id = get_option('revpublish_site_id', '');
        
        if (isset($_POST['revpublish_save'])) {
            check_admin_referer('revpublish_settings');
            
            update_option('revpublish_portal_url', sanitize_text_field($_POST['portal_url']));
            
            if (empty($site_secret)) {
                $new_secret = wp_generate_password(32, false);
                update_option('revpublish_site_secret', $new_secret);
                $site_secret = $new_secret;
            }
            
            echo '<div class="notice notice-success"><p>Settings saved!</p></div>';
        }
        
        ?>
        <div class="wrap">
            <h1>RevPublish Connector Settings</h1>
            <form method="post" action="">
                <?php wp_nonce_field('revpublish_settings'); ?>
                <table class="form-table">
                    <tr>
                        <th><label for="portal_url">RevPublish Portal URL</label></th>
                        <td>
                            <input type="url" id="portal_url" name="portal_url" 
                                   value="<?php echo esc_attr($portal_url); ?>" 
                                   class="regular-text" 
                                   placeholder="https://your-portal.com" />
                            <p class="description">Your RevPublish portal URL</p>
                        </td>
                    </tr>
                    <tr>
                        <th><label>Site ID</label></th>
                        <td>
                            <code><?php echo esc_html($site_id ?: 'Not set'); ?></code>
                            <p class="description">Unique identifier for this site</p>
                        </td>
                    </tr>
                    <tr>
                        <th><label>Site Secret</label></th>
                        <td>
                            <code><?php echo esc_html($site_secret ?: 'Not set'); ?></code>
                            <p class="description">Secret key for API authentication</p>
                        </td>
                    </tr>
                    <tr>
                        <th><label>API Endpoint</label></th>
                        <td>
                            <code><?php echo esc_url(rest_url('revpublish/v1/site-info')); ?></code>
                            <p class="description">Use this URL to connect from RevPublish portal</p>
                        </td>
                    </tr>
                </table>
                <?php submit_button('Save Settings', 'primary', 'revpublish_save'); ?>
            </form>
            
            <h2>How to Connect</h2>
            <ol>
                <li>Copy the <strong>API Endpoint</strong> URL above</li>
                <li>Copy the <strong>Site Secret</strong> above</li>
                <li>In RevPublish portal, add this site using the endpoint and secret</li>
                <li>The portal will automatically discover and register this site</li>
            </ol>
        </div>
        <?php
    }
    
    public function activate() {
        // Generate site ID and secret on first activation
        if (empty(get_option('revpublish_site_id'))) {
            update_option('revpublish_site_id', wp_generate_uuid4());
        }
        
        if (empty(get_option('revpublish_site_secret'))) {
            update_option('revpublish_site_secret', wp_generate_password(32, false));
        }
        
        // Flush rewrite rules
        flush_rewrite_rules();
    }
}

// Initialize plugin
new RevPublishConnector();

